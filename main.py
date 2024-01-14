import os
import colorama
import random
from internal_dontlook.types import DEFAULT_DATA, IslandData
from internal_dontlook.islands import create_island, json
from asyncio import run, sleep
import socketio
import keyboard as kb
import aiofiles

colorama.init(autoreset=True)
gts = lambda: os.get_terminal_size()
th = lambda: gts().columns
clear = lambda: os.system("cls") if os.name == "nt" else os.system("clear")

world_data: IslandData | None = None  # Server Id, Data
currentserverid: str = "test"
is_local: bool = False
is_return: bool = False  # returned from disconnect

TICK_DELAY = 0.2

sio = socketio.AsyncSimpleClient()

username = "<unset>"

if os.path.exists("isDebugEnabled"):
    DEBUG = True
else:
    DEBUG = False


async def read(f: str):
    fh = await aiofiles.open(f)
    d = await fh.read()
    await fh.close()
    return d


async def main_menu():
    clear()
    print(colorama.Fore.CYAN + "MiningAway 2 Electric Boogaloo".center(th()))
    print(
        colorama.Fore.YELLOW
        + random.choice((await read("splash.txt")).split("\n")).rjust(th())
    )
    print()
    print("[ Play ]".center(th()))
    print("[ Settings ]".center(th()))
    print()
    print(
        colorama.Fore.RED + f"[ Exit{' (CTRL+C)' if is_return else ''} ]".center(th())
    )
    while True:
        inp = input("% ").lower()
        match inp:
            case "play":
                await play()
                break
            case "settings":
                await settings()
                break
            case "exit":
                return


async def play():
    global is_local
    print(colorama.Fore.BLUE + "< Play")
    print(
        colorama.Fore.LIGHTBLACK_EX
        + "Type in your world name\nPut `!` at the front to mark it as a server and not a local world\nType `@` to make it localhost (mostly used for dev stuff)"
    )
    world_name = input(": ")

    async def load(data: IslandData):
        global currentserverid, world_data
        world_data = data
        currentserverid = world_name
        await game()

    if world_name == "@":
        world_name = "!localhost:9211"
    if world_name.startswith("!"):
        try:
            await sio.connect(f"http://{world_name.replace('!', '')}")
        except socketio.exceptions.ConnectionError as e:  # type: ignore
            simplified_str = "unknown"
            estr = str(e)
            if "max retries" in estr.lower():
                simplified_str = "failed to connect, max retries exceeded (probably incorrect server address)"
            else:
                simplified_str = estr
            print(f"> Connection failed: {simplified_str}")
        await game()
    if not os.path.exists(f"islands/{world_name}"):
        create_island(world_name)
        await load(DEFAULT_DATA)
    else:
        if not os.path.exists(f"islands/{world_name}/data.json"):
            print(colorama.Fore.RED + "> Save file is corrupt\n(Data not found)")
            await sleep(2)
            await main_menu()
        f = open(f"islands/{world_name}/data.json")
        daytar = json.load(f)
        f.close()
        await load(daytar)
        is_local = True


async def settings():
    pass


