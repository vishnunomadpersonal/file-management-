"""Test the three fixed queries via API."""
import requests
import json

# Login
login_resp = requests.post('http://localhost:8000/api/v1/auth/login', json={
    'email': 'Admin@filemanager.com',
    'password': 'Admin1234'
})
login_data = login_resp.json()
print(f"Login response: {login_data}")
token = login_data.get('data', {}).get('access_token') or login_data.get('access_token')
if not token:
    print("Failed to get token")
    exit(1)
    
headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

# Test the three queries
queries = [
    'show me running services',
    'top 3 largest files',
    'users created before 2025'
]

for q in queries:
    resp = requests.post('http://localhost:8000/api/v1/chat/', 
        headers=headers, 
        json={'message': q}
    )
    data = resp.json()
    routing = data.get('routing', {})
    method = routing.get('method', 'unknown')
    response_msg = data.get('response', {}).get('message', 'ERROR')[:150]
    print(f'Q: {q}')
    print(f'   Route: {method}')
    print(f'   Response: {response_msg}...')
    print()
