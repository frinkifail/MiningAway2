import os
import colorama
import random
from internal_dontlook.types import DEFAULT_DATA, IslandData
from internal_dontlook.islands import create_island

colorama.init(autoreset=True)
gts = lambda: os.get_terminal_size()
th = lambda: gts().columns
clear = lambda: os.system("cls") if os.name == "nt" else os.system("clear")

world_data: dict[str, IslandData] = {}  # Server Id, Data
currentserverid: str = "test"


def read(f: str):
    fh = open(f)
    d = fh.read()
    fh.close()
    return d


def main_menu():
    clear()
    print(colorama.Fore.CYAN + "MiningAway 2 Electric Boogaloo".center(th()))
    print(
        colorama.Fore.YELLOW + random.choice(read("splash.txt").split("\n")).rjust(th())
    )
    print()
    print("[ Play ]".center(th()))
    print("[ Settings ]".center(th()))
    print()
    print(colorama.Fore.RED + "[ Exit ]".center(th()))
    while True:
        inp = input("% ").lower()
        match inp:
            case "play":
                play()
                break
            case "settings":
                settings()
                break
            case "exit":
                exit()


def play():
    global currentserverid
    print(colorama.Fore.BLUE + "< Play")
    print(
        colorama.Fore.LIGHTBLACK_EX
        + "Type in your world name\nPut `!` at the front to make it as a server and not a local world"
    )
    world_name = input(": ")
    if world_name.startswith("!"):
        pass
    if not os.path.exists(f"islands/{world_name}"):
        create_island(world_name)
    else:
        if not os.path.exists(f"islands/{world_name}/data.json"):
            print(colorama.Fore.RED + "> Save file is corrupt\n(Data not found)")
            main_menu()
        world_data.update({world_name: DEFAULT_DATA})
        currentserverid = world_name
        game()


def settings():
    pass


def game():
    # world_data.update(
    #     {"test": DEFAULT_DATA}
    # )  # TODO: replace this with grabbing server data or socket or smth whatever
    if currentserverid not in world_data.keys():
        print(colorama.Fore.RED + "> Server data not found")
        main_menu()
    while True:
        data = world_data[currentserverid]  # keep it refreshed
        print(f"{colorama.Fore.GREEN}Money = {data['money']}")


main_menu()
