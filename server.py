from json import load
from os.path import exists
from threading import Thread
from time import sleep
import eventlet
import socketio
from internal_dontlook.types import DEFAULT_DATA, IslandData
from internal_dontlook.islands import create_island

sio = socketio.Server()
app = socketio.WSGIApp(sio)

TICK_DELAY = 0.2
game_thread: Thread | None = None

island_data: IslandData = None  # type: ignore
hostid: str = "admin"
if v := input("Host Player ID (leave empty for 'admin'): "):
    hostid = v

if v := input(
    "New island or load island (to create new, prefix island name with `!`): "
):
    if v.startswith("!"):
        create_island(v.replace("!", ""))
    else:  # yes i copied this from client code
        if not exists(f"islands/{v}/data.json"):
            print("> Save file is corrupt\n(Data not found)")
            exit()
        f = open(f"islands/{v}/data.json")
        island_data = load(f)
        # print(island_data)
        f.close()
        del f
else:
    print("> Aborted")
    exit()

kill_game_loop: bool = False

sid_usernames: dict[str, str] = {}
disconnected_properly: list[str] = []


def game_loop():
    while True:
        if kill_game_loop:
            print("> killed game loop")
            break
        island_data["money"] += 1
        sio.emit(
            "PlayerResourceChange",
            {"isTopLevel": True, "resource": "money", "to": island_data["money"]},
        )
        sleep(TICK_DELAY)


@sio.event
def connect(sid, environ):
    for i in DEFAULT_DATA.keys():
        if i not in island_data:
            sio.emit("InternalServerFailure", {"error": "InvalidIslandData"})
            quit()


@sio.on("PlayerConnect")
def login(sid, data: str):
    sid_usernames.update({sid: data})
    global game_thread
    if data == hostid:
        # sio.emit()
        game_thread = Thread(None, game_loop, "Game Loop")
        game_thread.start()
    if data in island_data["players"]:
        sio.emit("PlayerConnect", {"state": "error", "error": "AlreadyInServer"})
        return
    print(f"{data} joined le server")
    island_data["players"].append(data)
    sio.emit("PlayerConnect", {"state": "success", "who": data})


def proper_disconnect(username: str):
    global kill_game_loop
    if username == hostid:
        sio.emit("PlayerDisconnect", {"state": "host"})
        kill_game_loop = True
        quit()
    try:
        island_data["players"].remove(username)
        sio.emit("PlayerDisconnect", {"state": "success", "who": username})
    except ValueError:
        sio.emit("PlayerDisconnect", {"state": "error", "error": "NotInServer"})


@sio.on("PlayerDisconnect")
def logout(sid, data: str):
    disconnected_properly.append(sid)
    proper_disconnect(data)


@sio.on("PlayerResourceChange")
def plr_rc(sid, data: dict):
    if data["isTopLevel"]:
        island_data[data["resource"]] = data["to"]
    else:
        island_data["materials"][data["resource"]] = data["to"]
    sio.emit("PlayerResourceChange", data)


@sio.on("RefreshData")
def rd(sid: str, key: dict):
    if key["all"]:
        sio.emit("RefreshData", island_data, room=sid)
        return
    if key["isTopLevel"]:
        sio.emit("RefreshData", island_data[key["resource"]], room=sid)
    else:
        sio.emit("RefreshData", island_data["materials"][key["resource"]], room=sid)


@sio.event
def disconnect(sid):
    if sid not in disconnected_properly:
        user = sid_usernames.get(sid)
        if user == None:
            print(f"> Username for {sid} not found")
            return
        print(f"> {user} didn't disconnect properly")
        proper_disconnect(user)


eventlet.wsgi.server(eventlet.listen(("", 9211)), app)  # type: ignore
