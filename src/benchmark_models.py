"""Benchmark NVIDIA NIM models for SQL generation.
Requires NVIDIA_API_KEY environment variable to be set.
"""
import httpx
import asyncio
import time
import os
import sys

API_KEY = os.environ.get('NVIDIA_API_KEY')
if not API_KEY:
    print("ERROR: Set NVIDIA_API_KEY environment variable")
    sys.exit(1)

MODELS = [
    ('meta/llama-3.3-70b-instruct', 'Llama 3.3 70B (newest)'),
    ('nvidia/llama-3.3-nemotron-super-49b-v1', 'Nemotron Super 49B'),
    ('meta/llama-3.1-70b-instruct', 'Llama 3.1 70B (current)'),
    ('mistralai/mixtral-8x22b-instruct-v0.1', 'Mixtral 8x22B'),
]

QUERIES = [
    'Count total users',
    'Show top 5 largest files with uploader name',
    'Users with less than 3 files and their approver',
    'Storage used by each organization in MB',
    'Files uploaded this week grouped by user'
]

SCHEMA = '''Tables: users(id,name,email,role,organization_id,approved_by,created_at), 
files(id,filename,size,user_id,organization_id,virus_scan_date), 
organizations(id,name,storage_used_bytes)'''


async def benchmark():
    headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}
    
    print('=' * 70)
    print('NVIDIA MODEL BENCHMARK - 5 SQL Queries')
    print('=' * 70)
    
    results = {}
    
    async with httpx.AsyncClient(timeout=90.0) as client:
        for model_id, model_name in MODELS:
            print(f'\n🔥 {model_name} ({model_id})')
            print('-' * 50)
            
            times = []
            successes = 0
            
            for q in QUERIES:
                prompt = f'{SCHEMA}\nGenerate MySQL SELECT query for: {q}\nOutput ONLY SQL.'
                payload = {
                    'model': model_id,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'max_tokens': 300,
                    'temperature': 0.1
                }
                
                start = time.time()
                try:
                    resp = await client.post(
                        'https://integrate.api.nvidia.com/v1/chat/completions',
                        headers=headers,
                        json=payload
                    )
                    elapsed = time.time() - start
                    times.append(elapsed)
                    
                    if resp.status_code == 200:
                        successes += 1
                        print(f'  ✅ {q[:35]:35} | {elapsed:.2f}s')
                    else:
                        print(f'  ❌ {q[:35]:35} | HTTP {resp.status_code}')
                except Exception as e:
                    print(f'  ❌ {q[:35]:35} | Error: {e}')
                    times.append(99)
            
            avg = sum(times) / len(times)
            results[model_name] = {'avg': avg, 'success': successes}
            print(f'  📊 Avg: {avg:.2f}s | Success: {successes}/5')
    
    print('\n' + '=' * 70)
    print('SUMMARY - Best Models for SQL Generation')
    print('=' * 70)
    
    sorted_results = sorted(results.items(), key=lambda x: (-x[1]['success'], x[1]['avg']))
    medals = ['🥇', '🥈', '🥉', '4️⃣']
    for i, (name, data) in enumerate(sorted_results):
        medal = medals[i] if i < 4 else ''
        print(f"{medal} {name}: {data['avg']:.2f}s avg, {data['success']}/5 success")


if __name__ == '__main__':
    asyncio.run(benchmark())
