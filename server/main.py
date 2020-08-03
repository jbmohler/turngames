import json
import uuid
import importlib
import asyncio
from fastapi import FastAPI, WebSocket

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/health")
def get_api_health():
    return "."


class GamePlayer:
    def __init__(self, name):
        self._id = uuid.uuid1().hex
        self.name = name


class GameTurn:
    pass


class GameStruct:
    def __init__(self, server):
        self.game_id = str(uuid.uuid1())
        self.players = []
        self.observers = []
        self.history = []

        # import the server
        # TODO:  make this dynamic & elegant
        if server == "scum":
            import scumserver as module

        self.srvplug = module.Server()

        self.state = ("startup", 0)
        self.listeners = []

    def bump_state(self):
        self.state = (self.state[0], self.state[1] + 1)

    def move_state(self, new_state):
        self.state = (new_state, 0)

        asyncio.create_task(self.srvplug.update_state(self))

    def add_player(self, websocket, struct):
        p = GamePlayer(struct["name"])
        p.websocket = websocket
        self.players.append(p)
        self.listeners.append(websocket)
        self.bump_state()

    def add_observer(self, websocket, struct):
        self.observers.append(struct)
        self.listeners.append(websocket)
        self.bump_state()

    def player_lock(self):
        self.move_state("deal")

    async def distribute_deals(self, deals):
        pmap = {p._id: p for p in self.players}
        for player, hand in deals.items():
            obj = {"type": "deal", "cards": hand}
            await pmap[player].websocket.send_json(obj)

        self.move_state("bid")

    async def finalize_bid(self):
        # TODO implement a game with a bid to figure this out

        self.move_state("play")

    def get_state(self):
        if self.state[0] == "startup":
            state = {}
            state["state"] = self.state
            state["players"] = [x.name for x in self.players]
            return state
        elif self.state[0] == "deal":
            state = {}
            state["state"] = self.state
            state["players"] = [x.name for x in self.players]
            return state
        elif self.state[0] == "bid":
            state = {}
            state["state"] = self.state
            state["players"] = [x.name for x in self.players]
            return state
        elif self.state[0] == "play":
            state = {}
            state["state"] = self.state
            state["players"] = [x.name for x in self.players]
            return state
        else:
            raise NotImplementedError(f"no state implementation for {self.state[0]}")

    async def push_state_updates(self):
        last_sent = self.state
        while True:
            await asyncio.sleep(.15)
            if last_sent != self.state:
                current_state = self.get_state()
                for ws in self.listeners:
                    await ws.send_json({"type": "state_update", "state": current_state})
                last_sent = self.state


GAME_LIST = []


@app.get("/games/list")
def get_games_list():
    global GAME_LIST
    return {"games": [gs.game_id for gs in GAME_LIST]}


@app.websocket("/ws/start-game/{server}")
async def websocket_start_game(server: str, websocket: WebSocket):
    global GAME_LIST

    await websocket.accept()

    gs = GameStruct(server)
    GAME_LIST.append(gs)

    asyncio.get_event_loop().create_task(gs.push_state_updates())

    await handle_game_ws(websocket, gs, is_creator=True)


@app.websocket("/ws/join-game/{game_id}")
async def websocket_join_game(game_id: str, websocket: WebSocket):
    global GAME_LIST

    await websocket.accept()

    match = [gs for gs in GAME_LIST if gs.game_id == game_id]

    if len(match) != 1:
        await websocket.close()
        return

    gs = match[0]

    asyncio.get_event_loop().create_task(gs.push_state_updates())

    await handle_game_ws(websocket, gs, is_creator=False)


async def handle_game_ws(websocket: WebSocket, gs: GameStruct, is_creator: bool):
    await websocket.send_json({"type": "hello"})
    while True:
        try:
            data = await websocket.receive_json()
        except json.JSONDecodeError as e:
            print(f"error parsing content -- {str(e)}")

        if data["type"] == "identify" and "player" in data:
            gs.add_player(websocket, data["player"])

        if data["type"] == "identify" and "observer" in data:
            gs.add_observer(websocket, data["observer"])

        if data["type"] == "player_lock" and is_creator:
            gs.player_lock()

        # await websocket.send_text(f"Message text was: {data}")
