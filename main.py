import os
import colorama
import random
from internal_dontlook.types import DEFAULT_DATA, IslandData
from internal_dontlook.islands import create_island, json
from time import sleep
import socketio
import keyboard as kb

colorama.init(autoreset=True)
gts = lambda: os.get_terminal_size()
th = lambda: gts().columns
clear = lambda: os.system("cls") if os.name == "nt" else os.system("clear")

world_data: IslandData | None = None  # Server Id, Data
currentserverid: str = "test"
is_local: bool = False

TICK_DELAY = 0.2

sio = socketio.Client()

username = "<unset>"

if os.path.exists("isSocketDebugEnabled"):
    SOCKET_DEBUG = True
else:
    SOCKET_DEBUG = False


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
    global is_local
    print(colorama.Fore.BLUE + "< Play")
    print(
        colorama.Fore.LIGHTBLACK_EX
        + "Type in your world name\nPut `!` at the front to mark it as a server and not a local world\nType `@` to make it localhost (mostly used for dev stuff)"
    )
    world_name = input(": ")

    def load(data: IslandData):
        global currentserverid, world_data
        world_data = data
        currentserverid = world_name
        game()

    if world_name == "@":
        world_name = "!localhost:9211"
    if world_name.startswith("!"):
        try:
            sio.connect(f"http://{world_name.replace('!', '')}")
        except socketio.exceptions.ConnectionError as e:  # type: ignore
            simplified_str = "unknown"
            estr = str(e)
            if "max retries" in estr.lower():
                simplified_str = "failed to connect, max retries exceeded (probably incorrect server address)"
            else:
                simplified_str = estr
            print(f"> Connection failed: {simplified_str}")
        game()
    if not os.path.exists(f"islands/{world_name}"):
        create_island(world_name)
        load(DEFAULT_DATA)
    else:
        if not os.path.exists(f"islands/{world_name}/data.json"):
            print(colorama.Fore.RED + "> Save file is corrupt\n(Data not found)")
            main_menu()
        f = open(f"islands/{world_name}/data.json")
        daytar = json.load(f)
        f.close()
        load(daytar)
        is_local = True


def settings():
    pass


def game():
    global world_data
    # world_data.update(
    #     {"test": DEFAULT_DATA}
    # )  # TODO: replace this with grabbing server data or socket or smth whatever
    # sio.connect("http://localhost:9211")
    if not is_local:
        try:
            sio.emit("RefreshData", {"all": True})
        except socketio.exceptions.BadNamespaceError:  # type: ignore
            print("> Failed to connect to server")
            sleep(2)
            main_menu()
            return

        @sio.on("RefreshData")
        def temprd(d: IslandData):
            # nonlocal pause
            # if SOCKET_DEBUG:
            #     print(f"AllRefreshData: {d}")
            #     input()
            global world_data
            world_data = d

    sio.emit("PlayerConnect", username)

    print("Loading...")
    sleep(1)

    if world_data == None:
        print("> World data doesn't exist")
        main_menu()
        return  # doesn't do anything im pretty sure but because type checker
    data = world_data

    @sio.on("PlayerResourceChange")
    def plr_rc(d: dict):
        nonlocal pause
        if SOCKET_DEBUG:
            pause = True
            print(f"PlayerResourceChange: {d}")
            input()
            pause = False
        if d["isTopLevel"]:
            data[d["resource"]] = d["to"]
        else:
            data["materials"][d["resource"]] = d["to"]

    @sio.on("PlayerConnect")
    def plr_cn(d: dict):
        nonlocal pause
        if SOCKET_DEBUG:
            pause = True
            print(f"PlayerConnect: {d}")
            input()
            pause = False
        nonlocal print_txt, wait_ticks
        if d["state"] == "error":
            return
        data["players"].append(d["who"])
        print_txt = f"{d['who']} joined the game"
        wait_ticks = 10

    @sio.on("PlayerDisconnect")
    def plr_dcn(d: dict):
        nonlocal pause
        if SOCKET_DEBUG:
            pause = True
            print(f"PlayerDisconnect: {d}")
            input()
            pause = False
        nonlocal print_txt, wait_ticks, kill
        if d["state"] == "error":
            return
        if d["state"] == "host":
            sio.disconnect()
            kill = True
            print("> Host disconnected")
            sleep(2)
            main_menu()
            return
        try:
            data["players"].remove(d["who"])
        except ValueError:
            print("player not found")  # you have around .2 seconds to see this message
            return
        print_txt = f"{d['who']} left the game"
        wait_ticks = 10

    timer = 0
    print_txt: str | None = None
    wait_ticks = 0
    pause: bool = False
    kill: bool = False

    def open_menu():
        nonlocal pause, kill
        pause = True
        clear()
        print(colorama.Fore.GREEN + "-- MENU --".center(th()))
        print()
        print(colorama.Fore.BLUE + "[ Resume ]".center(th()))
        print(
            colorama.Fore.BLUE
            + "[ Settings ] (will disconnect from server)".center(th())
        )
        print()
        print(colorama.Fore.RED + "[ Disconnect ]".center(th()))
        while True:
            inp = input("% ").lower()
            match inp:
                case "resume":
                    pause = False
                    break
                case "settings":
                    kill = True
                    sleep(0.2)
                    settings()
                    break
                case "disconnect":
                    kill = True
                    sleep(0.2)
                    main_menu()
                    break

    kb.register_hotkey("m", open_menu, suppress=True)

    while True:
        if pause:
            continue
        if kill:
            kb.clear_all_hotkeys()
            sio.emit("PlayerDisconnect", username)
            sio.disconnect()
            data["players"].remove(username)
            print("Disconnecting...")
            sleep(1)
            break
        timer += 1
        clear()
        print("Connected players:")
        for i in data["players"]:
            print(f"- {i}")
        if wait_ticks > 0:
            wait_ticks -= 1
        if print_txt:
            if wait_ticks == 0:
                print_txt = None
                continue
            print(print_txt)
        print(f"{colorama.Fore.GREEN}Money = {data['money']}$")
        sleep(TICK_DELAY)


username = input("Insert username: ")
if len(username) > 16 or len(username) < 4 or username == "<unset>":
    print(
        "> Invalid username (must be longer than 3 characters, must be shorter than 16 characters)"
    )
    quit()
main_menu()
