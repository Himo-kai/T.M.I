# The Music

A terminal-based music streaming application that lets you play songs directly from YouTube.

## Features

- Search and play individual songs
- Radio mode that plays a sequence of songs based on a search term
- Live progress display with song title and playback time
- Clean, minimal interface
- Uses YouTube as a music source

## Requirements

- Python 3
- [mpv](https://mpv.io/) (system package)
- YouTube API key (free from Google Cloud Console)

## Setup

```bash
# Install requirments
pip install -r requirements.txt

# Install system dependencies
sudo pacman -S mpv

# Set up YouTube API key
export YOUTUBE_API_KEY='your_api_key_here'

# Run the application
python3 the_music.py
```

## Usage

1. Run the application:

```bash
python3 the_music.py
```

1. Use these commands:

- Type a song name to play it
- Type 'r' to start radio mode
- Type 'q' to quit

## Notes

- This project uses YouTube as a music source. Please respect YouTube's terms of service.
- No music is downloaded; audio is streamed live.
- You'll need a YouTube API key to use this application.
