import os
import json
from .types import DEFAULT_DATA, IslandData


def _ensurefolder():
    try:
        os.mkdir("islands")
    except FileExistsError:
        pass


def create_island(name: str):
    _ensurefolder()
    try:
        os.mkdir(f"islands/{name}")
    except FileExistsError:
        print("> Island already exists. Overwrite (y/n)?")
        while True:
            i = input().lower()
            if i == "y":
                print("> Overwriting...")
                os.rmdir(f"islands/{name}")
                os.mkdir(f"islands/{name}")
                break
            elif i == "n":
                print("> Choose a different name.")
                return False

    f = open(f"islands/{name}/data.json", "w+")
    json.dump(DEFAULT_DATA, f)
    f.close()
    return True


def save_island(name: str, island_data: IslandData):
    _ensurefolder()
    if not os.path.exists(f"islands/{name}"):
        print("> Island doesn't exist")
        return False
    f = open(f"islands/{name}/data.json", "w+")
    json.dump(island_data, f)
    f.close()
    return True
