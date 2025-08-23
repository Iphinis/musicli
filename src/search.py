import yt_dlp
from fzf import fzf_select
import readline
from download import Download
from player import Player
from settings import Settings
from utils import *

class Search:
    def __init__(self, library, player:Player=Player(), playlist:str=None):
        """
        library: instance of Library for playlist selection and path management
        player: object with a .play(url: str) method for playback
        """
        self.library = library
        self.player = player
        self.playlist = playlist

        self.last_query = ''
        self.results_cache = []
        self.downloader = Download(output_dir=Settings.get('library', 'root_path'))

        self._play_text = "Play"
        self._download_text = "Download"
        self._back_text = "[ Back ]"

    def _input_with_placeholder(self, placeholder: str) -> str:
        """Prefill input with last query as placeholder"""
        def hook():
            readline.insert_text(placeholder)
            readline.redisplay()
        readline.set_pre_input_hook(hook)
        try:
            return input("Search for a track: ").strip()
        finally:
            readline.set_pre_input_hook()

    def search_youtube(self, query: str, max_results: int = 10) -> list[dict]:
        """Search YouTube for a query, with simple caching"""
        if query == self.last_query and self.results_cache:
            return self.results_cache
        opts = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'default_search': 'ytsearch',
            'extract_flat': True
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
        entries = info.get('entries') or []
        self.last_query = query
        self.results_cache = entries
        return entries

    def get_stream_url(self, video_id: str) -> str:
        """Get the direct audio stream URL for a video ID"""
        with yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'quiet': False}) as ydl:
            info = ydl.extract_info(video_id, download=False)
        return info['url']

    def play_entry(self, entry: dict):
        """Playback via injected player"""
        url = self.get_stream_url(entry['id'])
        print(f"Playing: {entry['title']}", flush=True)
        self.player.play_url(url)

    def format_entry(self, e: dict) -> str:
        title = e.get('title', 'Unknown')
        author = e.get('channel') or e.get('uploader') or 'Unknown'
        dur = int(e.get('duration') or 0); m, s = divmod(dur, 60)
        url = e.get('webpage_url') or f"https://youtu.be/{e.get('id')}"
        return f"{title} <{author}> ({url} - {m}:{s:02d})"

    def run(self):
        while True:
            try:
                query = self._input_with_placeholder(self.last_query)
            except (EOFError, KeyboardInterrupt):
                print("Exiting...", flush=True)
                break
            if not query:
                continue

            entries = self.search_youtube(query)
            if not entries:
                print("No results found.", flush=True)
                continue

            while True:
                options = [self.format_entry(e) for e in entries]
                sel = fzf_select(options, multi=True,
                                 prompt="Select tracks (TAB select, ENTER to back): ")
                if not sel:
                    break

                items = [e for line in sel for e in entries if e['id'] in line]
                if not items:
                    continue

                # multiple selected: batch download
                if len(items) > 1:
                    if not self.playlist:
                        self.playlist = self.library.select_playlist(custom_actions=False)
                    
                    print(f"Downloading {len(items)} tracks to '{self.playlist}'...", flush=True)
                    for it in items:
                        url = it.get('webpage_url') or f"https://youtu.be/{it['id']}"
                        filename = it['title'].replace('/', '_') + '.flac'
                        saved = self.downloader.download_url(
                            url,
                            subfolder=self.playlist,
                            filename=filename
                        )
                        print(f"Saved to {saved}", flush=True)
                    print("All downloads complete.", flush=True)
                    input("Press Enter to continue... ")
                    continue

                # single item: choose action
                entry = items[0]
                action = fzf_select([self._play_text, self._download_text, self._back_text],
                                     multi=False, prompt="Action: ")
                if not action or action[0] == self._back_text:
                    continue
                if action[0] == self._play_text:
                    self.play_entry(entry)
                    input("Press Enter to continue... ")
                elif action[0] == self._download_text:
                    if not self.playlist:
                        self.playlist = self.library.select_playlist(custom_actions=False)

                    url = entry.get('webpage_url') or f"https://youtu.be/{entry['id']}"
                    filename = entry['title'].replace('/', '_')
                    saved = self.downloader.download_url(
                        url,
                        subfolder=self.playlist,
                        filename=filename
                    )
                    print(f"Saved to {saved}", flush=True)
                    input("Press Enter to continue... ")
