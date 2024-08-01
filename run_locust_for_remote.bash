#!/usr/bin/env bash
. .env
if [ "$REMOTE_URL" = "" ]; then
    echo "REMOTE_URL not found. Please provide this in your environment"
    exit 1
fi

echo using ${REMOTE_URL} as a remote url
locust --headless --csv cyrextech --users 6 --spawn-rate 1 -H ${REMOTE_URL}
