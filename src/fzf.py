import subprocess

def fzf_select(options:list[str]) -> str:
    """
    Display options in fzf and returns the selected option
    """
    fzf = subprocess.Popen(
        ["fzf", "--ansi", "--reverse"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    stdout, _ = fzf.communicate("\n".join(options))
    return stdout.strip()
