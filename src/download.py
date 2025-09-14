"""download.py"""
import yt_dlp
import os
from utils import ensure_dir
import platform
import subprocess
from sanitize_filename import sanitize

from settings import Settings

class Download:
    """
    Download an audio file.
    """
    
    def __init__(self, output_dir:str):
        """
        output_dir: base directory where downloads will be saved
        format: audiio format to post-process (e.g. 'flac', 'mp3')
        """
        self.output_dir=output_dir
        
        ensure_dir(self.output_dir)

    def download_url(self, url:str, subfolder:str, filename:str='') -> str:
        """
        Download only audio from a URL into output_dir/subfolder.
        Returns the full path to the downloaded file.
        Warning: overwrites file if it already exists.
        """
        if not subfolder:
            raise ValueError("Subfolder must be provided")

        # ensure subfolder exists
        target_dir = os.path.join(self.output_dir, subfolder)
        ensure_dir(target_dir)

        filename = (filename or '%(title)s') + '.%(ext)s'
        outtmpl = os.path.join(target_dir, filename)

        preferred_codec = Settings.get('download', 'preferred_codec')
        preferred_quality = Settings.get('download', 'preferred_quality')
        embed_thumbnail = Settings.get_bool('download', 'embed_thumbnail')

        # build options
        ydl_opts = {
            'format': "bestaudio/best", # best as fallback
            'verbose': Settings.get_bool('app', 'debug'),
            'outtmpl': outtmpl, # output path

            'writethumbnail': embed_thumbnail,
            'embedthumbnail': embed_thumbnail,
            'embedmetadata': True,

            # process the final audio file
            'postprocessors': [
                # internal metadata (ID3)
                {
                    'key': 'FFmpegMetadata',
                    'add_metadata': True,
                },
                # codec & quality
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': preferred_codec,
                    'preferredquality' : preferred_quality,
                },
                # embed thumbnail
                {
                    'key': 'EmbedThumbnail',
                },
            ],

            'xattrs': True, # internal metadata (e.g. link)

            # network settings
            'socket_timeout': 30,
            'retries': 10, # retry attempts when download fails
            'fragment_retries': 10, # retry attempts for fragment downloads (DASH/HLS)
            'continuedl': True, # allow resuming partially-downloaded files
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # final path
        final_path = None
        if info.get("requested_downloads"):
            final_path = info["requested_downloads"][0].get("filepath")
        elif info.get("_filename"):
            final_path = info["_filename"]
        elif info.get("filepath"):
            final_path = info["filepath"]
        
        if final_path:
            final_path = os.path.abspath(final_path)

            # sanitize filename
            try:
                dirpath, fname = os.path.split(final_path)
                stem, ext = os.path.splitext(fname)
                safe_stem = sanitize(stem)
                if safe_stem != stem:
                    new_fname = safe_stem + ext
                    new_path = os.path.join(dirpath, new_fname)
                    # avoid collision by appending _1, _2...
                    i = 1
                    while os.path.exists(new_path):
                        new_fname = f"{safe_stem}_{i}{ext}"
                        new_path = os.path.join(dirpath, new_fname)
                        i += 1
                    os.rename(final_path, new_path)
                    final_path = os.path.abspath(new_path)
            except Exception as e:
                # keep original if anything goes wrong
                print(f"[warn] failed to sanitize/rename {final_path}: {e}")

            # add OS specific xattr metadata for source url, if supported.
            try:
                match platform.system():
                    case "Linux":
                        os.setxattr(final_path, "user.xdg.origin.url", url.encode("utf-8"))
                    case "Darwin":
                        subprocess.run(["xattr", "-w", "com.apple.metadata:kMDItemWhereFroms", url, final_path], check=False)
                    case "Windows":
                        ads_name = final_path + ":xdg.origin.url"
                        with open(ads_name, "w", encoding="utf-8") as ads:
                            ads.write(url)
                    case _:
                        raise OSError("OS not recognized. Cannot set url xattr metadata.")
            except Exception as e:
                # ignore if setting xattr fails (filesystem or OS may not support it)
                print(f"[warn] failed to set xattr on {final_path}: {e}")

        return final_path
