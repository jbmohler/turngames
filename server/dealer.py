import random
import asyncio

# Here is an in-process class, but we aspire for this really to point to https://github.com/jbmohler/epicdeal


class Dealer:
    def __init__(self):
        pass

    async def deal_cards(self, players, cards):
        _cards = cards[:]
        random.shuffle(_cards)

        # test await & make it feel real :)
        await asyncio.sleep(0.5)

        card_count = len(_cards)
        deal_count = sum(v for _, v in players.items())
        if card_count < deal_count:
            raise RuntimeError(
                f"requested deal {deal_count}, but only {card_count} cards given"
            )

        results = {}
        # copy list to split off hands
        remaining = _cards[:]
        for k, v in players.items():
            hand, remaining = remaining[:v], remaining[v:]
            results[k] = hand
        return results
