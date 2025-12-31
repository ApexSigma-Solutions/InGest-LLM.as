#!/usr/bin/env python
import urllib.request
import subprocess
import time
import json
import os
import sys

os.environ['POSTGRES_DSN'] = 'postgresql://omega_user:omega_dev_password@127.0.0.1:5800/omega_kg_stable'
os.environ['LINEAR_WEBHOOK_SECRET'] = '76adJqIUya6kXGDbICTRFo38M5H32Koo19t0TbeRY1Y'
os.environ['CIRCUIT_BREAKER_THRESHOLD'] = '3'
os.environ['CIRCUIT_BREAKER_TIMEOUT'] = '300'

print("Starting service in background...")
import uvicorn
from ingest_llm.main import app

# Start uvicorn in subprocess
cmd = [sys.executable, '-m', 'uvicorn', 'ingest_llm.main:app', '--host', '127.0.0.1', '--port', '8768']
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

print(f"Service started with PID: {proc.pid}")
time.sleep(5)

try:
    print("\n=== Test 1: Health Check ===")
    response = urllib.request.urlopen('http://127.0.0.1:8768/api/v1/health', timeout=10)
    print(f"Status: {response.status}")
    print(f"Response: {response.read().decode()}")
    
    print("\n=== Test 2: Webhook POST ===")
    payload = b'{"action":"create","data":{"id":"VERIFY-001"}}'
    req = urllib.request.Request('http://127.0.0.1:8768/api/v1/webhook/linear', data=payload, method='POST')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Linear-Signature', 'test')
    
    response = urllib.request.urlopen(req, timeout=10)
    print(f"Status: {response.status}")
    print(f"Response: {response.read().decode()}")
    
    print("\n=== Test 3: Check Database ===")
    # This would require docker exec
    print("Run manually: docker exec apexsigma.postgres.stable psql -U omega_user -d omega_kg_stable -c \"SELECT status FROM ingest_transactions WHERE webhook_payload::jsonb->'data'->>'id' = 'VERIFY-001';\"")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
finally:
    print("\nStopping service...")
    proc.terminate()
    proc.wait(timeout=5)
    print("Done")
