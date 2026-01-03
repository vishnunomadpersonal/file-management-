#!/usr/bin/env python
"""Debug query tester - shows generated SQL."""
import requests
import time
import sys
import json

# Login
r = requests.post('http://localhost:8000/api/v1/auth/login',
                  json={'email': 'Admin@filemanager.com', 'password': 'Admin1234'})
token = r.json()['data']['access_token']

# Get query from args or use default
query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'how many users'

print('=' * 70)
print('QUERY:', query)
print('=' * 70)

start = time.time()
resp = requests.post(
    'http://localhost:8000/api/v1/chat/',
    headers={'Authorization': f'Bearer {token}'},
    json={'message': query},
    timeout=180
)
elapsed = time.time() - start
data = resp.json()

print('TIME:', f'{elapsed:.2f}s')
print('ROUTE:', data.get('routing', {}).get('method', 'unknown'))
print()
print('FULL RESPONSE DATA:')
print(json.dumps(data, indent=2, default=str))
