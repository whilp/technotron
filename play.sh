#!/bin/sh

while :; do 
    mplayer -really-quiet $(./streamr.py pop)
    sleep 3
done
