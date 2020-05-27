#!/bin/sh

trap 'kill $(jobs -p)' EXIT

#DB="build/iedb.db"
DB="build/temp.db"
sqlite_web --read-only "${DB}" --url-prefix "/sqlite-web" &
export FLASK_ENV=development
src/iedbtk/server.py
