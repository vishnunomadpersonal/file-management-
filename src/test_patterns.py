#!/usr/bin/env python
"""Test navigation patterns to verify they work correctly."""

import re

# Test patterns (same as in rule_based.py)
patterns = [
    ('Files', re.compile(r'\b(my files?|show files?|view files?|go to files?|open files?|take me to.*files?|navigate.*files?|files? page|where.*(i |my )?(upload|uploaded|stored|saved)|uploaded files?)\b', re.IGNORECASE)),
    ('All Files', re.compile(r'\b(all files|platform files|all documents|every file)\b', re.IGNORECASE)),
    ('Users', re.compile(r'\b(users?|manage users?|user management|show users?|take me to.*users?|list users?)\b', re.IGNORECASE)),
    ('Settings', re.compile(r'\b(settings|preferences|account settings|my account|take me to.*settings)\b', re.IGNORECASE)),
    ('Dashboard', re.compile(r'\b(dashboard|home|main page|go home|take me to.*dashboard|take me home)\b', re.IGNORECASE)),
    ('System Logs', re.compile(r'\b(system\s*logs?|audit\s*logs?|application\s*logs?|app\s*logs?|logs?\s*page|show\s*(me\s+)?(the\s+)?logs?|view\s*(the\s+)?logs?|check\s*(the\s+)?logs?|see\s*(the\s+)?logs?|take me to.*logs?)\b', re.IGNORECASE)),
    ('Organizations', re.compile(r'\b(organizations?|tenants?|take me to\s+(the\s+)?organizations?)\b', re.IGNORECASE)),
    ('Approvals', re.compile(r'\b(approvals?|pending|review)\b', re.IGNORECASE)),
    ('Analytics', re.compile(r'\b(analytics?|reports?|statistics?|metrics?|insights?|take me to.*analytics)\b', re.IGNORECASE)),
    ('API Gateway', re.compile(r'\b(api gateway|gateway|kong|take me to.*gateway)\b', re.IGNORECASE)),
    ('API Keys', re.compile(r'\b(api keys?|keys?|tokens?|take me to.*api.?keys?)\b', re.IGNORECASE)),
    ('Database', re.compile(r'\b(databases?|db|mysql|take me to.*database|where.*(check|see|view|find).*databases?)\b', re.IGNORECASE)),
    ('Infrastructure', re.compile(r'\b(infrastructure|infra|servers?|containers?|docker|services?\s*(status|running|up|down|health)|running\s+services?|show.*services?|list.*services?|everything\s*(up|running)|take me to.*infrastructure|minio|rabbitmq)\b', re.IGNORECASE)),
    ('Platform Admin', re.compile(r'\b(platform admin|platformadmin|admin panel|admin page|take me to.*platform.?admin)\b', re.IGNORECASE)),
    ('Quarantine', re.compile(r'\b(quarantine|quarantined|infected|virus|malware|take me to.*quarantine)\b', re.IGNORECASE)),
    ('Security', re.compile(r'\b(security|permissions|access control|rbac|take me to.*security)\b', re.IGNORECASE)),
    ('Team', re.compile(r'\b(team|members?|colleagues?|staff|take me to.*team)\b', re.IGNORECASE)),
]

# Test cases: (message, expected_destination)
test_cases = [
    # System Logs tests
    ('take me to our application logs', 'System Logs'),
    ('system logs', 'System Logs'),
    ('application logs', 'System Logs'),
    ('show me the logs', 'System Logs'),
    ('check logs', 'System Logs'),
    ('logs page', 'System Logs'),
    
    # Files tests - ORIGINAL
    ('where can i check my uploaded files', 'Files'),
    ('take me where i uploaded my files', 'Files'),
    ('my files', 'Files'),
    ('show files', 'Files'),
    ('where did i upload', 'Files'),
    
    # Files tests - NEW USER QUERIES
    ('where can i see files i have uploaded', 'Files'),
    ('take me to files i have uploaded', 'Files'),
    ('files i have uploaded', 'Files'),
    ('see my uploaded files', 'Files'),
    
    # Organizations tests
    ('take me to organizations', 'Organizations'),
    ('organizations', 'Organizations'),
    ('show organizations', 'Organizations'),
    
    # Infrastructure tests
    ('infrastructure', 'Infrastructure'),
    ('take me to infrastructure', 'Infrastructure'),
    ('show containers', 'Infrastructure'),
    ('docker status', 'Infrastructure'),
    
    # Database tests
    ('database', 'Database'),
    ('take me to database', 'Database'),
    ('where can i check my databases', 'Database'),
    
    # Dashboard tests
    ('home', 'Dashboard'),
    ('dashboard', 'Dashboard'),
    ('take me home', 'Dashboard'),
    
    # Users tests
    ('users', 'Users'),
    ('show users', 'Users'),
    ('manage users', 'Users'),
    
    # Settings tests
    ('settings', 'Settings'),
    ('my account', 'Settings'),
    
    # Analytics tests
    ('analytics', 'Analytics'),
    ('show reports', 'Analytics'),
    
    # API Keys tests
    ('api keys', 'API Keys'),
    
    # Team tests
    ('team', 'Team'),
    ('team members', 'Team'),
    
    # Quarantine tests
    ('quarantine', 'Quarantine'),
    ('quarantined files', 'Quarantine'),
    
    # Security tests  
    ('security', 'Security'),
    ('permissions', 'Security'),
]

def find_first_match(message):
    """Find the first matching pattern (simulates rule-based order)."""
    for name, pattern in patterns:
        if pattern.search(message):
            return name
    return None

def find_all_matches(message):
    """Find all matching patterns."""
    matches = []
    for name, pattern in patterns:
        if pattern.search(message):
            matches.append(name)
    return matches

if __name__ == "__main__":
    print("=" * 70)
    print("NAVIGATION PATTERN TEST")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for msg, expected in test_cases:
        first_match = find_first_match(msg)
        all_matches = find_all_matches(msg)
        
        # Check if expected is in matches (order matters!)
        is_correct = first_match == expected
        status = '✅' if is_correct else '❌'
        
        if is_correct:
            passed += 1
        else:
            failed += 1
        
        print(f'{status} "{msg}"')
        print(f'   Expected: {expected} | Got: {first_match}')
        if len(all_matches) > 1:
            print(f'   ⚠️  Multiple matches: {all_matches}')
        print()
    
    print("=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 70)
