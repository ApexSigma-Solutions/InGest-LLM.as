#!/usr/bin/env python
"""Test script for health endpoint"""

import urllib.request
import sys
import json


def main():
    try:
        print("Attempting to connect to health endpoint...", file=sys.stderr)
        response = urllib.request.urlopen(
            "http://127.0.0.1:8766/api/v1/health", timeout=10
        )
        data = response.read()
        print("SUCCESS")
        print(f"Status: {response.status}")
        print(f"Data: {data.decode()}")
        return 0
    except Exception as e:
        print(f"FAILED", file=sys.stderr)
        print(f"Error type: {type(e).__name__}", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
