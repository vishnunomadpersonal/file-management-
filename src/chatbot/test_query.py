#!/usr/bin/env python
"""Quick query tester."""
import requests
import time
import sys

# Login
r = requests.post('http://localhost:8000/api/v1/auth/login', 
                  json={'email': 'Admin@filemanager.com', 'password': 'Admin1234'})
token = r.json()['data']['access_token']

# Get query from args or use default
query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'how many users'

print('=' * 60)
print('QUERY:', query)
print('=' * 60)

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
print('RESPONSE:', data.get('response', {}).get('message', ''))
