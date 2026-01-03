#!/usr/bin/env python
"""
Test SQL generation and execution directly.
"""
import asyncio
import sys
import os

# Add parent path
sys.path.insert(0, '/var/www')

# Set environment for DB
os.environ.setdefault('DATABASE_URL', 'mysql+pymysql://filemanager_user:filemanager_pass@mysql:3306/filemanager')

from chatbot.text_to_sql_langchain import get_sql_agent

async def test_sql():
    query = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else 'users who uploaded less than 3 files with approver info'
    
    print('='*70)
    print('TESTING SQL GENERATION')
    print('='*70)
    print(f'Query: {query}')
    print('='*70)
    
    # Get agent
    agent = get_sql_agent()
    
    # User info for super admin
    user_info = {
        'user_id': 'test-admin-id',
        'role': 'super_admin',
        'organization_id': None
    }
    
    # Ask the question
    result = await agent.ask(query, user_info=user_info)
    
    print('\nGENERATED SQL:')
    print(result.get('query', 'N/A'))
    print()
    
    print('RAW RESULT:')
    raw = result.get('raw_result', 'N/A')
    print(raw[:2000] if isinstance(raw, str) else raw)
    print()
    
    print('ROW COUNT:', result.get('row_count', 'N/A'))
    print()
    
    print('FORMATTED ANSWER:')
    print(result.get('answer', 'N/A'))


if __name__ == '__main__':
    asyncio.run(test_sql())
