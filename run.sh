#!/bin/sh

trap 'kill $(jobs -p)' EXIT

sqlite_web --read-only "build/source.db" --url-prefix "/source.db" --port 8080 &
sqlite_web --read-only "build/iedb.db" --url-prefix "/iedb.db"  --port 8081 &
export FLASK_ENV=development
src/iedbtk/server.py
