import itertools
import random
import asyncio


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


class UpDownRivClient:
    GAME_LABEL = "udr"

    def __init__(self):
        self.cards = None
        self.cards_played = []

        self.trump = None

    def state_update(self, newstate):
        # TODO is this necessary
        if newstate.next_player == "me":
            play = self.player.play(game, newstate.trick)

        if newstate.trick.state == "trick_done":
            self.player.review_complete_trick(game, newstate.trick)

    async def accept_deal(self, deal):
        self.cards = deal["cards"]
        self.cards_played = []

        self.cards.sort(key=card_sort)
        print(self.cards)

    async def show_summary(self, tset):
        pmap = {p["id"]: p for p in tset["players"]}

        for player_results in tset["summary"]:
            pid = player_results["player_id"]
            score = player_results["score"]
            print(f"{pmap[pid]['name']}: {score}")

    async def make_bid(self, prompt):
        high = [c for c in self.cards if card_denomination(c) > 12]
        return {"bid": len(high)}

    def card_suit_ex(self, c):
        x = card_suit(c)
        if x == "z":
            x = self.trump
        return x

    async def make_play(self, prompt):
        # So far, this algorithm plays generally greedily - If below
        # bid amount and can take the hand, it does so then it tries
        # best not to.  TODO -- be smarter with trump.

        print(prompt)
        await asyncio.sleep(0.25)

        trick = prompt["trick"]
        if len(trick) > 0:
            on_table = [gtp["cards"][0] for gtp in trick]
            led = self.card_suit_ex(on_table[0])

            matching = [c for c in self.cards if self.card_suit_ex(c) == led]
            trump_cards = [c for c in self.cards if self.card_suit_ex(c) == self.trump]

            # TODO: count hands taken
            short_bid = True

            if len(matching) > 0:
                # must match suit called
                if short_bid:
                    card = matching[-1]
                else:
                    card = matching[0]
            elif len(trump_cards) > 0 and short_bid:
                # play trump
                card = random.choice(trump_cards)
            else:
                # play random
                card = random.choice(self.cards)
        else:
            # lead random
            card = random.choice(self.cards)

        result = {"cards": [card]}

        # update accounting
        # TODO -- what if the server returns illegal move? we've taken the
        # cards out of play ... although how would we even respond to that.
        self.cards_played += result["cards"]
        for c in result["cards"]:
            self.cards.remove(c)

        return result
