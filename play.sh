#!/bin/sh

UA="Mozilla/5.0"
CURL="curl -s --user-agent \'${UA}\' -L"
export TMPDIR=.

while :; do 
    next=$(./streamr.py randpop)
    tmp=$(mktemp -d .play-XXXXXXXX)
    trap "rm -rf $tmp" ERR EXIT
    ${CURL} "$next" -o $tmp/next &
    sleep 3
    mplayer -really-quiet "$tmp/next"
    rm -rf "$tmp"
done
