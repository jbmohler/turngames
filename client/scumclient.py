def card_denomination(c):
    if c == "ROOK":
        return 20
    else:
        x = int(c[1:])
        if x == 1:
            return 15
        return x


class ScumClient:
    def state_update(self, newstate):
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

        return {"cards": self.cards[:2]}
