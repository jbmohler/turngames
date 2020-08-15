import json
import argparse
import asyncio
import aiohttp


class ClientGame:
    def __init__(self, name, is_creator=False, myclient=None):
        self._name = name
        self.is_creator = is_creator
        self.myclient = myclient

    def get_name(self):
        return self._name


async def chat_server(session, game, server):
    if game.is_creator:
        tail = f"/ws/start-game/{game.myclient.GAME_LABEL}"
    else:
        while True:
            await asyncio.sleep(0.5)
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

                    if game.is_creator and state["state"][0] == "review":
                        print("going to play again")
                        await game.myclient.show_summary(data["state"])
                        await asyncio.sleep(2)
                        content = {"type": "new_trickset"}
                        await ws.send_str(json.dumps(content))

                if data["type"] == "deal":
                    await game.myclient.accept_deal(data)

                if data["type"] == "play":
                    response = await game.myclient.make_play(data)

                    content = {"type": "play_response"}
                    content.update(response)

                    await ws.send_str(json.dumps(content))

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

    # TODO abstract out game choice
    import scumclient

    game = ClientGame(args.player, args.host, scumclient.ScumClient())
    asyncio.get_event_loop().run_until_complete(start_game(server, game))

    input("enter to close")
