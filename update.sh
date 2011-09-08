#!/bin/sh

parallelism=${1:-1}

xargs -P$parallelism -n1 ./streamr.py update < ./sources
