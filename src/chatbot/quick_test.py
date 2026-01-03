#!/usr/bin/env python3
"""Quick test for chatbot queries."""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_queries():
    # Login
    print("Logging in...")
    login = requests.post(
        f'{BASE_URL}/api/v1/auth/login',
        json={'email': 'Admin@filemanager.com', 'password': 'Admin1234'}
    )
    token = login.json()['data']['access_token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print("Login successful!")
    
    # Test queries
    queries = [
        'approved users',
        'pending users', 
        'users without files',
        'admin users',
        'empty folders',
        'pdf files',
        'average file size',
        'how many users',
        'largest files',
        'monthly upload trend',
    ]
    
    print("\n" + "="*60)
    print("TESTING NEW QUERIES")
    print("="*60)
    
    passed = 0
    for q in queries:
        start = time.time()
        try:
            resp = requests.post(
                f'{BASE_URL}/api/v1/chat',
                headers=headers,
                json={'message': q},
                timeout=30
            )
            elapsed = (time.time() - start) * 1000
            data = resp.json()
            
            route = data.get('routing', {}).get('method', 'N/A')
            proc_time = data.get('routing', {}).get('elapsed_ms', 'N/A')
            response_msg = data.get('response', {}).get('message', '')
            has_data = len(response_msg) > 10
            
            # Check if routed to template SQL (good) or LLM (slow)
            if route in ['analytics_template_sql', 'embedding_classifier', 'rule_based']:
                status = "✅ FAST"
                passed += 1
            elif route == 'text_to_sql_llm':
                status = "⚠️  LLM"
            elif route == 'llm_chat':
                status = "⚠️  LLM"
            else:
                status = "❓ UNKNOWN"
            
            print(f"\n{status} Query: '{q}'")
            print(f"   Route: {route}")
            print(f"   Time: {int(elapsed)}ms (reported: {proc_time}ms)")
            print(f"   Has data: {has_data}")
            
        except Exception as e:
            print(f"\n❌ Query: '{q}'")
            print(f"   Error: {e}")
    
    print("\n" + "="*60)
    print(f"FAST ROUTES: {passed}/{len(queries)}")
    print("="*60)

if __name__ == "__main__":
    test_queries()
