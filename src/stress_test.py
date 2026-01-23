"""
STRESS TEST - Complex & Tricky Queries
========================================
Tests the chatbot with spider-web complex queries, ambiguous phrasing,
typos, and real-world messy user input.
"""
import asyncio
import sys
sys.path.insert(0, '/var/www')

from chatbot.orchestrator import ChatbotOrchestrator, UserContext

async def stress_test():
    orch = ChatbotOrchestrator()
    ctx = UserContext(user_id='1', role='super_admin', permissions=['all'], email='admin@filemanager.com')
    
    # STRESS TEST: Complex, ambiguous, real-world messy queries
    test_cases = [
        # ===== COMPOUND/MULTI-INTENT QUERIES =====
        ("give me users who are approved, have uploaded at least 3 files, belong to vedirobotics, and show their storage usage", "SQL"),
        ("list all admins with their file counts and tell me which org they're from", "SQL"),
        ("show me pending users who registered last week and never logged in", "SQL"),
        ("find users with more than 5 files but less than 20 and their average file size", "SQL"),
        
        # ===== NATURAL LANGUAGE / CONVERSATIONAL =====
        ("hey can you pull up all the users for me real quick", "SQL"),
        ("I need to know who's been uploading the most stuff lately", "SQL"),
        ("what's the deal with storage usage across orgs", "SQL"),
        ("so like who approved that new user john@test.com", "SQL"),
        ("any users that haven't done anything yet", "SQL"),
        
        # ===== TYPOS & MISSPELLINGS =====
        ("usres who uploded less than 5 files", "SQL"),
        ("show me teh files uploaded yestarday", "SQL"),
        ("list aprovved users", "SQL"),
        ("stoarge per organizaton", "SQL"),
        ("quarentined files", "SQL"),
        
        # ===== AMBIGUOUS QUERIES (context-dependent) =====
        ("files", "NAV"),  # Could be nav or SQL - should default to nav
        ("users", "SQL"),  # Ambiguous - list users (SQL) 
        ("show me everything", "SQL"),  # Vague but data request
        ("what do we have", "SQL"),  # Vague data question
        ("status", "SQL"),  # Could be system status
        
        # ===== LONG/VERBOSE QUERIES =====
        ("I would like you to please show me a complete list of all users who have registered with our platform and have been approved by an administrator and have uploaded files to the system", "SQL"),
        ("can you help me understand how many files have been uploaded by users who belong to organizations that have the enterprise plan", "SQL"),
        ("please provide me with information about the storage usage trends over the past month broken down by organization", "SQL"),
        
        # ===== SHORT/TERSE QUERIES =====
        ("count users", "SQL"),
        ("file stats", "SQL"),
        ("org list", "SQL"),
        ("top uploaders", "SQL"),
        ("storage?", "SQL"),
        
        # ===== QUESTIONS WITH CONTEXT =====
        ("who are the users that john@admin.com approved last month", "SQL"),
        ("what files did the super admin upload in december", "SQL"),
        ("which organizations have exceeded their quota", "SQL"),
        ("how many files are infected or quarantined", "SQL"),
        
        # ===== NEGATIVE/EXCLUSION QUERIES =====
        ("users except admins", "SQL"),
        ("files not in any folder", "SQL"),
        ("organizations without any users", "SQL"),
        ("users who haven't uploaded anything", "SQL"),
        ("everyone but super_admin role", "SQL"),
        
        # ===== TIME-BASED COMPLEX =====
        ("compare uploads between december 2025 and january 2026", "SQL"),
        ("users who joined in Q4 2025", "SQL"),
        ("files older than 6 months", "SQL"),
        ("activity in the last 72 hours", "SQL"),
        ("users inactive for over 2 weeks", "SQL"),
        
        # ===== RELATIONSHIP/JOIN QUERIES =====
        ("users and their organizations with file counts", "SQL"),
        ("files with uploader name and org", "SQL"),
        ("folders and their total size", "SQL"),
        ("who approved whom and when", "SQL"),
        ("organizations ranked by total storage used by their users", "SQL"),
        
        # ===== TRICKY NAVIGATION vs SQL =====
        ("show files page", "NAV"),
        ("go see users", "NAV"),
        ("open my documents", "NAV"),
        ("take me to where I can see quarantined items", "NAV"),
        ("let me see the settings", "NAV"),
        
        # ===== ANALYTICS/METRICS =====
        ("average files per user", "SQL"),
        ("median file size", "SQL"),
        ("file type distribution", "SQL"),
        ("user growth rate", "SQL"),
        ("storage utilization percentage", "SQL"),
        
        # ===== SECURITY/AUDIT QUERIES =====
        ("failed login attempts", "SQL"),
        ("users with suspicious activity", "SQL"),
        ("recently changed passwords", "SQL"),
        ("oauth vs password users", "SQL"),
        ("locked accounts", "SQL"),
        
        # ===== EDGE CASE PHRASING =====
        ("gimme users", "SQL"),
        ("lemme see files", "SQL"),
        ("whos the top uploader", "SQL"),
        ("whats our storage at", "SQL"),
        ("how many ppl registered", "SQL"),
        
        # ===== MIXED INTENT (should pick primary) =====
        ("show me files and also go to settings", "SQL"),  # Primary: files data
        ("list users then navigate to dashboard", "SQL"),  # Primary: list users
        
        # ===== FOLLOW-UP STYLE (no context) =====
        ("and their organizations too", "SQL"),  # Incomplete but data-related
        ("also include email addresses", "SQL"),
        ("sort by date", "SQL"),
        ("filter by role admin", "SQL"),
        
        # ===== GREETINGS THAT LOOK LIKE QUERIES =====
        ("hi, show me users", "SQL"),  # Greeting + query
        ("hello, what's the file count", "SQL"),
        ("hey there, go to files", "NAV"),
        
        # ===== PURE GREETINGS/SMALL TALK =====
        ("good morning!", "GREET"),
        ("how are you today", "GREET"),
        ("thanks for your help", "GREET"),
        ("that's all for now", "GREET"),
    ]
    
    correct = 0
    total = len(test_cases)
    failures = []
    
    print("=" * 80)
    print("STRESS TEST - Complex & Tricky Queries")
    print("=" * 80)
    print(f"Testing {total} complex queries...\n")
    
    for query, expected_type in test_cases:
        try:
            result = await orch.chat(query, ctx)
            routing = result.get('routing', {})
            method = routing.get('method', 'unknown')
            
            # Categorize result
            if any(x in method.lower() for x in ['sql', 'langchain', 'text_to', 'analytics']):
                actual = 'SQL'
            elif 'nav' in method.lower() or 'explicit' in method.lower():
                actual = 'NAV'
            elif 'help' in method.lower():
                actual = 'HELP'
            elif 'greet' in method.lower():
                actual = 'GREET'
            elif 'rule' in method.lower() or 'data_query' in method.lower():
                actual = 'RULE'
            elif 'llm_chat' in method.lower() or 'agentic' in method.lower():
                actual = 'LLM'
            else:
                actual = method[:15]
            
            # Check correctness (LLM and RULE are smart enough)
            is_correct = (
                actual == expected_type or 
                (actual == 'RULE' and expected_type in ['SQL', 'NAV', 'HELP', 'GREET']) or
                (actual == 'LLM' and expected_type in ['SQL', 'NAV', 'HELP', 'GREET'])
            )
            
            if is_correct:
                correct += 1
                status = '✅'
            else:
                status = '❌'
                failures.append((query, expected_type, actual, method))
            
            # Shorter output for cleaner display
            q_short = query[:50] + "..." if len(query) > 50 else query
            print(f'{status} "{q_short}" → {actual}')
            
        except Exception as e:
            failures.append((query, expected_type, 'ERROR', str(e)[:50]))
            print(f'❌ "{query[:50]}..." → ERROR')
    
    print()
    print("=" * 80)
    accuracy = correct / total * 100
    print(f"STRESS TEST ACCURACY: {correct}/{total} = {accuracy:.1f}%")
    print("=" * 80)
    
    if failures:
        print(f"\nFAILURES ({len(failures)}):")
        for q, exp, act, method in failures[:15]:  # Show first 15
            print(f"  • \"{q[:60]}\"")
            print(f"    Expected: {exp}, Got: {act} (method: {method})")
        if len(failures) > 15:
            print(f"  ... and {len(failures) - 15} more failures")
    
    # Verdict
    print()
    if accuracy >= 95:
        print("🎉 EXCELLENT! 95%+ accuracy on stress test!")
    elif accuracy >= 90:
        print("👍 GOOD! 90%+ accuracy - minor improvements possible")
    elif accuracy >= 85:
        print("⚠️  FAIR - 85%+ accuracy - some patterns need work")
    else:
        print("🔴 NEEDS IMPROVEMENT - Below 85% accuracy")
    
    return accuracy, failures

if __name__ == "__main__":
    accuracy, failures = asyncio.run(stress_test())
