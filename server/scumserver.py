import dealer

SUITS = ["Red", "Yellow", "Green", "Black"]
DENOMINATIONS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 1]

CARDS = [f"{s[0]}{d}" for s in SUITS for d in DENOMINATIONS]
CARDS.append("ROOK")

class Server:
    async def update_state(self, game):
        global CARDS

        if game.state[0] == "deal":
            print(f"dealing to {len(game.players)} players")

            game.dealer = dealer.Dealer()

            cardsper = len(CARDS) // len(game.players)

            remaining = len(CARDS) - cardsper * len(game.players)

            sequence = [cardsper+1]*remaining + [cardsper] * (len(game.players) - remaining)
            todeal = {p._id: s for p, s in zip(game.players, sequence)}

            # TODO:  this will be async with an await
            deals = await game.dealer.deal_cards(todeal, CARDS)

            await game.distribute_deals(deals)

        if game.state[0] == "bid":
            # no bidding in scum, move along

            await game.finalize_bid()

        if game.state[0] == "play":
            # something about player order

            pass
