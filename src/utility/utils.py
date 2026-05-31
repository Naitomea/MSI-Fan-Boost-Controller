import sys


def is_bundled() -> bool:
    return (
        getattr(sys, 'frozen', False) 
        and hasattr(sys, '_MEIPASS')
    )