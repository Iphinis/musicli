"""search_file.py"""
import readline
from sanitize_filename import sanitize
from urllib.parse import urlparse
from fzf import fzf_select

from player import Player
from search import Search

class SearchFile(Search):
    """
    Search and download audio files from a text file (url or query). Extends from Search.

    File's format:
    input1
    .
    .
    .
    inputn
    """
    def __init__(self, library, player:Player=Player(), playlist:str=None):
        super().__init__(library, player, playlist)

    def _input_with_placeholder(self, placeholder: str) -> str:
        """Prefill input with last path as placeholder"""
        def hook():
            readline.insert_text(placeholder)
            readline.redisplay()
        readline.set_pre_input_hook(hook)
        try:
            inp = input("File path: ").strip()
            self.last_query = inp
            return inp
        finally:
            readline.set_pre_input_hook()

    def run(self):
        while True:
            try:
                filepath = self._input_with_placeholder(self.last_query)
            except (EOFError, KeyboardInterrupt):
                break
            if not filepath:
                continue

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    queries = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print(f"File not found: {filepath}")
                continue

            if not queries:
                print("No queries found in file.")
                continue

            self.playlist = self.library.select_playlist(custom_actions=False)

            print(f"Downloading {len(queries)} tracks to '{self.playlist}'...")

            i = 1
            for query in queries:
                if not query:
                    print(f"Line {i} query ('{query}') is invalid. Skipping.")
                    continue

                parsed = urlparse(query)
                is_url = bool(parsed.scheme and parsed.netloc)
                if is_url:
                    # direct download without confirmation
                    url = query
                    filename = sanitize(query) or f"download_{(timedelta(days=int(ttl_days))).strftime('%Y-%m-%dT%H:%M:%SZ')}"
                else:
                    # otherwise manual confirmation is required
                    entries = self.search_youtube(query, max_results=1)
                    if not entries:
                        print(f"No results for: {query} (line {i}). Skipping.")
                        continue
                    entry = entries[0]
                    url = entry.get('webpage_url') or f"https://youtu.be/{entry['id']}"
                    filename = sanitize(query) or sanitize(entry['title'])

                    try:
                        choice = fzf_select(
                            ["yes", "no"],
                            multi=False,
                            prompt=f"Download result for {query}: {entry.get('title')} ({url}) ?",
                            start_option="yes",
                            raise_except=False
                        )
                    except (KeyboardInterrupt, EOFError):
                        print("Downloads cancelled.")
                        break
                    except Exception as e:
                        print(f"fzf selection failed: {e!s}. Skipping.")
                        continue

                    if not choice or choice[0] != "yes":
                        print(f"Skipped: {query}")
                        continue

                saved = self.downloader.download_url(
                    url,
                    subfolder=self.playlist,
                    filename=filename
                )
                title = entry.get('title') if not is_url and 'entry' in locals() else None
                if title:
                    print(f"Saved: {title} -> {saved}")
                else:
                    print(f"Saved: {saved}")
                i += 1

            print("End of download(s).")
            input("Press Enter to continue...")
