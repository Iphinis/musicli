import os

def clear_screen():
    command = 'cls' if os.name == 'nt' else 'clear'
    os.system(command)

def ensure_dir(path:str) -> None:
    os.makedirs(path, exist_ok=True)