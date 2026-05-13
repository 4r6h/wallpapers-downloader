# WallpapersCraft Downloader

A powerful Python-based downloader for wallpapers from WallpapersCraft with support for:

- Multiple categories & resolutions
- Interactive and CLI modes
- Automatic caching (24h)
- Persistent retry system for failed downloads
- Page ranges or full category downloads
- Organized folder structure

---

# Features

- Fetches live categories and resolutions automatically
- Downloads wallpapers in original selected resolution
- Supports downloading:
  - Single page
  - Page ranges
  - Entire categories
- Smart caching system to reduce requests
- Automatic retry handling for temporary failures
- Saves failed downloads for later retry
- Works in both:
  - Interactive mode
  - Command-line mode

---

# Requirements

Install dependencies:

```bash
pip install requests beautifulsoup4
```

Python version:

```bash
Python 3.8+
```

---

# Installation

Clone or download the script:

```bash
git clone https://github.com/yourusername/wallpaperscraft-downloader.git
cd wallpaperscraft-downloader
```

Or simply save the script as:

```bash
wallpaperscraft_downloader.py
```

---

# Usage

## Interactive Mode

Run without arguments:

```bash
python wallpaperscraft_downloader.py
```

You will be prompted to choose:

- Resolution(s)
- Category(s)
- Page options

---

# CLI Mode

## Download specific page

```bash
python wallpaperscraft_downloader.py -r 1920x1080 -c nature -p 1
```

---

## Download page range

```bash
python wallpaperscraft_downloader.py -r 1920x1080 -c anime -p 1-5
```

---

## Download all pages

```bash
python wallpaperscraft_downloader.py -r 1920x1080 -c cars -p all
```

---

## Multiple resolutions and categories

```bash
python wallpaperscraft_downloader.py \
-r 1920x1080,2560x1440 \
-c nature,anime \
-p 1-3
```

---

# Retry Failed Downloads

Enable persistent retry mode:

```bash
python wallpaperscraft_downloader.py \
-r 1920x1080 \
-c nature \
-p 1 \
--retry
```

Features:

- Retries temporary failures forever
- Skips permanent HTTP errors automatically
- Stops only when all files succeed or user presses `Ctrl+C`

---

# Cache System

Cache location:

```bash
~/.cache/wallpaperscraft_downloader/cache.json
```

Cache duration:

```bash
24 hours
```

Disable cache:

```bash
python wallpaperscraft_downloader.py --no-cache
```

---

# Output Directory

Default output folder:

```bash
./crafts/
```

Example:

```bash
crafts/nature/
crafts/anime/
crafts/cars/
```

---

# Custom Output Directory

Set custom folder using environment variable:

## Linux/macOS

```bash
export WALLCRAFT_DIR="/path/to/wallpapers"
```

## Windows (PowerShell)

```powershell
$env:WALLCRAFT_DIR="D:\Wallpapers"
```

---

# Failed Downloads

Temporary failed downloads are saved to:

```bash
crafts/failed_downloads.txt
```

Format:

```text
URL -> destination_path
```

---

# Command Line Arguments

| Argument | Description |
|---|---|
| `-r`, `--resolution` | Resolution(s), comma separated |
| `-c`, `--category` | Category(s), comma separated |
| `-p`, `--page` | Page number, range, or `all` |
| `--retry` | Retry failed downloads forever |
| `--no-cache` | Force live data fetch |

---

# Example Commands

## Download nature wallpapers

```bash
python wallpaperscraft_downloader.py \
-r 2560x1440 \
-c nature \
-p all
```

---

## Download anime wallpapers from pages 1–10

```bash
python wallpaperscraft_downloader.py \
-r 1920x1080 \
-c anime \
-p 1-10
```

---

## Download mobile wallpapers

```bash
python wallpaperscraft_downloader.py \
-r 1080x1920 \
-c abstract \
-p all
```

---

# Notes

- Some wallpapers may return:
  - 403
  - 404
  - 410

These are automatically skipped as permanent failures.

- The downloader replaces preview resolutions (`300x168`) with the selected resolution automatically.

---

# License

MIT License

---

# Disclaimer

This project is for educational and personal use only.

Please respect the terms of service of WallpapersCraft and the rights of wallpaper creators.