async def game():
    global world_data
    # world_data.update(
    #     {"test": DEFAULT_DATA}
    # )  # TODO: replace this with grabbing server data or socket or smth whatever
    # sio.connect("http://localhost:9211")
    if sio.client == None:
        print("> Client didn't load")
        await sleep(2)
        await main_menu()
        return
    if not is_local:
        try:
            await sio.emit("RefreshData", {"all": True})
            world_data = (await sio.receive(20))[1]
        except socketio.exceptions.BadNamespaceError:  # type: ignore
            print("> Failed to connect to server")
            await sleep(2)
            await main_menu()
            return
        except socketio.exceptions.TimeoutError:  # type: ignore
            print("> Server didn't respond in time")
            await sleep(2)
            await main_menu()
            return

    await sio.emit("PlayerConnect", username)
    while True:
        try:
            is_done = await sio.receive(20)
        except socketio.exceptions.TimeoutError:  # type: ignore
            print("> Connection failed: didnt connect in time")
            await sleep(2)
            await main_menu()
            return
        if is_done[0] == "PlayerConnect" and is_done[1]["state"] == "established":
            break
        else:
            print("> Connection failed: incorrect packet")
            await sleep(TICK_DELAY)

    # print("Loading...")
    # await sleep(1)

    if world_data == None:
        print("> World data doesn't exist")
        await sleep(2)
        await main_menu()
        return  # doesn't do anything im pretty sure but because type checker
    data = world_data

    async def bind_events():
        @sio.client.on("PlayerResourceChange")
        async def plr_rc(d: dict):
            if DEBUG:
                nonlocal print_txt
                print_txt.update({"socketDebug": "PlayerResourceChange"})
            if d["isTopLevel"]:
                data[d["resource"]] = d["to"]
            else:
                data["materials"][d["resource"]] = d["to"]

        @sio.client.on("PlayerConnect")
        async def plr_cn(d: dict):
            nonlocal pause
            if DEBUG:
                pause = True
                print(f"PlayerConnect: {d}")
                input()
                pause = False
            nonlocal print_txt, wait_ticks
            if d["state"] == "error":
                return
            data["players"].append(d["who"])
            print_txt.update({"joinMsg": f"{d['who']} joined the game"})
            wait_ticks.update({"joinMsg": 10})

        @sio.client.on("PlayerDisconnect")
        async def plr_dcn(d: dict):
            nonlocal pause
            if DEBUG:
                pause = True
                print(f"PlayerDisconnect: {d}")
                input()
                pause = False
            nonlocal print_txt, wait_ticks, kill
            if d["state"] == "error":
                match d["error"]:
                    case "NotInServer":
                        pass
                    case "HostNotLoggedIn":
                        print("> Host hasn't logged in yet\ntry again later")
                        await sleep(2)
                        await main_menu()
                        return
                    case _:
                        print("disconnect> Unknown error")
                        await sleep(0.5)
            if d["state"] == "host":
                await sio.disconnect()
                kill = True
                print("> Host disconnected")
                await sleep(2)
                await main_menu()
                return
            try:
                data["players"].remove(d["who"])
            except ValueError:
                print("player not found")  # you have around .2 seconds to see this message
                return
            print_txt.update({"leftMsg": f"{d['who']} left the game"})
            wait_ticks.update({"leftMsg": 10})

        @sio.client.on("Autosave")
        async def autosave(msg: str | None):
            if msg is not None:
                print_txt.update({"autosave": "Autosaving!!"})
            else:
                print_txt.update({"autosave": f"Autosaving!! {msg}"})
            wait_ticks.update({"autosave": 10})

    def bind_keys():
        kb.register_hotkey("q", lambda: run(open_menu()), suppress=True)
        kb.register_hotkey("e", lambda: run(inventory_toggle()), suppress=True)

    timer = 0
    print_txt: dict[str, str] = {}
    wait_ticks: dict[str, int] = {}
    pause: bool = False
    kill: bool = False
    inv_is_open: bool = False

    async def open_menu():
        kb.clear_all_hotkeys()
        nonlocal pause, kill
        global is_return
        pause = True
        await sleep(TICK_DELAY)
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
                    bind_keys()
                    break
                case "settings":
                    kill = True
                    is_return = True
                    await sleep(TICK_DELAY)
                    await settings()
                    break
                case "disconnect":
                    kill = True
                    is_return = True
                    await sleep(TICK_DELAY)
                    await main_menu()
                    break

    async def inventory_toggle():
        nonlocal inv_is_open, print_txt
        inv_is_open = not inv_is_open
        THE_ULTIMATE_COMPATABILITY_VARIABLE = "\n"
        if inv_is_open:
            print_txt.update(
                {
                    "inventory": f"""
Materials:
{THE_ULTIMATE_COMPATABILITY_VARIABLE.join([f"{k.capitalize()}: {v}" for k,v in data['materials'].items()])}
            """
                }
            )
        else:
            del print_txt["inventory"]

    bind_keys()

    while True:
        if pause:
            continue
        if kill:
            kb.clear_all_hotkeys()
            await sio.emit("PlayerDisconnect", username)
            await sio.disconnect()
            data["players"].remove(username)
            print("Disconnecting...")
            await sleep(1)
            break
        timer += 1
        clear()
        for k2, v2 in wait_ticks.items():
            if v2 > 0:
                wait_ticks[k2] -= 1
            else:
                del wait_ticks[k2]
                del print_txt[k2]
        if print_txt:
            for v in print_txt.values():
                print(v)
        print("Connected players:")
        for i in data["players"]:
            print(f"- {i}")
        # if wait_ticks > 0:
        #     wait_ticks -= 1
        print(f"{colorama.Fore.GREEN}Money = {data['money']}$")
        if DEBUG:
            print(print_txt, wait_ticks)
        await sio.client.sleep()
        await sleep(TICK_DELAY)
    await main_menu()


username = input("Insert username: ")
if len(username) > 16 or len(username) < 4 or username == "<unset>":
    print(
        "> Invalid username (must be longer than 3 characters, must be shorter than 16 characters)"
    )
    quit()
run(main_menu())
