import dealer

SUITS = ["Red", "Yellow", "Green", "Black"]
DENOMINATIONS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 1]

CARDS = [f"{s[0]}{d}" for s in SUITS for d in DENOMINATIONS]
CARDS.append("ROOK")


class Server:
    async def update_state(self, game):
        if game.state[0] == "deal":
            await self.run_state_deal(game)
        elif game.state[0] == "bid":
            # no bidding in scum, move along

            await game.finalize_bid()
        elif game.state[0] == "play":
            await self.run_state_play(game)

    async def run_state_deal(self, game):
        global CARDS

        print(f"dealing to {len(game.players)} players")

        game.dealer = dealer.Dealer()

        cardsper = len(CARDS) // len(game.players)

        remaining = len(CARDS) - cardsper * len(game.players)

        sequence = [cardsper + 1] * remaining + [cardsper] * (
            len(game.players) - remaining
        )
        todeal = {p.id: s for p, s in zip(game.players, sequence)}

        # TODO:  this will be async with an await
        deals = await game.dealer.deal_cards(todeal, CARDS)

        await game.distribute_deals(deals)

    async def run_state_play(self, game):
        # something about player order

        if game.live_trick == None:
            game.create_live_trick()
            player_id = game.players[0].id
        else:
            trick = game.live_trick
            player_id = game.get_next_player(trick.played[-1].player_id)

        await game.prompt_player(player_id)

    async def check_legal_play(self, game, play):
        pass
