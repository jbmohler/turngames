import collections
import dealer

SUITS = ["Red", "Yellow", "Green", "Black"]
DENOMINATIONS = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 1]

CARDS = [f"{s[0]}{d}" for s in SUITS for d in DENOMINATIONS]
CARDS.append("ROOK")

REDUCED_CARDS = [
    f"{s[0]}{d}" for s in SUITS for d in DENOMINATIONS if d not in (2, 3, 4)
]
REDUCED_CARDS.append("ROOK")

### dupe from client ####
def card_denomination(c):
    if c == "ROOK":
        return 20
    else:
        x = int(c[1:])
        if x == 1:
            return 15
        return x


def card_suit(c):
    if c == "ROOK":
        return "z"
    else:
        return c[0].lower()


def card_sort(c):
    return (card_suit(c), card_denomination(c))


############################


def print_trick(game, current):
    pmap = {p.id: p for p in game.players}
    print(f"Trick #{len(game.trick_history)}")

    trump = game.srvplug.trump
    for index, play in enumerate(current.played):
        card = play.cards[0]
        if index == 0:
            takes = play.player_id
            taking = card
            prime_suit = game.srvplug.card_suit_ex(card)
        elif game.srvplug.card_suit_ex(card) == trump:
            takes = play.player_id
            taking = card
            prime_suit = trump
        elif game.srvplug.card_suit_ex(card) == prime_suit and card_denomination(
            card
        ) > card_denomination(taking):
            takes = play.player_id
            taking = card

        print(f"\t{card} ({pmap[play.player_id].name})")
    print(f"{pmap[takes].name} takes the trick")
    return takes


def print_bids(game, bids):
    pmap = {p.id: p for p in game.players}
    # TODO: abstract n
    n = 7
    print(f"Bid on {n} cards")
    for player in game.players:
        print(f"\t{player.name}: {bids[player.id]}")


class Server:
    def __init__(self):
        self.card_counts = {}
        self.trump = None

        self.bids = {}

    async def update_state(self, game):
        if game.state[0] == "deal":
            await self.run_state_deal(game)
        elif game.state[0] == "bid":
            await self.run_state_bid(game)
        elif game.state[0] == "play":
            await self.run_state_play(game)
        elif game.state[0] == "review":
            pass

    async def run_state_deal(self, game):
        global CARDS, REDUCED_CARDS

        print(f"dealing to {len(game.players)} players")

        if not 2 <= len(game.players) <= 7:
            raise RuntimeError("up-and-down-the-river requires between 2 & 8 players")

        if len(game.players) < 5:
            cardset = REDUCED_CARDS
        else:
            cardset = CARDS

        game.dealer = dealer.Dealer()

        cardsper = 7

        todeal = {p.id: cardsper for p in game.players}
        todeal["trump"] = 1
        self.card_counts = todeal.copy()

        # TODO:  this will be async with an await
        deals = await game.dealer.deal_cards(todeal, cardset)

        self.trump_representative = deals.pop("trump")
        self.trump = card_suit(self.trump_representative)

        await game.distribute_deals(deals)

    async def run_state_bid(self, game):
        for player in game.players:
            ctx = None
            await game.prompt_bidder(player.id, ctx)

        self.bids = {player.id: None for player in game.players}

    async def check_legal_bid(self, game, player, data):
        thebid = int(data["bid"])

        if not 0 <= thebid <= self.card_counts[player.id]:
            return False
        return True

    async def place_bid(self, game, player, data):
        self.bids[player.id] = int(data["bid"])

        remaining = {pid for pid, bid in self.bids.items() if bid is None}

        if 0 == len(remaining):
            print_bids(game, self.bids)
            await game.finalize_bid()

    async def run_state_play(self, game):
        # something about player order

        player_id = None

        if game.live_trick:
            current = game.live_trick

            first = current.played[0].player_id
            last = current.played[-1].player_id

            for next_player in game.player_queue(last):
                if next_player == first:
                    player_id = print_trick(game, current)
                    game.trick_history.append(current)
                    game.live_trick = None
                    break
                else:
                    player_id = next_player
                    break
        else:
            player_id = game.players[0].id

        tricks = len(game.trick_history)
        # TODO trick count
        if tricks == 7:
            player_id = None

        if player_id:
            if game.live_trick == None:
                game.create_live_trick()

            await game.prompt_player(player_id)
        else:
            self.summarize_trickset(game)
            game.move_state("review")
            await game.announce_trickset_complete()

    def card_suit_ex(self, c):
        x = card_suit(c)
        if x == "z":
            x = self.trump
        return x

    def summarize_trickset(self, game):
        # total_score = # ...

        # game.append_trickset_summary(total_score)

        pass

    async def check_legal_play(self, game, play):
        if play.is_pass:
            return False

        if len(play.cards) != 1:
            return False

        if set(game.cards_played()).intersection(play.cards):
            return False

        # TODO:  check if earlier plays indicated a lack of a color
        # that is now contradicted.

        return True
