import requests
import os
from urllib.parse import urlencode
from pathlib import Path
import json
import base64
from datetime import datetime, timedelta
import random
import argparse
from PIL import Image
import numpy as np
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

class TokenExpiredError(Exception):
    pass

class ShutterflyDownloader:
    def __init__(self, access_token, output_dir="downloads", rate_limit_delay=0.1, max_retries=3, ignore_albums=None, max_parallel_workers=1):
        self.access_token = access_token
        self.output_dir = Path(output_dir)
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.ignore_albums = set(ignore_albums or [])  # Convert to set for faster lookups
        self.max_parallel_workers=max_parallel_workers
        self.session = requests.Session()
        
        # Handle both access tokens and session cookies
        if access_token.startswith('_thislife_session='):
            # This is a session cookie, extract the session value
            session_value = access_token.split('_thislife_session=')[1].split(';')[0]
            # URL decode the session value
            import urllib.parse
            session_value = urllib.parse.unquote(session_value)
            self.session.headers.update({
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://photos.shutterfly.com',
                'referer': 'https://photos.shutterfly.com/',
                'cookie': f'_thislife_session={session_value}'
            })
            print("Using session cookie authentication")
        else:
            # This is an access token
            self.session.headers.update({
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://photos.shutterfly.com',
                'referer': 'https://photos.shutterfly.com/'
            })
            print("Using access token authentication")
        
        # Parse token expiration if it's a JWT token, otherwise set default expiration
        try:
            token_parts = self.access_token.split('.')
            if len(token_parts) == 3:  # JWT tokens have 3 parts
                self.claims = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)))
                self.token_expiry = datetime.fromtimestamp(self.claims['exp'])
            else:
                # Not a JWT token, set default expiration to 1 hour from now
                self.claims = {}
                self.token_expiry = datetime.now() + timedelta(hours=1)
                print("Warning: Token doesn't appear to be in JWT format. Setting default expiration to 1 hour.")
        except Exception as e:
            # If token parsing fails, set default expiration
            self.claims = {}
            self.token_expiry = datetime.now() + timedelta(hours=1)
            print(f"Warning: Could not parse token expiration: {e}. Setting default expiration to 1 hour.")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load ignore list from file if it exists
        ignore_file = self.output_dir / 'ignore_albums.txt'
        if ignore_file.exists():
            with open(ignore_file) as f:
                self.ignore_albums.update(line.strip() for line in f if line.strip())
    
    def check_token_validity(self):
        """Check if token is still valid"""
        if datetime.now() >= self.token_expiry:
            raise TokenExpiredError("Access token has expired")

    def update_access_token(self, new_token):
        """Update the access token and its expiration time"""
        self.access_token = new_token
        try:
            token_parts = self.access_token.split('.')
            if len(token_parts) == 3:  # JWT tokens have 3 parts
                self.claims = json.loads(base64.b64decode(token_parts[1] + '=' * (-len(token_parts[1]) % 4)))
                self.token_expiry = datetime.fromtimestamp(self.claims['exp'])
            else:
                # Not a JWT token, set default expiration to 1 hour from now
                self.claims = {}
                self.token_expiry = datetime.now() + timedelta(hours=1)
                print("Warning: New token doesn't appear to be in JWT format. Setting default expiration to 1 hour.")
        except Exception as e:
            # If token parsing fails, set default expiration
            self.claims = {}
            self.token_expiry = datetime.now() + timedelta(hours=1)
            print(f"Warning: Could not parse new token expiration: {e}. Setting default expiration to 1 hour.")
        print("Access token updated successfully")

    def make_request(self, method, url, **kwargs):
        """Make a request with retry logic and exponential backoff"""
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                self.check_token_validity()
                
                if retry_count > 0:
                    # Exponential backoff: 2^retry_count seconds
                    wait_time = (2 ** retry_count) + (random.random() * 0.5)
                    print(f"Retrying in {wait_time:.1f} seconds...")
                    time.sleep(wait_time)
                
                response = getattr(self.session, method)(url, **kwargs)
                response.raise_for_status()
                
                return response
                
            except TokenExpiredError:
                print("\nAccess token has expired. Please provide a new token.")
                print("Options:")
                print("1. Save token to a file named 'token.txt' and press Enter")
                print("2. Paste token directly (if your terminal supports it)")
                
                new_token = None
                
                # Try reading from file first
                if os.path.exists('token.txt'):
                    try:
                        with open('token.txt', 'r') as f:
                            new_token = f.read().strip()
                        # Clean up the file
                        os.unlink('token.txt')
                        print("Successfully read token from token.txt")
                    except Exception as e:
                        print(f"Error reading token.txt: {e}")
                
                # If no file or file read failed, try direct input
                if not new_token:
                    try:
                        new_token = input("Enter token: ").strip()
                    except Exception:
                        print("Error reading token from input. Please try the file method.")
                        continue
                
                if not new_token:
                    print("No token provided. Please try again.")
                    continue
                
                self.update_access_token(new_token)
                retry_count -= 1  # Don't count token updates as retries
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                if retry_count <= self.max_retries:
                    print(f"Request failed: {str(e)}")
                else:
                    raise Exception(f"Max retries exceeded: {str(e)}")
            
            except Exception as e:
                print(f"Unexpected error: {str(e)}")
                raise

    def get_albums(self):
        """Fetch all albums from Shutterfly"""
        url = 'https://cmd.thislife.com/json?method=album.getAlbums'
        
        # Get user ID from environment or prompt user
        user_id = os.environ.get('LIFE_UID')
        if not user_id:
            print("\nNo LIFE_UID found in environment variables.")
            print("This is required for the Shutterfly API to work.")
            print("You can find your UID in the URL of your Shutterfly account page")
            print("or set it as an environment variable: export LIFE_UID=your_uid_here")
            user_id = input("Please enter your Shutterfly user ID: ").strip()
            if not user_id:
                raise Exception("User ID is required to proceed")
        
        # Handle different authentication methods
        if self.access_token.startswith('_thislife_session='):
            # Using session cookie - try both with and without access token
            # First try with just the session cookie
            payload = {
                "method": "album.getAlbums",
                "params": [
                    user_id,  # User ID as first param
                    None,
                    None,
                    True
                ],
                "headers": {
                    "X-SFLY-SubSource": "library"
                },
                "id": None
            }
            
            print(f"Debug: Trying with session cookie only...")
            response = self.make_request('post', url, json=payload)
            data = response.json()
            
            if data['result']['success']:
                print("Success with session cookie only!")
            else:
                print(f"Session cookie only failed: {data['result'].get('message', 'Unknown error')}")
                # Try with a placeholder token in case the API expects one
                payload["params"] = [
                    "placeholder_token",  # Try with a placeholder
                    user_id,
                    None,
                    None,
                    True
                ]
                print(f"Debug: Trying with placeholder token...")
                response = self.make_request('post', url, json=payload)
                data = response.json()
        else:
            # Using access token - send token in params
            # Try different parameter orders since API is saying "Wrong or missing Parameter"
            payload = {
                "method": "album.getAlbums",
                "params": [
                    self.access_token,
                    user_id,  # Use the user ID we just got
                    None,
                    None,
                    True
                ],
                "headers": {
                    "X-SFLY-SubSource": "library"
                },
                "id": None
            }
            
            print(f"Debug: Trying with token first, user ID second...")
            response = self.make_request('post', url, json=payload)
            data = response.json()
            
            if data['result']['success']:
                print("Success with token first!")
            else:
                print(f"Token first failed: {data['result'].get('message', 'Unknown error')}")
                # Try with user ID first, token second
                payload["params"] = [
                    user_id,
                    self.access_token,
                    None,
                    None,
                    True
                ]
                print(f"Debug: Trying with user ID first, token second...")
                response = self.make_request('post', url, json=payload)
                data = response.json()
        
        print(f"Debug: Making request to {url}")
        print(f"Debug: Payload: {json.dumps(payload, indent=2)}")
        print(f"Debug: Access token: {self.access_token[:20]}...")
        print(f"Debug: User ID: {user_id}")
        
        response = self.make_request('post', url, json=payload)
        data = response.json()
        
        print(f"Debug: Response status: {response.status_code}")
        print(f"Debug: Response data: {json.dumps(data, indent=2)}")
        
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
        
        response = self.make_request('post', url, json=payload)
        return response.json()
    
    def extract_moment_ids(self, moments_string):
        """Extract all moment IDs from the moments string"""
        records = [moments_string[i:i+277] for i in range(0, len(moments_string), 277)]
        # Extract the 16-digit moment IDs and strip leading zeros
        moment_ids = [record[9:25].lstrip('0') for record in records]
        return moment_ids
    
    def build_download_url(self, moment_id):
        """Construct the download URL for a given moment ID"""
        params = {
            'accessToken': self.access_token,
            'momentId': moment_id,
            'source': 'library'
        }
        return f"https://io.thislife.com/download?{urlencode(params)}"
    
    def download_photo(self, moment_id, album_name, index, downloaded_files=None, duplicate_stats=None):
        """Download a single photo to its album directory
        
        Args:
            moment_id: The ID of the photo to download
            album_name: The name of the album
            index: The index of the photo in the album
            downloaded_files: Set of filenames already downloaded in this session
            duplicate_stats: Dictionary to track duplicate statistics
        """
        url = self.build_download_url(moment_id)
        album_dir = self.output_dir / self.sanitize_filename(album_name)
        album_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            response = self.make_request('get', url, stream=True)
            
            # Try to get filename from content-disposition header
            filename = None
            cd = response.headers.get('content-disposition')
            if cd and 'filename=' in cd:
                filename = cd.split('filename=')[1].strip('"\'')
            
            # Fallback filename if none provided
            if not filename:
                filename = f"photo_{index:04d}_{moment_id}.jpg"
            
            filepath = album_dir / filename
            
            # Only do comparison if we've already downloaded a file with this name in this session
            if downloaded_files is not None and filename in downloaded_files:
                if duplicate_stats is not None:
                    duplicate_stats['same_name_count'] += 1
                
                # Download to temporary file first
                temp_filepath = album_dir / f"temp_{moment_id}.jpg"
                with open(temp_filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                # Compare files
                is_different, difference_type = self.files_are_different(filepath, temp_filepath)
                if is_different:
                    # Track the type of difference
                    if duplicate_stats is not None:
                        if difference_type == 'size':
                            duplicate_stats['different_size'] += 1
                        elif difference_type == 'content':
                            duplicate_stats['different_content'] += 1
                    
                    # Files are different, create unique name
                    base, ext = os.path.splitext(filename)
                    counter = 1
                    while filepath.exists():
                        new_filename = f"{base}_{counter}{ext}"
                        filepath = album_dir / new_filename
                        counter += 1
                    # Rename temp file to unique name
                    temp_filepath.rename(filepath)
                    diff_msg = f"different file size" if difference_type == 'size' else f"different content but same size"
                    print(f"Warning: Found {diff_msg} for {filename}, saved as: {filepath.name}")
                else:
                    # Files are identical, delete temp file
                    temp_filepath.unlink()
                    print(f"Note: File {filename} is identical to previously downloaded copy")
            else:
                # No duplicate in this session, write directly
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"Successfully downloaded: {album_name}/{filepath.name}")
            
            # Track this filename
            if downloaded_files is not None:
                downloaded_files.add(filename)
            
            return True
            
        except Exception as e:
            print(f"Error downloading moment_id {moment_id} for album {album_name}: {str(e)}")
            return False
    
    def files_are_different(self, file1, file2, chunk_size=8192):
        """Compare two files chunk by chunk to see if they're different
        
        Returns:
            tuple: (is_different, difference_type)
            where difference_type is one of: None, 'size', 'content', 'pixels'
        """
        if file1.stat().st_size != file2.stat().st_size:
            return True, 'size'
        
        # For image files, compare pixel data
        if any(file1.name.lower().endswith(ext) for ext in ('.jpg', '.jpeg', '.png')):
            try:
                with Image.open(file1) as img1, Image.open(file2) as img2:
                    # Normalize orientation based on EXIF
                    try:
                        for img in (img1, img2):
                            if hasattr(img, '_getexif') and img._getexif():
                                orientation = img._getexif().get(274)  # 274 is the orientation tag
                                if orientation:
                                    rotations = {
                                        3: Image.ROTATE_180,
                                        6: Image.ROTATE_270,
                                        8: Image.ROTATE_90
                                    }
                                    if orientation in rotations:
                                        img = img.transpose(rotations[orientation])
                    except:
                        pass  # Ignore orientation errors
                    
                    # Check dimensions first (after potential rotation)
                    if img1.size != img2.size:
                        return True, 'pixels'
                    
                    # Convert to RGB, dropping alpha channel if present
                    if img1.mode in ('RGBA', 'LA'):
                        img1 = img1.convert('RGB')
                    if img2.mode in ('RGBA', 'LA'):
                        img2 = img2.convert('RGB')
                    
                    # Convert both to RGB for consistent comparison
                    if img1.mode != 'RGB':
                        img1 = img1.convert('RGB')
                    if img2.mode != 'RGB':
                        img2 = img2.convert('RGB')
                    
                    # Get pixel data
                    data1 = np.array(img1)
                    data2 = np.array(img2)
                    
                    # Compare pixel data
                    if not np.array_equal(data1, data2):
                        # Calculate difference percentage for debugging
                        diff_pixels = np.sum(data1 != data2)
                        total_pixels = data1.size
                        diff_percent = (diff_pixels / total_pixels) * 100
                        print(f"Images differ by {diff_percent:.2f}% of pixels")
                        return True, 'pixels'
                    
                    return False, None
            except Exception as e:
                print(f"Warning: Error comparing images: {e}")
                # Fall back to byte comparison if image comparison fails
                pass
        
        # For non-image files or if image comparison failed, do byte comparison
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            while True:
                chunk1 = f1.read(chunk_size)
                chunk2 = f2.read(chunk_size)
                if chunk1 != chunk2:
                    return True, 'content'
                if not chunk1:  # EOF
                    return False, None
    
    @staticmethod
    def sanitize_filename(filename):
        """Remove invalid characters from filename"""
        return "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).rstrip()
    
    def download_album(self, album_id, album_name, duplicate_stats=None):
        """Download all photos in an album"""
        print(f"\nProcessing album: {album_name}")
        
        album_data = self.get_album_contents(album_id)
        if not album_data['result']['success']:
            print(f"Failed to get album contents for {album_name}")
            return 0, 0
        
        moments_string = album_data['result']['payload'].get('moments', '')
        moment_ids = self.extract_moment_ids(moments_string)
        
        print(f"Found {len(moment_ids)} photos in album")
        
        # Check for duplicates
        seen_moments = {}
        for i, moment_id in enumerate(moment_ids, 1):
            if moment_id in seen_moments:
                print(f"\nWarning: Duplicate moment ID {moment_id} found at positions {seen_moments[moment_id]} and {i}")
            else:
                seen_moments[moment_id] = i
        
        if len(seen_moments) != len(moment_ids):
            print(f"\nWarning: Album contains {len(moment_ids)} photos but only {len(seen_moments)} unique moment IDs")
        
        successful = 0
        failed = 0
        downloaded_files = set()
        
        # Use provided stats or create new ones
        album_stats = duplicate_stats if duplicate_stats is not None else {
            'same_name_count': 0,
            'different_size': 0,
            'different_content': 0
        }

        with ThreadPoolExecutor(max_workers=self.max_parallel_workers) as executor:
            # schedule all downloads
            futures = {
                executor.submit(
                    self.download_photo,
                    moment_id,
                    album_name,
                    idx,
                    downloaded_files,
                    album_stats
                ): moment_id
                for idx, moment_id in enumerate(moment_ids, start=1)
            }

            # as each download completes, tally results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    print(f"Error in worker for moment {futures[future]}: {e}")
                    failed += 1
        
        # Print album-level duplicate statistics if we found any
        if album_stats['same_name_count'] > 0 and duplicate_stats is None:  # Only print if not aggregating
            print(f"\nDuplicate filename statistics for this album:")
            print(f"- Found {album_stats['same_name_count']} files with duplicate names")
            if album_stats['different_size'] > 0:
                print(f"  - {album_stats['different_size']} had different file sizes (definitely different photos)")
            if album_stats['different_content'] > 0:
                print(f"  - {album_stats['different_content']} had same size but different content (possible metadata differences)")
        
        return successful, failed
    
    def download_all_albums(self, resume_from=None):
        """Download all albums and their photos"""
        albums = self.get_albums()
        print(f"Found {len(albums)} albums")
        
        # Find the starting point if resuming
        start_index = 0
        if resume_from:
            for i, album in enumerate(albums):
                if album['name'] == resume_from:
                    start_index = i
                    print(f"Resuming from album: {resume_from}")
                    break
            else:
                print(f"Warning: Album '{resume_from}' not found, starting from beginning")
        
        total_successful = 0
        total_failed = 0
        
        for album in albums[start_index:]:
            print(f"\nProcessing album: {album['name']} ({album['photo_count']} photos)")
            successful, failed = self.download_album(album['id'], album['name'])
            
            total_successful += successful
            total_failed += failed
            
            time.sleep(self.rate_limit_delay)  # Delay between albums
        
        print(f"\nDownload complete!")
        print(f"Total successfully downloaded: {total_successful}")
        print(f"Total failed downloads: {total_failed}")
        return total_successful, total_failed

    def count_items(self):
        """Count total number of albums and photos without downloading"""
        albums = self.get_albums()
        total_photos = sum(album['photo_count'] for album in albums)
        
        print(f"\nFound {len(albums)} albums containing {total_photos} total photos:")
        for album in albums:
            print(f"- {album['name']}: {album['photo_count']} photos")
        
        return len(albums), total_photos

    def compare_local_vs_server(self):
        """Compare local downloaded photos against server counts"""
        print("\nComparing local downloads with server data...")
        
        # Get server-side album data and sanitize names
        server_albums = self.get_albums()
        server_data = {self.sanitize_filename(album['name']): album['photo_count'] 
                      for album in server_albums}
        
        # Get local data
        local_data = {}
        for album_dir in self.output_dir.iterdir():
            if album_dir.is_dir():
                # Count all files (not directories) in the album directory
                photo_count = len([f for f in album_dir.iterdir() if f.is_file()])
                local_data[album_dir.name] = photo_count
        
        # Compare and report
        print("\nComparison Results:")
        print("-" * 60)
        print(f"{'Album Name':<40} {'Server':<8} {'Local':<8} {'Status'}")
        print("-" * 60)
        
        missing_albums = set(server_data.keys()) - set(local_data.keys())
        extra_albums = set(local_data.keys()) - set(server_data.keys())
        common_albums = set(server_data.keys()) & set(local_data.keys())
        
        # Track albums needing redownload
        incomplete_albums = []
        incomplete_photo_count = 0
        
        # Show matching albums with different counts
        for album in sorted(common_albums):
            server_count = server_data[album]
            local_count = local_data[album]
            status = "✓" if server_count == local_count else "≠"
            if server_count != local_count:
                status = f"Missing {server_count - local_count}"
                incomplete_albums.append((album, server_count))
                incomplete_photo_count += server_count
            print(f"{album[:39]:<40} {server_count:<8} {local_count:<8} {status}")
        
        # Show missing albums
        for album in sorted(missing_albums):
            print(f"{album[:39]:<40} {server_data[album]:<8} {'0':<8} Not downloaded")
            incomplete_albums.append((album, server_data[album]))
            incomplete_photo_count += server_data[album]
        
        # Show extra local albums
        for album in sorted(extra_albums):
            print(f"{album[:39]:<40} {'?':<8} {local_data[album]:<8} Local only")
        
        # Print summary
        print("\nSummary:")
        print(f"Total albums on server: {len(server_data)}")
        print(f"Total albums locally: {len(local_data)}")
        print(f"Missing albums: {len(missing_albums)}")
        print(f"Extra local albums: {len(extra_albums)}")
        print(f"Incomplete albums: {len(incomplete_albums)} ({incomplete_photo_count} photos total)")
        
        server_total = sum(server_data.values())
        local_total = sum(local_data.values())
        print(f"\nTotal photos on server: {server_total}")
        print(f"Total photos locally: {local_total}")
        print(f"Difference: {server_total - local_total}")
        
        if incomplete_albums:
            print("\nAlbums needing redownload:")
            for album, photo_count in sorted(incomplete_albums):
                print(f"- {album} ({photo_count} photos)")
            print(f"\nUse --fix-incomplete to redownload these {len(incomplete_albums)} albums")

    def find_album_by_name(self, album_name, use_sanitized=False):
        """Find an album by its name
        
        Args:
            album_name: The name of the album to find
            use_sanitized: If True, compare using sanitized names
        """
        albums = self.get_albums()
        for album in albums:
            if use_sanitized:
                if self.sanitize_filename(album['name']) == album_name:
                    return album
            else:
                if album['name'] == album_name:
                    return album
        return None

    def download_single_album(self, album_name, use_sanitized=False):
        """Download a single album by name"""
        album = self.find_album_by_name(album_name, use_sanitized)
        if not album:
            print(f"\nAlbum not found: {album_name}")
            print("\nAvailable albums:")
            albums = self.get_albums()
            for a in albums:
                name = a['name']
                if use_sanitized:
                    name = self.sanitize_filename(name)
                print(f"- {name}")
            return 0, 0
        
        print(f"\nFound album: {album['name']} ({album['photo_count']} photos)")
        return self.download_album(album['id'], album['name'])

    def should_ignore_album(self, album_name):
        """Check if an album should be ignored"""
        sanitized_name = self.sanitize_filename(album_name)
        return album_name in self.ignore_albums or sanitized_name in self.ignore_albums

    def redownload_incomplete_albums(self):
        """Redownload all albums that have missing photos"""
        print("\nChecking for incomplete albums...")
        
        # Get server-side album data and sanitize names
        server_albums = self.get_albums()
        server_data = {self.sanitize_filename(album['name']): album for album in server_albums}
        
        # Get local data
        local_data = {}
        for album_dir in self.output_dir.iterdir():
            if album_dir.is_dir():
                # Count all files (not directories) in the album directory
                photo_count = len([f for f in album_dir.iterdir() if f.is_file()])
                local_data[album_dir.name] = photo_count
        
        # Collect all albums that need redownloading
        albums_to_download = []
        ignored_albums = []
        
        # Find albums with missing photos
        for sanitized_name, local_count in local_data.items():
            if sanitized_name in server_data:
                server_album = server_data[sanitized_name]
                if self.should_ignore_album(server_album['name']):
                    ignored_albums.append(server_album['name'])
                    continue
                
                server_count = server_album['photo_count']
                if local_count < server_count:
                    missing = server_count - local_count
                    albums_to_download.append((server_album, missing))
        
        # Find completely missing albums
        missing_albums = set(server_data.keys()) - set(local_data.keys())
        for sanitized_name in missing_albums:
            server_album = server_data[sanitized_name]
            if not self.should_ignore_album(server_album['name']):
                albums_to_download.append((server_album, server_album['photo_count']))
            else:
                ignored_albums.append(server_album['name'])
        
        if ignored_albums:
            print("\nIgnoring these albums:")
            for album_name in sorted(ignored_albums):
                print(f"- {album_name}")
        
        # Sort albums by photo count
        albums_to_download.sort(key=lambda x: x[0]['photo_count'])
        
        if albums_to_download:
            print("\nWill download albums in this order:")
            for album, missing in albums_to_download:
                print(f"- {album['name']} ({album['photo_count']} photos, {missing} missing)")
        
        total_successful = 0
        total_failed = 0
        
        # Track cumulative duplicate statistics
        cumulative_stats = {
            'same_name_count': 0,
            'different_size': 0,
            'different_content': 0,
            'albums_with_duplicates': 0,
            'total_albums': len(albums_to_download)
        }
        
        # Download albums in sorted order
        for album, missing in albums_to_download:
            print(f"\nDownloading {album['name']}: {album['photo_count']} photos")
            
            # Create stats for this album
            album_stats = {
                'same_name_count': 0,
                'different_size': 0,
                'different_content': 0
            }
            
            successful, failed = self.download_album(album['id'], album['name'], album_stats)
            total_successful += successful
            total_failed += failed
            
            # Update cumulative stats
            if album_stats['same_name_count'] > 0:
                cumulative_stats['albums_with_duplicates'] += 1
                cumulative_stats['same_name_count'] += album_stats['same_name_count']
                cumulative_stats['different_size'] += album_stats['different_size']
                cumulative_stats['different_content'] += album_stats['different_content']
        
        print(f"\nRedownload complete!")
        print(f"Total successfully downloaded: {total_successful}")
        print(f"Total failed downloads: {total_failed}")
        
        # Print cumulative duplicate statistics
        if cumulative_stats['same_name_count'] > 0:
            print(f"\nCumulative duplicate statistics across all albums:")
            print(f"- {cumulative_stats['albums_with_duplicates']} out of {cumulative_stats['total_albums']} albums had duplicates")
            print(f"- Found {cumulative_stats['same_name_count']} total files with duplicate names")
            if cumulative_stats['different_size'] > 0:
                print(f"  - {cumulative_stats['different_size']} had different file sizes (definitely different photos)")
            if cumulative_stats['different_content'] > 0:
                print(f"  - {cumulative_stats['different_content']} had same size but different content (possible metadata differences)")
        
        return total_successful, total_failed

    def find_similar_filenames(self, filename):
        """Find all files that appear to be duplicates of this filename based on naming pattern"""
        # Work with just the filename part, not the full path
        base, ext = os.path.splitext(filename.name)
        
        # Handle the case where the original file might have underscores
        # If this file ends in _N where N is a number, remove that to get the original base
        if '_' in base:
            parts = base.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                original_base = parts[0]
            else:
                original_base = base
        else:
            original_base = base
        
        # Find all files that are either:
        # 1. Exact match of the original base
        # 2. Original base followed by _N where N is a number
        similar_files = []
        for f in filename.parent.iterdir():
            if not f.is_file():
                continue
                
            f_base, f_ext = os.path.splitext(f.name)
            if f_ext.lower() != ext.lower():  # Must have same extension
                continue
                
            if f_base == original_base:  # Exact match
                similar_files.append(f)
            elif '_' in f_base:  # Possible _N suffix
                f_parts = f_base.rsplit('_', 1)
                if len(f_parts) == 2 and f_parts[0] == original_base and f_parts[1].isdigit():
                    similar_files.append(f)
        
        return similar_files

    def dedupe_album(self, album_dir, thorough=False):
        """Find and remove exact duplicates in an album directory"""
        album_dir = Path(album_dir)
        if not album_dir.is_dir():
            return 0
        
        processed = set()
        removed = 0
        
        # Get server count if available (for informational purposes only)
        server_count = None
        try:
            albums = self.get_albums()
            for album in albums:
                if self.sanitize_filename(album['name']) == album_dir.name:
                    server_count = album['photo_count']
                    break
        except:
            pass  # Ignore errors, we'll proceed without server count
        
        local_count = len([f for f in album_dir.iterdir() if f.is_file()])
        
        # Skip if we don't have more files than we should (unless in thorough mode)
        if not thorough and server_count is not None and local_count <= server_count:
            print(f"Skipping {album_dir.name}: has {local_count} files, should have {server_count}")
            return 0
        
        if server_count is not None:
            print(f"Checking {album_dir.name}: has {local_count} files, should have {server_count}")
        else:
            print(f"Checking {album_dir.name}: has {local_count} files")
        
        for filepath in album_dir.iterdir():
            if not filepath.is_file() or filepath in processed:
                continue
            
            similar_files = self.find_similar_filenames(filepath)
            if len(similar_files) > 1:  # We found potential duplicates
                # Compare all files regardless of size
                files_to_remove = set()
                for i, file1 in enumerate(similar_files):
                    for file2 in similar_files[i+1:]:  # Compare with all subsequent files
                        if file2 not in files_to_remove:  # Skip if already marked for removal
                            is_different, diff_type = self.files_are_different(file1, file2)
                            if not is_different:  # Files are identical
                                # Keep the one with the shorter name
                                keep_file = min(file1, file2, key=lambda f: len(f.name))
                                remove_file = file2 if keep_file == file1 else file1
                                print(f"Removing duplicate: {remove_file.name} (identical to {keep_file.name})")
                                files_to_remove.add(remove_file)
                            else:
                                diff_msg = {
                                    'size': 'different file size',
                                    'content': 'different content',
                                    'pixels': 'different image content'
                                }.get(diff_type, 'unknown difference')
                                print(f"Keeping both {file1.name} and {file2.name} ({diff_msg})")
                
                # Remove all duplicates found
                for file_to_remove in files_to_remove:
                    file_to_remove.unlink()
                    removed += 1
                
                processed.update(similar_files)
            else:
                processed.add(filepath)
        
        # Print summary for this album if we found and removed duplicates
        if removed > 0:
            new_count = len([f for f in album_dir.iterdir() if f.is_file()])
            print(f"\nRemoved {removed} duplicates from {album_dir.name}")
            print(f"Album now has {new_count} files")
            if server_count is not None:
                if new_count < server_count:
                    print(f"Warning: Album still missing {server_count - new_count} photos")
                elif new_count > server_count:
                    print(f"Warning: Album has {new_count - server_count} extra photos")
                else:
                    print("Album now has the correct number of photos")
        
        return removed

    def dedupe_all(self, thorough=False):
        """Run deduplication across all album directories"""
        print("\nChecking for duplicates...")
        if thorough:
            print("Running in thorough mode: checking all albums")
        else:
            print("Running in quick mode: only checking albums that might have duplicates")
        
        total_removed = 0
        albums_processed = 0
        albums_with_dupes = 0
        albums_skipped = 0
        
        for album_dir in sorted(self.output_dir.iterdir()):
            if album_dir.is_dir():
                removed = self.dedupe_album(album_dir, thorough)
                if removed > 0:
                    albums_with_dupes += 1
                    total_removed += removed
                elif removed == 0 and not thorough:
                    albums_skipped += 1
                albums_processed += 1
        
        print(f"\nDeduplication complete!")
        if not thorough:
            print(f"Skipped {albums_skipped} albums with correct or fewer files than expected")
        if total_removed > 0:
            print(f"Found duplicates in {albums_with_dupes} out of {albums_processed - albums_skipped} checked albums")
            print(f"Removed {total_removed} duplicate files")
        else:
            print("No exact duplicates found")
        
        return total_removed

