#!/usr/bin/env python
"""Test script for root endpoint"""

import urllib.request
import sys
import json


def main():
    sys.stdout.flush()
    sys.stderr.flush()

    try:
        print("Attempting to connect to root endpoint...", file=sys.stderr, flush=True)
        response = urllib.request.urlopen("http://127.0.0.1:8766/", timeout=10)
        data = response.read()
        print("SUCCESS", flush=True)
        print(f"Status: {response.status}", flush=True)
        print(f"Data: {data.decode()}", flush=True)
        return 0
    except Exception as e:
        print("FAILED", file=sys.stderr, flush=True)
        print(f"Error type: {type(e).__name__}", file=sys.stderr, flush=True)
        print(f"Error: {e}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
