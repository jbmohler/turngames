import dealer

SUITS = ["Red", "Yellow", "Green", "Black"]
DENOMINATIONS = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 1]

CARDS = [f"{s[0]}{d}" for s in SUITS for d in DENOMINATIONS]
CARDS.append("ROOK")

### dupe from client ####
def card_denomination(c):
    if c == "ROOK":
        return 20
    else:
        x = int(c[1:])
        if x == 1:
            return 15
        return x


############################


def print_trick(game, current):
    pmap = {p.id: p for p in game.players}
    print(f"Trick #{len(game.trick_history)}")
    for play in current.played:
        if play.is_pass:
            print(f"\t<passes> ({pmap[play.player_id].name})")
        else:
            takes = play
            print(f"\t{play.cards} ({pmap[play.player_id].name})")
    print(f"{pmap[takes.player_id].name} takes the trick")


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

        current = game.live_trick

        if game.live_trick == None:
            game.create_live_trick()
            player_id = game.players[0].id
        elif len(current.played) == len(game.players):
            last = [gtp for gtp in reversed(current.played) if not gtp.is_pass][0]
            game.trick_history.append(current)
            print_trick(game, current)

            game.create_live_trick()
            player_id = last.player_id
        else:
            trick = game.live_trick
            player_id = game.get_next_player(trick.played[-1].player_id)

        await game.prompt_player(player_id)

    async def check_legal_play(self, game, play):
        print(play.as_dict())
        if play.is_pass and len(play.cards) > 0:
            return False
        if not play.is_pass and len(play.cards) == 0:
            return False

        if set(game.cards_played()).intersection(play.cards):
            return False

        current = game.live_trick

        base_denom = 0
        if len(current.played) == 0:
            if play.is_pass:
                return False
        else:
            if play.is_pass:
                return True
            last = [gtp for gtp in reversed(current.played) if not gtp.is_pass][0]

            base_denom = card_denomination(last.cards[0])
            multiplicity = len(last.cards)

        denoms = set(card_denomination(c) for c in play.cards)
        if len(denoms) > 1:
            return False

        if denoms.pop() <= base_denom:
            return False

        return True
