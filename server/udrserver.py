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
    for index, play in enumerate(current.played):
        if index == 0:
            led = card_suit(play.cards[0])
        print(f"\t{play.cards} ({pmap[play.player_id].name})")
    print(f"{pmap[takes.player_id].name} takes the trick")


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
        deals = await game.dealer.deal_cards(todeal, CARDS)

        self.trump = card_suit(deals["trump"])

        await game.distribute_deals(deals)

    async def run_state_bid(self, game):
        for player in game.players:
            obj = {"type": "bid"}
            await player.websocket.send_json(obj)

        # TODO: figure out when to call this
        # await game.finalize_bid()

    async def check_legal_bid(self, game, bid):
        asdf

    async def place_bid(self, game, bid):
        asdf

    async def run_state_play(self, game):
        # something about player order

        playcount = collections.Counter(
            player_id for player_id, _ in game.cards_played_per_player()
        )
        remaining = {
            pid: dealt - playcount.get(pid, 0)
            for pid, dealt in self.card_counts.items()
        }

        default_player = None
        player_id = None

        if game.live_trick:
            current = game.live_trick

            first = current.played[0].player_id
            last = current.played[-1].player_id

            for next_player in game.player_queue(last):
                if next_player == first:
                    default_player = [
                        gtp for gtp in reversed(current.played) if not gtp.is_pass
                    ][0].player_id
                    game.trick_history.append(current)
                    print_trick(game, current)
                    game.live_trick = None
                    break
                elif remaining[next_player] > 0:
                    player_id = next_player
                    break
        else:
            default_player = game.players[0].id

        if game.live_trick == None:
            for player in game.players:
                if remaining[player.id] < 3:
                    print(f"{player.name}:  {remaining[player.id]}")

            rplayers = [p for p in game.players if remaining[p.id] > 0]

            if len(rplayers):
                for pid in game.player_queue(default_player, include=True):
                    if remaining[pid] > 0:
                        player_id = pid
                        break

                game.create_live_trick()

        if player_id:
            await game.prompt_player(player_id)
        else:
            self.summarize_trickset(game)
            game.move_state("review")
            await game.announce_trickset_complete()

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
