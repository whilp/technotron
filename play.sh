#!/bin/sh

while :; do 
    mplayer -really-quiet $(./streamr.py pop)
    sleep 1
done
