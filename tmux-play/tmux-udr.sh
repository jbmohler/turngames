#!/bin/sh

tmux new-session -d -s foo 'exec bash -c "cd server && uvicorn main:app --reload"'
tmux rename-window 'Foo'
tmux select-window -t foo:0
tmux split-window -h 'exec bash -c "python client/gamebase.py --player=Fred --game=udr || read sam"'
tmux split-window -v 'exec bash -c "python client/gamebase.py --player=Sally --game=udr --host --group=Fred,Joe,George || read sam"'
tmux split-window -v 'exec bash -c "python client/gamebase.py --player=Joe --game=udr || read sam"'
tmux split-window -v 'exec bash -c "python client/gamebase.py --player=George --game=udr || read sam"'
#tmux select-layout tiled
tmux -2 attach-session -t foo
