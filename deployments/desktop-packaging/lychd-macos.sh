#!/bin/sh
# Use the interpreter in this edition even when the shell has another Python on PATH.
exec "$(/usr/bin/dirname "$0")/runtime/bin/python3" -I -B -m lychd "$@"
