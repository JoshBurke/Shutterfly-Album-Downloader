# Shutterfly Album Downloader

This is a Python script that downloads all albums & photos from Shutterfly for a given user using the Shutterfly's unofficial site API. It supports rate limiting, exponential backoff, and retries. It also supports supplying a new access token mid-download (tokens expire after 1 hour). All you need is an access token you can obtain [like this](#getting-a-token).

This script does not use the Shutterfly API, it uses the site's backend API. The site API is not documented and may change at any time, which could break this script. I reverse engineered it from the site's network traffic, and made some assumptions about the structure of the data that have held up so far, but there's no guarantee that they'll work for every user.

## Requirements

- Python 3.9 or later
- Pipenv
- Shutterfly access token

## Installation

1. Clone the repository
2. Install pipenv
3. Run `pipenv install` to install the dependencies
4. Insert your Shutterfly API access token [get like this](#getting-a-token) into the `downloader.py` file (line 195) 
5. Run the script:

```bash
python downloader.py
```

## Notes

- The script will download all albums & photos for the given user.
- The script will pause, prompt for a new access token, and resume downloading if the access token expires.
- The script will retry downloading if the download fails.
- The script will back off exponentially if the rate limit is exceeded.
- The script will save the downloaded photos to the `shutterfly_photos` directory.
- The script will print the total number of photos downloaded.

## Getting a token

You can get a token by logging into the Shutterfly site, opening the network tab in the browser's developer tools, navigating to the photos page, and finding the request that fetches the albums. The token is in the request headers. It lasts for 1 hour, so you may need to get a new one if you're downloading a lot of photos. The default rate limit is 1 request per second, but you can increase it in the `downloader.py` file (line 200).

## Usage

You can run the script in two modes:

1. Download mode (default):
```bash
python downloader.py --token YOUR_TOKEN
```

2. Count-only mode (doesn't download anything):
```bash
python downloader.py --token YOUR_TOKEN --count-only
```

### Command Line Options

- `--token` or `-t`: Shutterfly access token (can also be set via SHUTTERFLY_TOKEN environment variable)
- `--output-dir` or `-o`: Output directory for downloaded photos (default: shutterfly_photos)
- `--rate-limit` or `-r`: Rate limit delay between requests in seconds (default: 1.0)
- `--count-only` or `-c`: Only count albums and photos without downloading
- `--compare`: Compare local downloads with server data to identify missing or incomplete albums
- `--album` or `-a`: Download a single album by name
- `--fix-incomplete`: Redownload all albums that have missing photos (overwrites existing files)

Examples:
```bash
# Download with custom output directory and rate limit
python downloader.py -t YOUR_TOKEN -o my_photos -r 0.5

# Just count albums and photos
python downloader.py -t YOUR_TOKEN --count-only

# Compare local downloads with server data
python downloader.py -t YOUR_TOKEN --compare

# Download a single album
python downloader.py -t YOUR_TOKEN --album "My Vacation Photos"

# Redownload all incomplete albums
python downloader.py -t YOUR_TOKEN --fix-incomplete

# Use token from environment variable
export SHUTTERFLY_TOKEN=your_token_here
python downloader.py --count-only
```

## Comparing Local and Server Data

You can use the `--compare` option to check if your local downloads match what's on the server. This will:
- Compare the number of photos in each album
- Identify albums that are missing locally
- Find any local albums that don't exist on the server
- Show total photo count differences

The comparison takes into account filename sanitization (removal of special characters) to ensure accurate matching between local and server album names.