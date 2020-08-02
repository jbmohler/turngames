import json
import uuid
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
    pass


class GameTurn:
    pass


class GameStruct:
    def __init__(self):
        self.game_id = str(uuid.uuid1())
        self.players = []
        self.observers = []
        self.history = []

        self.state = ("startup", 0)
        self.listeners = []

    def bump_state(self):
        self.state = (self.state[0], self.state[1] + 1)

    def move_state(self, new_state):
        self.state = (new_state, 0)

    def add_player(self, websocket, struct):
        self.players.append(struct)
        self.listeners.append(websocket)
        self.bump_state()

    def add_observer(self, websocket, struct):
        self.observers.append(struct)
        self.listeners.append(websocket)
        self.bump_state()

    def get_state(self):
        if self.state[0] == "startup":
            state = {}
            state["players"] = [x["name"] for x in self.players]
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


@app.websocket("/ws/start-game")
async def websocket_start_game(websocket: WebSocket):
    global GAME_LIST

    await websocket.accept()

    gs = GameStruct()
    GAME_LIST.append(gs)

    asyncio.get_event_loop().create_task(gs.push_state_updates())

    await handle_game_ws(websocket, gs)


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

    await handle_game_ws(websocket, gs)


async def handle_game_ws(websocket: WebSocket, gs: GameStruct):
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

        # await websocket.send_text(f"Message text was: {data}")