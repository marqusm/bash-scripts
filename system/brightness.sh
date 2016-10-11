#!/usr/bin/env bash

command=``
xrandr --current --verbose | grep -sw 'connected' | awk '{print $1;}' |
while read -r line
do
    eval "xrandr --output "${line}" --brightness "$1
done
