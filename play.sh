#!/bin/sh

UA="Mozilla/5.0"
CURL="curl -s --user-agent \'${UA}\' -L"

while :; do 
    ${CURL} $(./streamr.py pop) | mplayer -cache 8192 -really-quiet -
    sleep 1
done
