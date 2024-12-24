# Shutterfly Album Downloader

This is a Python script that downloads all albums & photos from Shutterfly for a given user using the Shutterfly's unofficial site API. It supports rate limiting, exponential backoff, and retries. It also supports supplying a new access token mid-download (tokens expire after 1 hour). All you need is an access token you can obtain [like this](#getting-a-token).

This script does not use the Shutterfly API, it uses the site's backend API. The site API is not documented and may change at any time, which could break this script. I reverse engineered it from the site's network traffic, and made some assumptions about the structure of the data that have held up so far, but there's no guarantee that they'll work for every user.

## Requirements

- Python 3.9 or later
- Shutterfly access token

## Installation

1. Clone the repository (no need to install pipenv, no dependencies)
2. Insert your Shutterfly API access token [get like this](#getting-a-token) into the `downloader.py` file (line 195) 3. Run the script:

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