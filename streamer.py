import subprocess
import sys
import os
import json
import random
from time import sleep

# Ensure yt-dlp and mpv are installed
def check_dependencies():
    missing = []
    for cmd in ["yt-dlp", "mpv"]:
        if subprocess.call(["which", cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            missing.append(cmd)
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Please install them with:\n  sudo apt install mpv\n  pip install yt-dlp")
        sys.exit(1)

HIST_FILE = "history.json"
FAV_FILE = "favorites.json"

def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

def add_to_history(track):
    hist = load_json(HIST_FILE)
    if not hist or hist[-1]['url'] != track['url']:
        hist.append(track)
        if len(hist) > 100:
            hist = hist[-100:]
        save_json(HIST_FILE, hist)

def add_to_favorites(track):
    favs = load_json(FAV_FILE)
    if not any(f['url'] == track['url'] for f in favs):
        favs.append(track)
        save_json(FAV_FILE, favs)

def remove_from_favorites(idx):
    favs = load_json(FAV_FILE)
    if 0 <= idx < len(favs):
        favs.pop(idx)
        save_json(FAV_FILE, favs)

def show_tracks(tracks, title, console):
    from rich.table import Table
    if not tracks:
        console.print(f"[yellow]{title} is empty.[/yellow]")
        return
    table = Table(title=title, show_lines=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Title", style="bold")
    table.add_column("Duration", style="magenta")
    
    for idx, track in enumerate(tracks):
        duration = f"{track['duration']//60}:{str(track['duration']%60).zfill(2)}" if track['duration'] else "?"
        table.add_row(str(idx+1), track['title'], duration)
    
    console.print(table)

def search_youtube(query, num_results=10):
    """Search YouTube and return a list of dicts: {title, url, duration} (if available)."""
    import yt_dlp
    ydl_opts = {'quiet': True, 'skip_download': True, 'extract_flat': 'in_playlist'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search = f"ytsearch{num_results}:{query}"
        info = ydl.extract_info(search, download=False)
        results = []
        if 'entries' in info and len(info['entries']) > 0:
            for entry in info['entries']:
                title = entry.get('title', 'Unknown Title')
                url = "https://www.youtube.com/watch?v=" + entry['id']
                duration = entry.get('duration')
                results.append({'title': title, 'url': url, 'duration': duration})
        return results

def get_audio_url(video_url):
    """Get direct audio stream URL and metadata from YouTube video."""
    import yt_dlp
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            audio_url = info['url']
            title = info.get('title', 'Unknown Title')
            duration = info.get('duration', None)
            artist = info.get('artist') or info.get('uploader', '')
            return audio_url, title, duration, artist
    except Exception as e:
        return None, None, None, None

def play_audio_with_controls_rich(audio_url, title, duration, artist, control_state, console):
    """Play audio using mpv with keyboard controls and rich UI. Uses curses for key input. Adds volume control."""
    import threading
    import curses
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from time import sleep

    def run_mpv():
        proc = subprocess.Popen(["mpv", "--no-video", audio_url], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        control_state['proc'] = proc
        proc.wait()
        control_state['playing'] = False

    def send_mpv_command(cmd):
        proc = control_state.get('proc')
        if proc and proc.stdin:
            try:
                proc.stdin.write((cmd + '\n').encode())
                proc.stdin.flush()
            except Exception:
                pass

    def curses_key_listener(stdscr):
        stdscr.nodelay(True)
        while control_state['playing']:
            try:
                key = stdscr.getch()
                if key == ord('p'):
                    if control_state['paused']:
                        if control_state['proc']:
                            control_state['proc'].send_signal(subprocess.signal.SIGCONT)
                        control_state['paused'] = False
                        control_state['status_msg'] = "[green]Resumed.[/green]"
                    else:
                        if control_state['proc']:
                            control_state['proc'].send_signal(subprocess.signal.SIGSTOP)
                        control_state['paused'] = True
                        control_state['status_msg'] = "[yellow]Paused.[/yellow]"
                elif key == ord('n'):
                    if control_state['proc']:
                        control_state['proc'].terminate()
                    control_state['skip'] = True
                    control_state['status_msg'] = "[cyan]Skipped.[/cyan]"
                    break
                elif key == ord('q'):
                    if control_state['proc']:
                        control_state['proc'].terminate()
                    control_state['quit'] = True
                    control_state['status_msg'] = "[red]Quitting...[/red]"
                    break
                elif key == ord('v'):
                    send_mpv_command('set volume +5')
                    control_state['status_msg'] = "[blue]Volume up[/blue]"
                elif key == ord('b'):
                    send_mpv_command('set volume -5')
                    control_state['status_msg'] = "[blue]Volume down[/blue]"
            except Exception:
                pass
            sleep(0.1)

    def render_panel():
        status = "[yellow]Paused[/yellow]" if control_state.get('paused') else "[green]Playing[/green]"
        msg = control_state.get('status_msg', "")
        dur = duration if duration else 0
        elapsed = control_state.get('elapsed', 0)
        if dur:
            progress = min(1.0, float(elapsed) / dur)
            bar_len = 30
            filled = int(progress * bar_len)
            bar = "[bold green]" + "█" * filled + "[/bold green]" + "─" * (bar_len - filled)
            prog_text = f"{int(elapsed)//60}:{str(int(elapsed)%60).zfill(2)} / {int(dur)//60}:{str(int(dur)%60).zfill(2)}"
        else:
            bar = ""
            prog_text = ""
        panel = Panel(
            Text.from_markup(
                f"[bold magenta]{title or 'Unknown Title'}[/bold magenta]" + (f"\n[white]{artist}[/white]" if artist else "") +
                f"\n\n[white]Controls:[/white] [b]p[/b]=pause/resume  [b]n[/b]=next/skip  [b]q[/b]=quit  [b]v[/b]=vol+  [b]b[/b]=vol-" +
                (f"\n\n[white]Progress:[/white] {bar} {prog_text}" if bar else "") +
                f"\n\nStatus: {status}\n{msg}"
            ),
            title="[bold cyan]Now Playing[/bold cyan]",
            border_style="bright_blue"
        )
        return panel

    control_state['playing'] = True
    control_state['paused'] = False
    control_state['skip'] = False
    control_state['quit'] = False
    control_state['proc'] = None
    control_state['status_msg'] = ""
    control_state['elapsed'] = 0

    t1 = threading.Thread(target=run_mpv)
    t1.start()
    def update_elapsed():
        elapsed = 0
        while control_state['playing']:
            sleep(1)
            if not control_state.get('paused'):
                elapsed += 1
            control_state['elapsed'] = elapsed
    t2 = threading.Thread(target=update_elapsed)
    t2.start()
    # Run curses in main thread for key listening
    def curses_main(stdscr):
        with Live(render_panel(), refresh_per_second=4, console=console):
            while control_state['playing']:
                curses_key_listener(stdscr)
                sleep(0.2)
    try:
        curses.wrapper(curses_main)
    except Exception as e:
        console.print(f"[red]Playback error: {e}[/red]")
    control_state['playing'] = False

def search_and_select(tracks, console):
    """Display a list of tracks and let user select one."""
    from rich.table import Table
    from rich.prompt import Prompt
    from rich.panel import Panel
    
    if not tracks:
        console.print("[red]No tracks found.[/red]")
        return None
    
    table = Table(title="Search Results", show_lines=True)
    table.add_column("#", style="cyan", width=3)
    table.add_column("Title", style="bold")
    table.add_column("Duration", style="magenta")
    
    for idx, track in enumerate(tracks):
        duration = f"{track['duration']//60}:{str(track['duration']%60).zfill(2)}" if track['duration'] else "?"
        table.add_row(str(idx+1), track['title'], duration)
    
    console.print(table)
    
    while True:
        choice = Prompt.ask("Select a track by number, or 'a' to add all to playlist, or 'q' to cancel", console=console).strip()
        if choice == 'q':
            return None
        if choice == 'a':
            return 'all'
        if choice.isdigit():
            idx = int(choice)-1
            if 0 <= idx < len(tracks):
                return idx
        console.print("[red]Invalid selection. Try again.[/red]")

def show_playlist(playlist, console):
    show_tracks(playlist, "Playlist", console)

def main():
    check_dependencies()
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.text import Text
    from rich.align import Align
    import random
    console = Console()

    playlist_shuffle = False
    playlist_repeat = False

    console.print(Panel(Align.center("[bold cyan]Terminal Music Streamer[/bold cyan]", vertical="middle"), style="bold magenta"))
    console.print("[green]Type 'radio <song/artist>' for radio mode (auto-play similar tracks)[/green]")
    console.print("[yellow]Or enter a song/artist to search and play.[/yellow]")
    playlist = []
    while True:
        status_str = f"[cyan]Commands: [bold]playlist[/bold] [bold]playall[/bold] [bold]remove <n>[/bold] [bold]clear[/bold] [bold]history[/bold] [bold]favorites[/bold] [bold]fav <n>[/bold] [bold]unfav <n>[/bold] [bold]playfav <n>[/bold] [bold]clearhistory[/bold] [bold]clearfavs[/bold] [bold]shuffle[/bold] [bold]repeat[/bold] [bold]q[/bold]uit | Shuffle: {'ON' if playlist_shuffle else 'OFF'} | Repeat: {'ON' if playlist_repeat else 'OFF'}[/cyan]"
        console.print(status_str)
        query = Prompt.ask("\n[bold]Enter search, command, or 'q' to quit[/bold]", console=console).strip()
        if query.lower() == 'q':
            break
        elif query.lower() == 'playlist':
            show_playlist(playlist, console)
            continue
        elif query.lower() == 'playall':
            if not playlist:
                console.print("[yellow]Playlist is empty.[/yellow]")
                continue
            play_list = playlist[:]
            if playlist_shuffle:
                random.shuffle(play_list)
            idx = 0
            while idx < len(play_list):
                track = play_list[idx]
                title = f"Track {idx+1}/{len(play_list)}\n{track['title']}"
                audio_url, title, duration, artist = get_audio_url(track['url'])
                if not audio_url:
                    console.print(f"[red]Error: Could not retrieve audio stream.[/red]")
                    idx += 1
                    continue
                control_state = {}
                play_audio_with_controls_rich(audio_url, title, duration, artist, control_state, console)
                add_to_history(track)
                if control_state.get('quit'):
                    break
                if control_state.get('skip'):
                    idx += 1
                    continue
                idx += 1
                if idx == len(play_list) and playlist_repeat:
                    idx = 0
            continue
        elif query.lower() == 'history':
            show_tracks(load_json(HIST_FILE), "History", console)
            continue
        elif query.lower() == 'favorites':
            show_tracks(load_json(FAV_FILE), "Favorites", console)
            continue
        elif query.lower().startswith('fav '):
            try:
                idx = int(query.split()[1]) - 1
                if 0 <= idx < len(playlist):
                    add_to_favorites(playlist[idx])
                    console.print(f"[yellow]Added to favorites:[/yellow] {playlist[idx]['title']}")
                else:
                    console.print("[red]Invalid track number in playlist.[/red]")
            except Exception:
                console.print("[red]Usage: fav <track_number> (from playlist)")
            continue
        elif query.lower().startswith('unfav '):
            try:
                idx = int(query.split()[1]) - 1
                favs = load_json(FAV_FILE)
                if 0 <= idx < len(favs):
                    removed = favs[idx]['title']
                    remove_from_favorites(idx)
                    console.print(f"[red]Removed from favorites:[/red] {removed}")
                else:
                    console.print("[red]Invalid favorite number.")
            except Exception:
                console.print("[red]Usage: unfav <fav_number>")
            continue
        elif query.lower().startswith('playfav '):
            try:
                idx = int(query.split()[1]) - 1
                favs = load_json(FAV_FILE)
                if 0 <= idx < len(favs):
                    track = favs[idx]
                    console.print(f"[green]Playing favorite:[/green] {track['title']}")
                    audio_url, title, duration, artist = get_audio_url(track['url'])
                    if not audio_url:
                        console.print(f"[red]Error: Could not retrieve audio stream.[/red]")
                        continue
                    control_state = {}
                    play_audio_with_controls_rich(audio_url, title, duration, artist, control_state, console)
                    add_to_history(track)
                else:
                    console.print("[red]Invalid favorite number.")
            except Exception:
                console.print("[red]Usage: playfav <fav_number>")
            continue
        elif query.lower() == 'clearhistory':
            save_json(HIST_FILE, [])
            console.print("[red]History cleared.[/red]")
            continue
        elif query.lower() == 'clearfavs':
            save_json(FAV_FILE, [])
            console.print("[red]Favorites cleared.[/red]")
            continue
        elif query.lower().startswith('remove '):
            try:
                idx = int(query.split()[1]) - 1
                if 0 <= idx < len(playlist):
                    removed = playlist.pop(idx)
                    console.print(f"[red]Removed:[/red] {removed['title']}")
                else:
                    console.print("[red]Invalid track number.")
            except Exception:
                console.print("[red]Usage: remove <track_number>")
            continue
        elif query.lower() == 'clear':
            playlist.clear()
            console.print("[red]Playlist cleared.[/red]")
            continue
        elif query.lower() == 'shuffle':
            playlist_shuffle = not playlist_shuffle
            console.print(f"[yellow]Shuffle: {'ON' if playlist_shuffle else 'OFF'}[/yellow]")
            continue
        elif query.lower() == 'repeat':
            playlist_repeat = not playlist_repeat
            console.print(f"[yellow]Repeat: {'ON' if playlist_repeat else 'OFF'}[/yellow]")
            continue
        elif query.lower().startswith('radio '):
            radio_query = query[6:].strip()
            if not radio_query:
                console.print("[red]Please provide a song or artist for radio mode.[/red]")
                continue
            # Enhanced radio with shuffle/repeat
            while True:
                tracks = search_youtube(radio_query, num_results=10)
                if not tracks:
                    console.print("[red]No results found.[/red]")
                    break
                play_list = tracks[:]
                if playlist_shuffle:
                    random.shuffle(play_list)
                idx = 0
                while idx < len(play_list):
                    track = play_list[idx]
                    title = f"Track {idx+1}/{len(play_list)}\n{track['title']}"
                    audio_url, title, duration, artist = get_audio_url(track['url'])
                    if not audio_url:
                        console.print(f"[red]Error: Could not retrieve audio stream.[/red]")
                        idx += 1
                        continue
                    control_state = {}
                    play_audio_with_controls_rich(audio_url, title, duration, artist, control_state, console)
                    add_to_history(track)
                    if control_state.get('quit'):
                        return
                    if control_state.get('skip'):
                        control_state['skip'] = False
                        idx += 1
                        continue
                    idx += 1
                    if idx == len(play_list) and playlist_repeat:
                        idx = 0
                break
            continue
        elif query.lower() == 'radio':
            console.print("[red]Please provide a song or artist for radio mode.[/red]")
            continue
        console.print(f"[blue]Searching YouTube for:[/blue] [bold]{query}[/bold]")
        tracks = search_youtube(query, num_results=10)
        if not tracks:
            console.print("[red]No results found.[/red]")
            continue
        selection = search_and_select(tracks, console)
        if selection is None:
            continue
        if selection == 'all':
            playlist.extend(tracks)
            console.print(f"[yellow]{len(tracks)} tracks added to playlist![/yellow]")
            continue
        track = tracks[selection]
        console.print(f"[green]Playing:[/green] {track['title']}")
        audio_url, title, duration, artist = get_audio_url(track['url'])
        if not audio_url:
            console.print(f"[red]Error: Could not retrieve audio stream.[/red]")
            continue
        control_state = {}
        play_audio_with_controls_rich(audio_url, title, duration, artist, control_state, console)
        add_to_history(track)

if __name__ == "__main__":
    main()
