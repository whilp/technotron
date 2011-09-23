#!/bin/sh

id=$(sed -nre 's/^link .*\///p' $1)
echo "url http://cdn.official.fm/mp3s/${id%???}/${id}.mp3" >> $1
