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

    def state_update(self, newstate):
        # TODO is this necessary
        if newstate.next_player == "me":
            play = self.player.play(game, newstate.trick)

        if newstate.trick.state == "trick_done":
            self.player.review_complete_trick(game, newstate.trick)

    async def accept_deal(self, deal):
        self.cards = deal["cards"]

        self.cards.sort(key=card_denomination)
        print(self.cards)

    async def make_play(self, prompt):
        # this is essentially the greedy algorithm

        print(prompt)
        await asyncio.sleep(1.0)

        trick = prompt["trick"]
        if len(trick) > 0:
            last = [gtp for gtp in reversed(trick) if not gtp["is_pass"]][0]
            topcards = last["cards"]

            # bucket cards (they are sorted)
            for denom, _cards in itertools.groupby(self.cards, key=card_denomination):
                cards = list(_cards)
                if denom > card_denomination(topcards[0]) and len(cards) >= len(
                    topcards
                ):
                    break
            else:
                return {"is_pass": True}

            return {"cards": cards[: len(topcards)]}
        else:
            # bucket cards (they are sorted)
            for denom, _cards in itertools.groupby(self.cards, key=card_denomination):
                cards = list(_cards)
                break

            return {"cards": cards}
