import requests
import time
import os
from urllib.parse import urlencode
from pathlib import Path
import json
import base64

class ShutterflyDownloader:
    def __init__(self, access_token, output_dir="downloads", rate_limit_delay=1.0):
        self.access_token = access_token
        self.output_dir = Path(output_dir)
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'origin': 'https://photos.shutterfly.com',
            'referer': 'https://photos.shutterfly.com/'
        })
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_albums(self):
        """Fetch all albums from Shutterfly"""
        url = 'https://cmd.thislife.com/json?method=album.getAlbums'
        
        # Extract sfly_uid from JWT token
        token_parts = self.access_token.split('.')
        claims = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)))
        sfly_uid = claims['sfly_uid']
        
        payload = {
            "method": "album.getAlbums",
            "params": [
                self.access_token,
                sfly_uid,
                None,
                None,
                True
            ],
            "headers": {
                "X-SFLY-SubSource": "library"
            },
            "id": None
        }
        
        response = self.session.post(url, json=payload)
        data = response.json()
        
        if not data['result']['success']:
            raise Exception(f"Failed to get albums: {data['result'].get('message', 'Unknown error')}")
        
        albums = []
        for permission in data['result']['payload'][0]:
            story = permission['story']
            albums.append({
                'id': story['uid'],
                'name': story['name'],
                'photo_count': story['visible_moment_count']
            })
        
        return albums
    
    def get_album_contents(self, album_id):
        """Fetch contents of a specific album"""
        url = 'https://cmd.thislife.com/json?method=album.getAlbum'
        
        payload = {
            "method": "album.getAlbum",
            "params": [
                self.access_token,
                album_id,
                "startupItem",
                None,
                False,
                True,
                True
            ],
            "headers": {
                "X-SFLY-SubSource": "albums"
            },
            "id": None
        }
        
        response = self.session.post(url, json=payload)
        return response.json()
    
    def extract_moment_ids(self, moments_string):
        """Extract all moment IDs from the moments string"""
        records = [moments_string[i:i+277] for i in range(0, len(moments_string), 277)]
        moment_ids = [record[9:25] for record in records]
        return moment_ids
    
    def build_download_url(self, moment_id):
        """Construct the download URL for a given moment ID"""
        params = {
            'accessToken': self.access_token,
            'momentId': moment_id,
            'source': 'library'
        }
        return f"https://io.thislife.com/download?{urlencode(params)}"
    
    def download_photo(self, moment_id, album_name, index):
        """Download a single photo to its album directory"""
        url = self.build_download_url(moment_id)
        album_dir = self.output_dir / self.sanitize_filename(album_name)
        album_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            response = self.session.get(url, stream=True)
            response.raise_for_status()
            
            # Try to get filename from content-disposition header
            filename = None
            cd = response.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                filename = cd.split('filename=')[1].strip('"\'')
            
            # Fallback filename if none provided
            if not filename:
                filename = f"photo_{index:04d}_{moment_id}.jpg"
            
            filepath = album_dir / filename
            
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"Successfully downloaded: {album_name}/{filename}")
            return True
            
        except Exception as e:
            print(f"Error downloading moment_id {moment_id} for album {album_name}: {str(e)}")
            return False
    
    @staticmethod
    def sanitize_filename(filename):
        """Remove invalid characters from filename"""
        return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
    
    def download_album(self, album_id, album_name):
        """Download all photos in an album"""
        print(f"\nProcessing album: {album_name}")
        
        album_data = self.get_album_contents(album_id)
        if not album_data['result']['success']:
            print(f"Failed to get album contents for {album_name}")
            return 0, 0
        
        moments_string = album_data['result']['payload'].get('moments', '')
        moment_ids = self.extract_moment_ids(moments_string)
        
        print(f"Found {len(moment_ids)} photos in album")
        
        successful = 0
        failed = 0
        
        for i, moment_id in enumerate(moment_ids, 1):
            print(f"Downloading photo {i}/{len(moment_ids)}")
            
            if self.download_photo(moment_id, album_name, i):
                successful += 1
            else:
                failed += 1
            
            if i < len(moment_ids):
                time.sleep(self.rate_limit_delay)
        
        return successful, failed
    
    def download_all_albums(self):
        """Download all albums and their photos"""
        albums = self.get_albums()
        print(f"Found {len(albums)} albums")
        
        total_successful = 0
        total_failed = 0
        
        for album in albums:
            print(f"\nProcessing album: {album['name']} ({album['photo_count']} photos)")
            successful, failed = self.download_album(album['id'], album['name'])
            
            total_successful += successful
            total_failed += failed
            
            time.sleep(self.rate_limit_delay)  # Delay between albums
        
        print(f"\nDownload complete!")
        print(f"Total successfully downloaded: {total_successful}")
        print(f"Total failed downloads: {total_failed}")
        return total_successful, total_failed

# Example usage:
if __name__ == "__main__":
    ACCESS_TOKEN = "insert token here"
    
    downloader = ShutterflyDownloader(
        access_token=ACCESS_TOKEN,
        output_dir="shutterfly_photos",
        rate_limit_delay=1.0
    )
    
    downloader.download_all_albums()