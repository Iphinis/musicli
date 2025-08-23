import subprocess
import signal
import os

from settings import Settings

def fzf_select(options:list[str], multi:bool=False, prompt:str="", start_option:str|None=None) -> list[str]:
    """
    Display options in fzf and return selected option(s).

    Args:
        options: List of strings to show in fzf.
        multi: If True, allow multi-selection.
        prompt: Prompt text to display.
        start_index: If provided, initial highlighted position (0-based).
    """
    
    fzf_cmd = [
        "fzf",
        "--prompt", prompt,
        "--ansi",
        "--reverse",
        "--cycle",
        "--no-bold",
        "--expect", "ctrl-d,ctrl-z"
    ]

    if multi:
        fzf_cmd.append("--multi")

    if start_option:
        try:
            idx = options.index(start_option)
            cursor_pos = idx + 1  # fzf is 1-based
        except ValueError:
            # fallback if option not found
            cursor_pos = 1
        fzf_cmd += ["--bind", f"load:pos({cursor_pos})"]

    fzf = subprocess.Popen(
        fzf_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    stdout, _ = fzf.communicate("\n".join(options))
    
    if not stdout:
        return []
    
    return stdout.strip().split("\n")