import requests
import subprocess
import threading
import queue
import time
from datetime import datetime
import os

def search_youtube(query, radio_mode=False):
    """Search YouTube for audio tracks"""
    try:
        api_key = os.getenv('YOUTUBE_API_KEY')
        if not api_key:
            print("Error: YOUTUBE_API_KEY not set")
            return None

        params = {
            'part': 'snippet',
            'q': f"{query} audio",
            'type': 'video',
            'maxResults': 5 if radio_mode else 1,
            'key': api_key,
            'videoCategoryId': '10',
            'videoDuration': 'medium',
            'order': 'relevance'
        }

        response = requests.get('https://www.googleapis.com/youtube/v3/search', params=params)
        data = response.json()
        
        if 'items' not in data or not data['items']:
            print("No results found on YouTube")
            return None

        base_url = "https://www.youtube.com/watch?v="
        if radio_mode:
            tracks = []
            for item in data['items']:
                try:
                    video_id = item['id']['videoId']
                    title = item['snippet']['title']
                    tracks.append({"url": base_url + video_id,
                                 "title": title})
                except KeyError:
                    continue
            return tracks if tracks else None
        else:
            try:
                video_id = data['items'][0]['id']['videoId']
                title = data['items'][0]['snippet']['title']
                return {"url": base_url + video_id,
                        "title": title}
            except (KeyError, IndexError):
                print("Error extracting video information from YouTube response")
                return None

    except Exception as e:
        print(f"Error searching YouTube: {str(e)}")
        return None

def play_track(track_info):
    """Play YouTube track with progress display"""
    process = None
    try:
        process = subprocess.Popen(["mpv", "--no-video", "--quiet", track_info['url']],
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)

        def check_for_quit(q):
            while True:
                try:
                    # Check for user input
                    if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                        q.put(True)
                        return
                    # Check if process has ended
                    if process.poll() is not None:
                        q.put(True)
                        return
                except:
                    pass

        q = queue.Queue()
        t = threading.Thread(target=check_for_quit, args=(q,))
        t.daemon = True
        t.start()

        def get_duration():
            try:
                output = subprocess.check_output(["mpv", "--no-video", "--quiet", "--format=duration", "--frames=0", track_info['url']],
                                               stderr=subprocess.STDOUT)
                return float(output.strip())
            except:
                return 300

        duration = get_duration()
        start_time = time.time()

        while process.poll() is None:
            try:
                elapsed = int(time.time() - start_time)
                current = datetime.fromtimestamp(elapsed).strftime('%M:%S')
                progress = int((elapsed / duration) * 50)
                bar = '█' * progress + '░' * (50 - progress)
                
                title = track_info['title'][:50] + '...' if len(track_info['title']) > 50 else track_info['title']
                progress = f"\r{title} - {current} | {bar} | {elapsed} seconds"
                print(progress, end='')
                time.sleep(0.5)

                # Check for quit signal
                if not q.empty():
                    process.terminate()
                    break
            except KeyboardInterrupt:
                process.terminate()
                break
            except Exception as e:
                print(f"\nError: {str(e)}")
                process.terminate()
                break

        q.put(True)
        t.join()

    except Exception as e:
        print(f"\nError playing track: {str(e)}")
        if process:
            try:
                process.terminate()
            except:
                pass
    finally:
        if process:
            try:
                process.terminate()
            except:
                pass

def main():
    print("\nWelcome to the Music Streamer!")
    print("Type a song name to play it")
    print("Type 'r' to start radio mode")
    print("Type 'q' to quit\n")

    while True:
        user_input = input("\nEnter song name, 'r' for radio, or 'q' to quit: ").strip()

        if user_input.lower() == 'q':
            print("\nGoodbye!")
            break

        if user_input.lower() == 'r':
            print("\nStarting radio mode...")
            print("Type 'q' at any time to stop radio mode\n")

            search_term = input("Enter a search term for radio: ").strip()
            if not search_term:
                continue

            tracks = search_youtube(search_term, radio_mode=True)
            if not tracks:
                print("\nNo tracks found. Returning to main menu.")
                continue

            for track in tracks:
                print(f"\nPlaying now: {track['title']}")
                play_track(track)
                
                # Check if user wants to quit after each song
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    if input().lower() == 'q':
                        break

        else:
            track_info = search_youtube(user_input)
            if track_info:
                print(f"\nPlaying: {track_info['title']}")
                play_track(track_info)
            else:
                print("\nNo track found. Try a different search term.")

if __name__ == "__main__":
    main()
