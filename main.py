import os
import colorama
import random

colorama.init(autoreset=True)
gts = lambda: os.get_terminal_size()


def read(f: str):
    fh = open(f)
    d = fh.read()
    fh.close()
    return d


def main_menu():
    print(colorama.Fore.CYAN + "MiningAway 2 Electric Boogaloo".center(gts().columns))
    print(
        colorama.Fore.YELLOW
        + random.choice(read("splash.txt").split("\n")).rjust(gts().columns)
    )


main_menu()
