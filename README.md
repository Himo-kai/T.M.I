# T.M.I
Terminal Music Interface | play music with a simple Python terminal app to stream music from YouTube for free.

## Features
- Search for songs or artists
- Streams audio directly from YouTube
- Plays audio in your terminal using `mpv`

## Requirements
- Python 3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (Python package)
- [mpv](https://mpv.io/) (system package)

## Setup
```bash
sudo apt install mpv 
pip install -r requirements.txt
```

## Usage
```bash
python3 streamer.py
```

## Notes
- This project uses YouTube as a source. Respect YouTube's terms of service.
- No music is downloaded; audio is streamed live.
