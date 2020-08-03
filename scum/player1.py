
import itertools

# terms:
#  - hand
#  - dealt
#  - group
#  - trick


class GreedyPlayer:
    def __init__(self):
        self.hand = None
        self.played = []

    def receive_deal(self, game, dealt):
        self.hand = dealt

    def play(self, game, trick):
        if len(trick.play_history) == 0:
            return self._play(self._lowest_denomination_group())
        elif len(game.players) == len(trick.play_history) + 1:
            # last one playing
            return self._play(self._lowest_exceeding(trick.max_group()))
        else:
            return self._play(self._lowest_exceeding(trick.max_group()))

    def review_complete_trick(self, game, trick):
        self.played.add(trick.cards)

    def _play(self, cards):
        # remove the cards from my hand
        if cards == None:
            return None
        self.hand = set(self.hand).difference(cards)
        return cards

    def _group_sets(self):
        kf = lambda x: x.denomination()

        for denom, cards in itertools.groupby(key=kf, sorted(self.hand, key=kf)):
            yield denom, cards

    def _lowest_denomination_group(self):
        for denom, cards in self._group_sets():
            return list(cards)

    def _lowest_exceeding(self, card_group):
        for denom, _cards in self._group_sets():
            cards = list(_cards)
            if denom == "bird":
                return cards
            elif denom > card_group.denomination() and len(cards) >= len(card_group):
                return cards[:len(card_group)]

        return None
