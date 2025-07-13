# Shutterfly Album Downloader

This is a Python script that downloads all albums & photos from Shutterfly for a given user using the Shutterfly's unofficial site API. It supports rate limiting, exponential backoff, and retries. It also supports supplying a new access token mid-download (tokens expire after 1 hour). All you need is an access token you can obtain [like this](#getting-a-token).

This script does not use the Shutterfly API, it uses the site's backend API. The site API is not documented and may change at any time, which could break this script. I reverse engineered it from the site's network traffic, and made some assumptions about the structure of the data that have held up so far, but there's no guarantee that they'll work forever.

It might take some massaging to get it working for your account/use-case, as everyone stores their photos differently. I built it for my girlfriend's mom, who's photos are being held ransom by Shutterfly as they make her buy something every year so they don't delete them off their servers. This would be understandable, except they don't offer a good way to bulk download them so I figured I'd build this. If you're here, chances are you're in a similar situation; this script should help if you want a head start on getting your photos off Shutterfly.

## Requirements

- Python 3.9 or later
- Pipenv
- Shutterfly access token

## Installation

1. Clone the repository
2. Install pipenv
3. Run `pipenv install` to install the dependencies
4. Inject your Shutterfly API access token [get like this](#getting-a-token) into the env:

```bash
export SHUTTERFLY_TOKEN=your_token_here
```

5. Run the script:

```bash
python downloader.py
```

6 (conditional): If your account is pre-2013ish, you'll need to set the `LIFE_UID` environment variable to your account's UID. You can find it in the URL of your account's page on shutterfly.com or in various requests:

```bash
export LIFE_UID=your_uid_here
```

They switched over to the new user ID scheme when they acquired "ThisLife" in 2013 and migrated their whole photo system. I found it easy to manage both of these in a single `.env` file in the root of the repo.

## Notes

- The script will download all albums & photos for the given user.
- The script will pause, prompt for a new access token, and resume downloading if the access token expires.
- The script will retry downloading if the download fails.
- The script will back off exponentially if the rate limit is exceeded.
- The script will save the downloaded photos to the `shutterfly_photos` directory.
- The script will print the total number of photos downloaded.

## Getting a token

To use this script, you need a Shutterfly access token. This token is required for all operations except deduplication. The token typically lasts for 1 hour, after which you will need to supply a new one.

### How to obtain your token

1. Log in to the Shutterfly website in your browser.
2. Open the browser's Developer Tools (usually F12 or right-click → Inspect).
3. Go to the Network tab.
4. Navigate to "My Photos".
5. Click the trash can in Developer Tools Network tab.
6. Click on "Albums".
7. Look for a network request to `cmd.thislife.com/json?method=album.getAlbums`.
8. Click on the request and check the **Request Data** section. The access token will appear as the first parameter in the "params" array (a long string starting with "eyJ").
9. Copy the entire token string (it may look like a long string of letters, numbers, and sometimes dots).

### How to provide the token to the script

You can provide the token in several ways:

- **Command line argument:**
  ```bash
  python downloader.py --token YOUR_TOKEN
  # or
  python downloader.py -t YOUR_TOKEN
  ```
- **Environment variable:**
  ```bash
  export SHUTTERFLY_TOKEN=your_token_here
  python downloader.py
  ```
- **Prompt:**
  If you do not provide a token via the above methods, the script will prompt you to paste it when needed.
- **Environment file (.env):**
  Create a `.env` file in the script's directory with:
  ```
  SHUTTERFLY_TOKEN=your_token_here
  ```
  Then run the script normally.

### Refreshing the token during long downloads

If your token expires during a download, the script will pause and prompt you for a new token. You can:

1. Obtain a new token using the browser steps above.
2. Save the new token in a file named `token.txt` in the script's directory. The script will automatically read and use this token when prompted, then delete the file for security.
3. Alternatively, you can paste the new token directly into the terminal when prompted.

### Token formats

- The script supports both JWT (tokens with dots, e.g., `xxxxx.yyyyy.zzzzz`) and non-JWT (base64 or URL-encoded) token formats.
- The script will attempt to decode and validate the token, and will alert you if the format is invalid.

**Note:** The token is required for all operations except deduplication (`--dedupe`).

## Usage

You can run the script in many different modes. The main is downloading:

```bash
python downloader.py
```

Though I find it easiest to use in this order:

1. First just count to understand the scope and how much time it will take with whatever rate limit you want to use:

```bash
python downloader.py --count-only
```

2. Run it in regular mode until it breaks or something happens. Refresh the token if it prompts you, easiest way is to put it in a `token.txt` file. Note the album that it stops on if it stops:

```bash
python downloader.py
```

3. For faster downloads, specify a maximum number of parallel downloads (the default is 1 - no parallel downloads). This has been safely tested up to 50.

```bash
python downloader.py --parallel-workers 50
```

4. If it stopped and you want to resume:

```bash
python downloader.py --resume-from <album name>
```

5. If you can't remember where it stopped, get some stats on local vs remote:

```bash
python downloader.py --compare
```

6. After it finishes, do a full pass and redownload all incomplete albums (sometimes photos or albums just failed at some point when you weren't watching):

```bash
python downloader.py --fix-incomplete
```

7. You can give it a full dedupe to make sure you don't have duplicates:

```bash
python downloader.py --dedupe --thorough
```

### Command Line Options

- `--token` or `-t`: Shutterfly access token (can also be set via SHUTTERFLY_TOKEN environment variable)
- `--output-dir` or `-o`: Output directory for downloaded photos (default: shutterfly_photos)
- `--rate-limit` or `-r`: Rate limit delay between requests in seconds (default: 1.0, but I often used 0.0 and never got throttled)
- `--count-only` or `-c`: Only count albums and photos without downloading
- `--compare`: Compare local downloads with server data to identify missing or incomplete albums
- `--album` or `-a`: Download a single album by name
- `--fix-incomplete`: Redownload all albums that have missing photos (overwrites existing files)
- `--resume-from`: Resume downloading from a specific album name
- `--ignore-albums`: Space-separated list of album names to ignore during download
- `--parallel-workers` or `-p`: Maximum parallel downloads (default: 1, tested up to 50)
- `--dedupe`: Find and remove exact duplicate photos while preserving files with different content
- `--thorough`: When deduping, check all albums even if they have the correct number of files

Examples:

```bash
# Download with custom output directory, parallel downloads, and rate limit
python downloader.py -t YOUR_TOKEN -o my_photos -p 50 -r 0.5

# Just count albums and photos
python downloader.py -t YOUR_TOKEN --count-only

# Compare local downloads with server data
python downloader.py -t YOUR_TOKEN --compare

# Download a single album
python downloader.py -t YOUR_TOKEN --album "My Vacation Photos"

# Redownload all incomplete albums
python downloader.py -t YOUR_TOKEN --fix-incomplete

# Resume download from a specific album (albums are processed alphabetically so order is the same every time you run the script)
python downloader.py -t YOUR_TOKEN --resume-from "Vacation 2023"

# Ignore specific albums during download
python downloader.py -t YOUR_TOKEN --ignore-albums "Test Album" "Duplicates"

# Find and remove duplicate photos
python downloader.py --dedupe

# Thorough duplicate check across all albums
python downloader.py --dedupe --thorough

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

## Deduplication

The `--dedupe` option helps you find and remove duplicate photos while preserving unique content:

- Compares files by size, content, and pixel data for images
- Preserves files that have the same name but different content
- Reports statistics about duplicates found
- Can run in thorough mode (`--thorough`) to check all albums regardless of photo count

The deduplication process:

1. First checks file names for approximate matches (e.g. "IMG_1234.jpg" and "IMG_1234 1.jpg")
2. First checks file sizes (fast comparison)
3. If sizes match, compares file contents
4. For image files, compares actual pixel data
5. Handles EXIF orientation correctly
6. Provides detailed statistics about types of duplicates found
