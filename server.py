from json import load
from os.path import exists
from asyncio import Task, create_task, run, sleep
from aiohttp import web
import socketio
from internal_dontlook.miners import CoalMiner, EnergyGenerator
from internal_dontlook.types import DEFAULT_DATA, IslandData
from internal_dontlook.islands import create_island, save_island

sio = socketio.AsyncServer()
app = web.Application()
sio.attach(app)

TICK_DELAY = 0.2
AUTOSAVE_DELAY = 10  # seconds
game_task: Task | None = None
save_task: Task | None = None

island_data: IslandData = None  # type: ignore
hostid: str = "admin"
hostsid: str | None = None
island_name: str | None = None
if v := input("Host Player ID (leave empty for 'admin'): "):
    hostid = v

if v := input(
    "New island or load island (to create new, prefix island name with `!`): "
):

    def loadIsland():
        global island_data, island_name
        island_name = v.replace("!", "")
        if not exists(f"islands/{v.replace('!', '')}/data.json"):
            print("> Save file is corrupt\n(Data not found)")
            exit()
        f = open(f"islands/{v.replace('!', '')}/data.json")
        island_data = load(f)
        # print(island_data)
        f.close()
        del f

    if v.startswith("!"):
        create_island(v.replace("!", ""))
        loadIsland()
    else:  # yes i copied this from client code
        loadIsland()
else:
    print("> Aborted")
    exit()

kill_game_loop: bool = False

sid_usernames: dict[str, str] = {}
disconnected_properly: list[str] = []

timer = 0


async def save_loop():  # autosave!!
    while True:
        if kill_game_loop:
            print("> killed save loop")
            break
        if hostsid == None or island_name == None:
            continue
        await sio.emit(
            "Autosave"
        )  # other people can leave during funny autosave but if host leaves im pretty sure
        await sio.emit(  # everything explodes
            "Autosave", "don't leave the game.", room=hostsid
        )
        save_island(island_name, island_data)  # type: ignore
        await sio.sleep()
        await sleep(AUTOSAVE_DELAY)


async def game_loop():
    while True:
        if timer == 1:
            energy = EnergyGenerator(island_data)
            miner = CoalMiner(island_data)
            await energy.connect(miner)
        if kill_game_loop:
            print("> killed game loop")
            break
        # island_data["money"] += 1
        # await sio.emit(
        #     "PlayerResourceChange",
        #     {"isTopLevel": True, "resource": "money", "to": island_data["money"]},
        # )
        if timer > 1:
            await miner.mine()  # type: ignore
        await sio.emit(
            "PlayerResourceChange",
            {
                "isTopLevel": False,
                "resource": "coal",
                "to": island_data["materials"]["coal"],
            },
        )
        await sio.sleep()
        await sleep(TICK_DELAY)


@sio.event
async def connect(sid, environ):
    for i in DEFAULT_DATA.keys():
        if i not in island_data:
            await sio.emit("InternalServerFailure", {"error": "InvalidIslandData"})
            quit()


@sio.on("PlayerConnect")
async def login(sid, data: str):
    if sid_usernames.__len__() == 0 and data != hostid:
        await sio.emit(
            "PlayerDisconnect", {"state": "error", "error": "HostNotLoggedIn"}
        )
    sid_usernames.update({sid: data})
    global game_task, save_task, hostsid
    if data == hostid:
        # sio.emit()
        game_task = create_task(game_loop())
        save_task = create_task(save_loop())
        hostsid = sid
    if data in island_data["players"]:
        await sio.emit("PlayerConnect", {"state": "error", "error": "AlreadyInServer"})
        return
    print(f"{data} joined le server")
    island_data["players"].append(data)
    await sio.emit("PlayerConnect", {"state": "success", "who": data})
    await sio.emit("PlayerConnect", {"state": "established"}, room=sid)


async def proper_disconnect(username: str):
    global kill_game_loop
    if username == hostid:
        await sio.emit("PlayerDisconnect", {"state": "host"})
        kill_game_loop = True
        quit()
    try:
        island_data["players"].remove(username)
        await sio.emit("PlayerDisconnect", {"state": "success", "who": username})
    except ValueError:
        await sio.emit("PlayerDisconnect", {"state": "error", "error": "NotInServer"})


@sio.on("PlayerDisconnect")
async def logout(sid, data: str):
    disconnected_properly.append(sid)
    await proper_disconnect(data)


@sio.on("PlayerResourceChange")
async def plr_rc(sid, data: dict):
    if data["isTopLevel"]:
        island_data[data["resource"]] = data["to"]
    else:
        island_data["materials"][data["resource"]] = data["to"]
    await sio.emit("PlayerResourceChange", data)


@sio.on("RefreshData")
async def rd(sid: str, key: dict):
    if key["all"]:
        await sio.emit("RefreshData", island_data, room=sid)
        return
    if key["isTopLevel"]:
        await sio.emit("RefreshData", island_data[key["resource"]], room=sid)
    else:
        await sio.emit(
            "RefreshData", island_data["materials"][key["resource"]], room=sid
        )


@sio.event
async def disconnect(sid):
    if sid not in disconnected_properly:
        user = sid_usernames.get(sid)
        if user == None:
            print(f"> Username for {sid} not found")
            return
        print(f"> {user} didn't disconnect properly")
        await proper_disconnect(user)


# eventlet.asgi.server(eventlet.listen(("", 9211)), app)  # type: ignore
web.run_app(app, port=9211)
