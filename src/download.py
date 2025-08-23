import yt_dlp
import os
from utils import ensure_dir
from settings import Settings

class Download:
    def __init__(self, output_dir:str):
        """
        output_dir: base directory where downloads will be saved
        format: audiio format to post-process (e.g. 'flac', 'mp3')
        """
        self.output_dir=output_dir
        
        ensure_dir(self.output_dir)

    def download_url(self, url:str, subfolder:str='', filename:str=None) -> str:
        """
        Download only audio from a URL into output_dir/subfolder.
        Returns the full path to the downloaded file.
        """
        if not subfolder:
            return

        # ensure subfolder exists
        target_dir = os.path.join(self.output_dir, subfolder)
        ensure_dir(target_dir)

        # construct output template
        if filename:
            out_name = filename
        else:
            # use yt-dlp default title replacement
            out_name = '%(title)s.%(ext)s'
        outtmpl = os.path.join(target_dir, out_name)

        codec = Settings.get('download', 'preferred_codec')
        quality = Settings.get('download', 'preferred_quality')
        thumbnail = True if Settings.get('download', 'thumbnail') == True else False

        # build options
        ydl_opts = {
            'format': "bestaudio",
            'quiet': False,
            'no-playlist': True,
            'no_warnings': True,
            'restrictfilenames': True,
            'outtmpl': outtmpl,

            'embed-thumbnail': thumbnail,
            'writethumbnail': thumbnail,

            'postprocessors': [
                # thumbnail
                {
                    'key': 'EmbedThumbnail',
                },
                # codec & quality
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': codec,
                    'preferredquality': quality
                },
                # internal metadata (ID3)
                {
                    'key': 'FFmpegMetadata',
                },
            ],

            'xattrs': True, # external metadata (e.g. link)
            'writeinfojson': True, # write metadata in a .info.json

            # network settings
            'socket_timeout': 30,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # determine real filename
        ext = Settings.get('download', 'preferred_codec')
        title = info.get('title')
        saved_name = filename or f"{title}.{ext}"
        return os.path.join(target_dir, saved_name)
