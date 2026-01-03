#!/usr/bin/env python
"""Verify chatbot query answers against actual database."""
from sqlalchemy import create_engine, text
import os

db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://filemanager:filemanager@mysql:3306/filemanager')
engine = create_engine(db_url)

print('QUESTION: Users who uploaded less than 3 files + who approved them')
print('='*70)

with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT u.full_name, u.email, u.status,
               approver.full_name as approved_by_name,
               COUNT(f.id) as file_count
        FROM users u
        LEFT JOIN files f ON u.id = f.user_id
        LEFT JOIN users approver ON u.approved_by = approver.id
        GROUP BY u.id, u.full_name, u.email, u.status, approver.full_name
        HAVING COUNT(f.id) < 3
        ORDER BY file_count
    '''))
    rows = list(result)
    print(f'CORRECT ANSWER: {len(rows)} users')
    print()
    for i, row in enumerate(rows, 1):
        approver = row.approved_by_name if row.approved_by_name else 'Not approved yet'
        print(f'{i}. {row.full_name} ({row.email})')
        print(f'   Files: {row.file_count}, Status: {row.status}')
        print(f'   Approved by: {approver}')
        print()
