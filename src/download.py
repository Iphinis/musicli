import yt_dlp
import os

class Download:
    def __init__(self, output_dir: str, formats: list[str] = None):
        """
        output_dir: base directory where downloads will be saved
        formats: list of audio formats to post-process (e.g. ['flac', 'mp3'])
        """
        self.output_dir = output_dir
        self.formats = formats or ['flac']
        os.makedirs(self.output_dir, exist_ok=True)

    def download_url(self, url: str, subfolder: str = '', filename: str = None) -> str:
        """
        Download only audio from a URL into output_dir/subfolder.
        Returns the full path to the downloaded file.
        """
        # ensure subfolder exists
        target_dir = os.path.join(self.output_dir, subfolder)
        os.makedirs(target_dir, exist_ok=True)

        # construct output template
        if filename:
            out_name = filename
        else:
            # use yt-dlp default title replacement
            out_name = '%(title)s.%(ext)s'
        outtmpl = os.path.join(target_dir, out_name)

        # build options
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'outtmpl': outtmpl,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.formats[0],
                'preferredquality': '192',
            }]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # determine real filename
        ext = self.formats[0]
        title = info.get('title')
        saved_name = filename or f"{title}.{ext}"
        return os.path.join(target_dir, saved_name)
