import itertools
import asyncio


def card_denomination(c):
    if c == "ROOK":
        return 20
    else:
        x = int(c[1:])
        if x == 1:
            return 15
        return x


class ScumClient:
    GAME_LABEL = "scum"

    def __init__(self):
        self.cards = None
        self.cards_played = []

    def state_update(self, newstate):
        # TODO is this necessary
        if newstate.next_player == "me":
            play = self.player.play(game, newstate.trick)

        if newstate.trick.state == "trick_done":
            self.player.review_complete_trick(game, newstate.trick)

    async def accept_deal(self, deal):
        self.cards = deal["cards"]
        self.cards_played = []

        self.cards.sort(key=card_denomination)
        print(self.cards)

    async def show_summary(self, tset):
        pmap = {p["id"]: p for p in tset["players"]}

        for pid, rank in tset["summary"]:
            print(f"{pmap[pid]}: {rank}")

    async def make_play(self, prompt):
        # this is essentially the greedy algorithm

        print(prompt)
        await asyncio.sleep(.25)

        trick = prompt["trick"]
        if len(trick) > 0:
            last = [gtp for gtp in reversed(trick) if not gtp["is_pass"]][0]
            topcards = last["cards"]
            high_denom = card_denomination(topcards[0])

            # bucket cards (they are sorted)
            for denom, _cards in itertools.groupby(self.cards, key=card_denomination):
                cards = list(_cards)
                if denom > high_denom and len(cards) >= len(topcards):
                    result = {"cards": cards[: len(topcards)]}
                    break
            else:
                result = {"is_pass": True}
        else:
            # bucket cards (they are sorted)
            for denom, _cards in itertools.groupby(self.cards, key=card_denomination):
                cards = list(_cards)
                break

            result = {"cards": cards}

        if not result.get("is_pass", False):
            # update accounting
            # TODO -- what if the server returns illegal move? we've taken the
            # cards out of play ... although how would we even respond to that.
            self.cards_played += result["cards"]
            for c in result["cards"]:
                self.cards.remove(c)
        return result
