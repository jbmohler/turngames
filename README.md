## Introduction

It should be simple and fun to write an AI for various card games.  But every
time I try, I'm mired in the muck of dealing and game state and blah-blah-blah.
So here is a tool that attempts to abstract that all out and ensure that AI
clients can be run on separate computers with a high level of isolation.

Because, hey, people who use this are totally out to cheat with their AI's and
snoop memory on their fellow AI's.

## Testing & dev

```sh
python -m venv venv
python -m pip install pip --upgrade
pip install -r requirements.txt
sh tmux-play/tmux-multi.sh
```

## Goals

* support games with or with-out a bidding phase
* support secure hand deals
* handle all game state around game tricks
* have server based game state validation (legality & state changes)
* be obsessive about deal & player isolation
