#!/bin/sh

xargs -P8 -n1 ./streamr.py update < ./sources
