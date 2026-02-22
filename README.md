# Shutterfly Album Downloader

A Python script that bulk-downloads all albums and photos from Shutterfly using their unofficial site API. Supports rate limiting, exponential backoff, retries, parallel downloads, deduplication, and mid-download token refresh.

I reverse-engineered this from the site's network traffic. It's not documented and may change at any time (Shutterfly is incentivized to prevent bulk downloads), but it has held up so far. If it breaks, open an issue.

I built it for my girlfriend's mom, whose photos are being held ransom by Shutterfly — they make her buy something every year or they delete them, and they don't offer a good way to bulk download. If you're here, chances are you're in a similar situation.

## Requirements

- Python 3.9+
- Pipenv (`pip install pipenv`)

## Quick Start

```bash
git clone https://github.com/JoshBurke/Shutterfly-Album-Downloader.git
cd Shutterfly-Album-Downloader
pipenv install
```

Then get your auth token (see below) and run:

```bash
export SHUTTERFLY_TOKEN=your_token_here
pipenv run python downloader.py --count-only   # see how many photos you have
pipenv run python downloader.py                 # download everything
```

## Authentication

You need a Shutterfly auth credential to use this script. There are two options:

### Option A: Access Token (Recommended)

The easiest method. Tokens last ~1 hour; the script will prompt you for a new one when it expires.

1. Log in to [photos.shutterfly.com](https://photos.shutterfly.com) in your browser.
2. Open Developer Tools (F12 or right-click → Inspect).
3. Go to the **Network** tab.
4. Navigate to **My Photos → Albums**.
5. Look for a request to `cmd.thislife.com/json?method=album.getAlbums`.
6. Click the request and look at the **Request Body** (or "Payload" tab). In the `params` array, the first value is your access token — a long string starting with `eyJ`.
7. Copy the entire token string.

```bash
export SHUTTERFLY_TOKEN=eyJr...your_full_token_here
```

For accounts created **before ~2013** (pre-ThisLife migration), the user ID in the token may differ from your actual Shutterfly UID. In that case you also need to set `LIFE_UID`:

```bash
export LIFE_UID=your_uid_here
```

You can find your `LIFE_UID` by looking at the `getAlbums` response payload in the Network tab — it appears in the album data under each album you created (typically starts with `100...`).

> **Tip:** If you're downloading a lot and don't want to keep refreshing tokens, you can save a new token to a file called `token.txt` in the script directory. The script will read it automatically when the current token expires.

### Option B: Session Cookie

Useful when you can't easily capture a JWT (SSO/corporate logins, mobile flows) or tokens keep expiring too fast.

1. Log in to [photos.shutterfly.com](https://photos.shutterfly.com).
2. Open Developer Tools → **Application** (Chrome) or **Storage** (Firefox) → Cookies.
3. Find the `_thislife_session` cookie for `photos.shutterfly.com`.
4. Copy its value.

```bash
export SHUTTERFLY_TOKEN="_thislife_session=your_cookie_value_here"
export LIFE_UID=your_uid_here   # Required for cookie auth
```

`LIFE_UID` is always required with cookie auth because the cookie doesn't contain it.

> **Note:** Treat both tokens and cookies like passwords — anyone with them can access your photos.

### Managing credentials

I found it easiest to put both values in a `.env` file in the repo root:

```
SHUTTERFLY_TOKEN=eyJr...
LIFE_UID=100123456789
```

The `.env` file is gitignored so it won't be committed.

## Usage

### Recommended workflow

1. **Count** — understand the scope:
   ```bash
   python downloader.py --count-only
   ```

2. **Download** — let it run. If the token expires, refresh it (easiest via `token.txt`):
   ```bash
   python downloader.py
   ```

3. **Speed up** — use parallel downloads (tested safely up to 50):
   ```bash
   python downloader.py --parallel-workers 50
   ```

4. **Resume** — if it stopped, pick up where you left off:
   ```bash
   python downloader.py --resume-from "Album Name"
   ```

5. **Compare** — check local vs server to find gaps:
   ```bash
   python downloader.py --compare
   ```

6. **Fix gaps** — redownload any incomplete albums:
   ```bash
   python downloader.py --fix-incomplete
   ```

7. **Dedupe** — remove exact duplicates:
   ```bash
   python downloader.py --dedupe --thorough
   ```

### All options

| Flag | Description | Default |
|------|-------------|---------|
| `--token`, `-t` | Auth token (or set `SHUTTERFLY_TOKEN` env var) | — |
| `--output-dir`, `-o` | Output directory | `shutterfly_photos` |
| `--rate-limit`, `-r` | Delay between requests (seconds) | `0.1` |
| `--parallel-workers`, `-p` | Max parallel downloads | `1` |
| `--count-only`, `-c` | Count albums/photos without downloading | — |
| `--compare` | Compare local downloads vs server | — |
| `--album`, `-a` | Download a single album by name | — |
| `--fix-incomplete` | Redownload albums with missing photos | — |
| `--resume-from` | Resume from a specific album name | — |
| `--ignore-albums` | Space-separated album names to skip | — |
| `--dedupe` | Find and remove duplicate photos | — |
| `--thorough` | Dedupe all albums (even correctly-sized ones) | — |

### Examples

```bash
# Custom output dir, parallel, with rate limit
python downloader.py -t YOUR_TOKEN -o my_photos -p 50 -r 0.5

# Download one album
python downloader.py --album "Vacation 2019"

# Ignore specific albums
python downloader.py --ignore-albums "Test Album" "Duplicates"

# Dedupe only (no token needed)
python downloader.py --dedupe --thorough
```

## Comparing Local and Server Data

The `--compare` option checks if your local downloads match the server:

- Compares photo counts per album
- Identifies missing or incomplete albums
- Finds local-only albums that don't exist on the server
- Handles filename sanitization (special characters) for accurate matching

## Deduplication

The `--dedupe` option removes exact duplicate photos while preserving unique content:

1. Finds files with similar names (e.g. `IMG_1234.jpg` and `IMG_1234_1.jpg`)
2. Compares file sizes (fast check)
3. If sizes match, compares raw file contents
4. For images, compares actual pixel data (handles EXIF orientation)
5. Only removes files that are truly identical — different content is always kept

Use `--thorough` to check all albums, even ones with the expected number of files.

## Testing

```bash
pipenv install --dev
pipenv run pytest
```

Tests cover request/response shapes, moment parsing, URL building, duplicate handling, compare output, and dedupe behavior. CI runs automatically on PRs via GitHub Actions.
