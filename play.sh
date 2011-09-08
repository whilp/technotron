#!/bin/sh

while :; do 
    mplayer -cache 8192 -really-quiet $(./streamr.py pop)
    sleep 1
done
