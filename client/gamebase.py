import json
import argparse
import asyncio
import aiohttp


class ClientGame:
    def __init__(self, name, is_creator=False):
        self._name = name
        self.is_creator = is_creator

    def get_name(self):
        return self._name


async def chat_server(session, game, server):
    if game.is_creator:
        # TODO abstract game choice
        tail = "/ws/start-game/scum"
    else:
        while True:
            await asyncio.sleep(.5)
            content = await session.get(f"{server}/games/list")
            games = json.loads(await content.text())
            if len(games["games"]) > 0:
                game_id = games["games"][0]
                break

        tail = f"/ws/join-game/{game_id}"

    async with session.ws_connect(f"{server}{tail}") as ws:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except Exception as e:
                    print(f"error: {str(e)}\nparsing :  {msg.data[:20]}")
                    continue

                if data["type"] == "hello":
                    content = {"type": "identify", "player": {"name": game.get_name()}}
                    await ws.send_str(json.dumps(content))

                if data["type"] == "state_update":
                    state = data["state"]
                    if game.is_creator and state["state"][0] == "startup":
                        # TODO abstract start state
                        if len(state["players"]) == 3:
                            content = {"type": "player_lock"}
                            await ws.send_str(json.dumps(content))
                    print("Received update")

                if data["type"] == "deal":
                    print(data["cards"])

            elif msg.type == aiohttp.WSMsgType.ERROR:
                break


async def start_game(server, game):
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                content = await session.get(f"{server}/api/health")
                break
            except:
                pass

        # async with session.get('http://httpbin.org/get') as resp:
        #    print(resp.status)
        #    print(await resp.text())

        await chat_server(session, game, server)


if __name__ == "__main__":
    server = "http://localhost:8000"

    parser = argparse.ArgumentParser(description="make a game client")
    parser.add_argument("--player", help="player name")
    parser.add_argument(
        "--host", default=False, action="store_true", help="is game host"
    )

    args = parser.parse_args()

    game = ClientGame(args.player, args.host)
    asyncio.get_event_loop().run_until_complete(start_game(server, game))

    input("enter to close")
