import os
import subprocess
import sys
from pathlib import Path

from settings import Settings

def clear_screen():
    if Settings.get('app', 'clear_screen') == 'True':
        command = 'cls' if os.name == 'nt' else 'clear'
        os.system(command)

def ensure_dir(path:str) -> None:
    os.makedirs(path, exist_ok=True)

def open_path(path: Path) -> None:
    """
    Open a directory or file with the system default application.
    On Linux: uses xdg-open
    On macOS: uses open
    On Windows: uses os.startfile
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p!r} does not exist")

    if sys.platform == "darwin":
        subprocess.run(["open", str(p)])
    elif sys.platform == "win32":
        # os.startfile only exists on Windows
        os.startfile(str(p))
    else:
        # assume Linux / XDG‑compliant desktop
        subprocess.run(["xdg-open", str(p)], check=False)
