import collections
import asyncio
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


class Server:
    def __init__(self):
        self.card_counts = {}
        self.trump = None

        # 1 .. 15
        self.trickset_index = 0

        self.bids = {}

    async def update_state(self, game):
        if game.state[0] == "deal":
            self.trickset_index += 1
            await self.run_state_deal(game)
        elif game.state[0] == "bid":
            await self.run_state_bid(game)
        elif game.state[0] == "play":
            await self.run_state_play(game)
        elif game.state[0] == "review":
            pass

    @property
    def deal_type(self):
        return "normal"

    @property
    def deal_count(self):
        return max(1, abs(self.trickset_index - 8))

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

        cardsper = self.deal_count

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
            self.print_bids(game, self.bids)
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
                    trickwin = self.assign_trick(game, current)
                    player_id = trickwin["win_player"]
                    self.print_trick(game, current)

                    game.trick_history.append(current)
                    game.live_trick = None
                    break
                else:
                    player_id = next_player
                    break
        else:
            player_id = game.players[0].id

        tricks = len(game.trick_history)
        if tricks == self.deal_count:
            player_id = None

        if player_id:
            if game.live_trick == None:
                game.create_live_trick()

            await game.prompt_player(player_id)
        else:
            self.summarize_trickset(game)
            game.move_state("review")
            await game.announce_trickset_complete()
            if self.trickset_index == 15:
                # up-down-riv is done after 15 tricksets
                await asyncio.sleep(3)
                game.move_state("lobby")

    def print_trick(self, game, current):
        pmap = {p.id: p for p in game.players}
        print(f"Trick #{len(game.trick_history)+1}")

        results = self.assign_trick(game, current)
        for index, play in enumerate(current.played):
            print(f"\t{play.cards[0]} ({pmap[play.player_id].name})")
        print(
            f"{pmap[results['win_player']].name} takes the trick with {results['win_card']}"
        )

    def print_bids(self, game, bids):
        n = self.deal_count
        print(f"Bid on {n} cards")
        for player in game.players:
            print(f"\t{player.name}: {bids[player.id]}")

    def card_suit_ex(self, c):
        x = card_suit(c)
        if x == "z":
            x = self.trump
        return x

    def assign_trick(self, game, current):
        cden = card_denomination
        trump = self.trump

        for index, play in enumerate(current.played):
            card = play.cards[0]
            if index == 0:
                takes = play.player_id
                taking = card
                prime_suit = self.card_suit_ex(card)
            elif self.card_suit_ex(card) == trump:
                takes = play.player_id
                taking = card
                prime_suit = trump
            elif self.card_suit_ex(card) == prime_suit and cden(card) > cden(taking):
                takes = play.player_id
                taking = card
        return {"win_player": takes, "win_card": taking}

    def summarize_trickset(self, game):
        total_score = []

        taken = collections.defaultdict(lambda: 0)
        for trick in game.trick_history:
            trickwin = self.assign_trick(game, trick)
            taken[trickwin["win_player"]] += 1

        for player in game.players:
            tricks = taken[player.id]
            bids = self.bids[player.id]
            total_score.append(
                {
                    "player_id": player.id,
                    "bid": bids,
                    "tricks": tricks,
                    "score": tricks + (10 if tricks == bids else 0),
                }
            )

        ntd = "continue" if self.trickset_index < 15 else "complete"
        game.append_trickset_summary(total_score, next_trick_disposition=ntd)

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