def main():
    """Main entry point with argument handling"""
    parser = argparse.ArgumentParser(description='Download or count Shutterfly albums and photos')
    parser.add_argument('--token', '-t', help='Shutterfly access token')
    parser.add_argument('--output-dir', '-o', default='shutterfly_photos', 
                       help='Output directory for downloaded photos')
    parser.add_argument('--rate-limit', '-r', type=float, default=0.1,
                       help='Rate limit delay between requests in seconds')
    parser.add_argument('--parallel-workers', '-p', type=int, default=1,
                        help='Rate limit delay between requests in seconds')
    parser.add_argument('--count-only', '-c', action='store_true',
                       help='Only count albums and photos without downloading')
    parser.add_argument('--resume-from', help='Resume downloading from this album name')
    parser.add_argument('--compare', action='store_true',
                       help='Compare local downloads with server data')
    parser.add_argument('--album', '-a', help='Download a single album by name')
    parser.add_argument('--fix-incomplete', action='store_true',
                       help='Redownload all albums with missing photos')
    parser.add_argument('--ignore-albums', nargs='+', help='List of album names to ignore')
    parser.add_argument('--dedupe', action='store_true',
                       help='Find and remove exact duplicate photos (keeps files with different content)')
    parser.add_argument('--thorough', action='store_true',
                       help='When deduping, check all albums even if they have the correct number of files')
    
    args = parser.parse_args()
    
    # Get token from argument or environment or prompt
    token = args.token or os.environ.get('SHUTTERFLY_TOKEN')
    if not token and not args.dedupe:  # Only need token if not just deduping
        token = input("Enter Shutterfly access token: ").strip()
    
    downloader = ShutterflyDownloader(
        access_token=token,
        output_dir=args.output_dir,
        rate_limit_delay=args.rate_limit,
        ignore_albums=args.ignore_albums,
        max_parallel_workers=args.parallel_workers
    )
    
    if args.dedupe:
        downloader.dedupe_all(thorough=args.thorough)
    elif args.count_only:
        num_albums, num_photos = downloader.count_items()
    elif args.compare:
        downloader.compare_local_vs_server()
    elif args.fix_incomplete:
        print("\nStarting redownload of incomplete albums...")
        total_successful, total_failed = downloader.redownload_incomplete_albums()
        print(f"\nRedownload complete!")
        print(f"Total successfully downloaded: {total_successful}")
        print(f"Total failed downloads: {total_failed}")
    elif args.album:
        print("\nStarting single album download...")
        total_successful, total_failed = downloader.download_single_album(args.album)
        print(f"\nDownload complete!")
        print(f"Total successfully downloaded: {total_successful}")
        print(f"Total failed downloads: {total_failed}")
    else:
        print("\nStarting download...")
        total_successful, total_failed = downloader.download_all_albums(resume_from=args.resume_from)
        print(f"\nDownload complete!")
        print(f"Total successfully downloaded: {total_successful}")
        print(f"Total failed downloads: {total_failed}")

if __name__ == "__main__":
    main()