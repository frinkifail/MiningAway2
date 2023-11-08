from typing import TypedDict


class MaterialData(TypedDict):
    coal: int
    iron: int
    gold: int
    diamonds: int


class IslandData(TypedDict):
    money: float
    materials: MaterialData
    players: list[str]


DEFAULT_DATA = IslandData(
    money=0, materials=MaterialData(coal=0, iron=0, gold=0, diamonds=0), players=[]
)

material_values = {  # value, ???
    "coal": [20],
    "iron": [30],
    "gold": [40],
    "diamonds": [60],
}
