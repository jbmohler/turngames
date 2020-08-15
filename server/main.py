import json
import uuid
import importlib
import asyncio
from fastapi import FastAPI, WebSocket
import starlette.websockets

app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/api/health")
def get_api_health():
    return "."


class GamePlayer:
    def __init__(self, name):
        self.id = uuid.uuid1().hex
        self.name = name

    def as_dict(self):
        return {"id": self.id, "name": self.name}


class GameTurn:
    pass


class GameTrick:
    # TODO: consider what separates a trick based game from any other kind of
    # game

    class GameTrickPlay:
        def __init__(self, player_id, cards, is_pass):
            self.player_id = player_id
            self.cards = cards
            self.is_pass = is_pass

        def as_dict(self):
            return {
                "player_id": self.player_id,
                "cards": self.cards,
                "is_pass": self.is_pass,
            }

    def __init__(self):
        self.played = []

    def add(self, gtp):
        self.played.append(gtp)

    def get_state(self):
        return [gtp.as_dict() for gtp in self.played]


class GameStruct:
    def __init__(self, server):
        self.game_id = str(uuid.uuid1())
        self.players = []
        self.observers = []

        # import the server
        # TODO:  make this dynamic & elegant
        if server == "scum":
            import scumserver as module

        self.srvplug = module.Server()

        self.trickset_summary = []

        self.clear_trickset()

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

        return p

    def add_observer(self, websocket, struct):
        self.observers.append(struct)
        self.listeners.append(websocket)
        self.bump_state()

    def player_lock(self):
        self.move_state("deal")

    def clear_trickset(self):
        print("clearing trickset")
        self.trick_history = []
        self.live_trick = None

    def new_trickset(self):
        self.clear_trickset()

        # TODO:  re-order players by prior trickset

        self.move_state("deal")

    async def distribute_deals(self, deals):
        pmap = {p.id: p for p in self.players}
        for player, hand in deals.items():
            obj = {"type": "deal", "cards": hand}
            await pmap[player].websocket.send_json(obj)

        self.move_state("bid")

    async def announce_trickset_complete(self):
        state = self.get_state()
        for player in self.players:
            obj = {"type": "review_trickset", "state": state}
            await player.websocket.send_json(obj)

    async def finalize_bid(self):
        # TODO implement a game with a bid to figure this out

        self.move_state("play")

    def cards_played(self):
        for _, card in self.cards_played_per_player():
            yield card

    def cards_played_per_player(self):
        live = [self.live_trick] if self.live_trick else []
        for trick in self.trick_history + live:
            for gtp in trick.played:
                if not gtp.cards:
                    continue
                for card in gtp.cards:
                    yield gtp.player_id, card

    def create_live_trick(self):
        self.live_trick = GameTrick()

    def append_trickset_summary(self, data):
        self.trickset_summary.append(data)

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
        elif self.state[0] == "review":
            state = {}
            state["state"] = self.state
            state["players"] = [x.as_dict() for x in self.players]
            state["summary"] = self.trickset_summary[-1]
            return state
        else:
            raise NotImplementedError(f"no state implementation for {self.state[0]}")

    async def push_state_updates(self):
        last_sent = self.state
        while True:
            await asyncio.sleep(0.15)
            if last_sent != self.state:
                current_state = self.get_state()
                for ws in self.listeners:
                    await ws.send_json({"type": "state_update", "state": current_state})
                last_sent = self.state

    async def prompt_player(self, player_id, retry_msg=None):
        pmap = {p.id: p for p in self.players}

        obj = {"type": "play", "trick": self.live_trick.get_state()}
        if retry_msg:
            obj["retry_msg"] = retry_msg
        await pmap[player_id].websocket.send_json(obj)

    async def play_response(self, player, data):
        candidate = GameTrick.GameTrickPlay(
            player.id, data.get("cards", []), data.get("is_pass", False)
        )

        if await self.srvplug.check_legal_play(self, candidate):
            self.live_trick.add(candidate)
            self.bump_state()
            await self.srvplug.run_state_play(self)
        else:
            await self.prompt_player(player.id, retry_msg="illegal play")

    def player_queue(self, after_player_id, include=False):
        if include:
            yield after_player_id
        offset = self.players[1:] + [self.players[0]]
        # we count on the outer code to have a terminator on this enumeration
        while True:
            for p1, p2 in zip(self.players, offset):
                if p1.id == after_player_id:
                    yield p2.id
                    after_player_id = p2.id
                    break
            else:
                raise RuntimeError("player not found in player_queue")


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

    player = None
    while True:
        try:
            data = await websocket.receive_json()
        except starlette.websockets.WebSocketDisconnect:
            print(f"player {player.name if player else 'unidentified'} disconnect")
            break
        except json.JSONDecodeError as e:
            print(f"error parsing content -- {str(e)}")

        if data["type"] == "identify" and "player" in data:
            player = gs.add_player(websocket, data["player"])

        if data["type"] == "identify" and "observer" in data:
            gs.add_observer(websocket, data["observer"])

        if data["type"] == "player_lock" and is_creator:
            gs.player_lock()

        if data["type"] == "new_trickset" and is_creator:
            gs.new_trickset()

        if data["type"] == "play_response":
            await gs.play_response(player, data)

        # await websocket.send_text(f"Message text was: {data}")
