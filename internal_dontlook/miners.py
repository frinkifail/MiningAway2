from __future__ import annotations
from abc import abstractmethod
from asyncio import Task, create_task, sleep
from typing import Type, cast
from .types import IslandData


class Object:
    def __init__(self, island_data: IslandData) -> None:
        self.is_connected_to: list["Object"] = []
        self.requires_connection: list[
            Type["Object"]
        ] = []  # Requires to be connected to a specific type of object
        self.island_data = island_data

    @abstractmethod
    async def connect(self, to: "Object"):
        ...

    async def _ensure_type(self, to: "Object"):
        for i in self.requires_connection:
            if not isinstance(to, i):
                return False


class EnergyGenerator(Object):
    def __init__(self, island_data: IslandData) -> None:
        super().__init__(island_data)
        self.requires_connection.append(Miner)
        self.buffer = 0
        self.task: Task | None = None

    async def loop(self):
        while True:
            await sleep(1)
            for i in self.is_connected_to:
                if isinstance(i, Miner):
                    i.power += 100 / len(self.is_connected_to)

    async def connect(self, to: Object):
        if not await self._ensure_type(to):
            return False
        if isinstance(to, Miner):
            if self.is_connected_to.__len__() == 0:
                self.task = create_task(self.loop())
            self.is_connected_to.append(to)


class PoweredObject(Object):
    def __init__(self, island_data: IslandData) -> None:
        super().__init__(island_data)
        self.power: float = 0
        self.max_power: float = 0
        self.uses_power: float = 0


class Miner(PoweredObject):
    def __init__(self, island_data: IslandData) -> None:
        super().__init__(island_data)
        self.produces: str = "<unset>"
        self.produce_amount: int = 0
        self.level: int = 1
        self.upgrade_cost: float = 0
        self.upgrade_exponent: float = 0

    async def mine(self):
        if self.power - self.uses_power > 0:
            self.power -= self.uses_power
            self.island_data["materials"][self.produces] += int(
                self.produce_amount * (self.level / 1.24778)
            )

    async def upgrade(self):
        if self.island_data["money"] - self.upgrade_cost > 0:
            self.island_data["money"] -= self.upgrade_cost
            self.level += 1
            self.upgrade_cost *= self.upgrade_exponent
            self.upgrade_cost = round(self.upgrade_cost, 2)


class CoalMiner(Miner):
    def __init__(self, island_data: IslandData) -> None:
        super().__init__(island_data)
        self.max_power = 100
        self.uses_power = 20
        self.produces = "coal"
        self.produce_amount = 1
        self.upgrade_cost = 60
        self.upgrade_exponent = 1.18445


def deserialize(obj: dict) -> Miner:
    miner = Miner(obj["island_data"])
    for k, v in obj.items():
        miner.__dict__[k] = v
    return miner
