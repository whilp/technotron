#!/bin/sh

while :; do
    mplayer $(./streamr.py pop)
    sleep 3
done
