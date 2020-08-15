#!/bin/sh

tmux new-session -d -s foo 'exec bash -c "cd server && uvicorn main:app --reload"'
tmux rename-window 'Foo'
tmux select-window -t foo:0
tmux split-window -h 'exec bash -c "python client/gamebase.py --player=Fred --game=scum || read sam"'
tmux split-window -v 'exec bash -c "python client/gamebase.py --player=Sally --game=scum --host || read sam"'
tmux split-window -v 'exec bash -c "python client/gamebase.py --player=Joe --game=scum || read sam"'
#tmux select-layout tiled
tmux -2 attach-session -t foo
