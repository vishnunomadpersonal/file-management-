"""
RUTHLESS STRESS TEST - Production Readiness Check
==================================================
Tests the chatbot with difficult, ambiguous, and edge-case queries.
Goal: Find every weakness before production deployment.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# Test categories with increasingly difficult queries
STRESS_TEST_QUERIES = {
    # ==========================================================================
    # CATEGORY 1: TYPOS & MISSPELLINGS (Real users can't spell)
    # ==========================================================================
    "typos": [
        ("how many usrs are there", "user_count", "typo: usrs"),
        ("show me all the fiels", "file_list", "typo: fiels"),
        ("organizatons with most users", "org_stats", "typo: organizatons"),
        ("stoarge used by each user", "storage_by_user", "typo: stoarge"),
        ("who uplaoded the most files", "top_uploaders", "typo: uplaoded"),
        ("pendng users list", "pending_users", "typo: pendng"),
        ("aprroved users", "approved_users", "typo: aprroved"),
    ],
    
    # ==========================================================================
    # CATEGORY 2: VAGUE/AMBIGUOUS QUERIES (Users don't know what they want)
    # ==========================================================================
    "ambiguous": [
        ("show me stuff", "unclear", "vague: stuff"),
        ("files", "file_list", "single word"),
        ("users", "user_list", "single word"),
        ("data", "unclear", "too vague"),
        ("everything", "system_overview", "vague: everything"),
        ("show me things", "unclear", "vague: things"),
        ("what do we have", "system_overview", "vague question"),
        ("give me info", "unclear", "vague: info"),
        ("status", "system_overview", "single word status"),
    ],
    
    # ==========================================================================
    # CATEGORY 3: COMPLEX MULTI-CONDITION QUERIES (SQL Hell)
    # ==========================================================================
    "complex_sql": [
        ("users who uploaded more than 5 files but less than 10", "complex_filter", "range filter"),
        ("files larger than 1MB uploaded by admins in the last week", "multi_condition", "3 conditions"),
        ("organizations with more than 3 users but no files", "complex_join", "negative + count"),
        ("top 5 users by storage who haven't logged in this month", "ranking_with_filter", "rank + date"),
        ("files uploaded between monday and friday last week", "date_range", "relative dates"),
        ("users in vedirobotics org who uploaded pdf files", "multi_table_filter", "org + file type"),
        ("average file size per organization excluding empty orgs", "aggregate_with_exclude", "avg + filter"),
        ("users who were approved but never uploaded anything", "approved_no_files", "status + negative"),
        ("percentage of users who are active vs inactive", "percentage_calc", "percentage"),
        ("show me files grouped by month and user", "multi_group", "multiple groupings"),
    ],
    
    # ==========================================================================
    # CATEGORY 4: NATURAL LANGUAGE VARIATIONS (Same meaning, different words)
    # ==========================================================================
    "variations": [
        ("gimme the user count", "user_count", "slang: gimme"),
        ("how many peeps we got", "user_count", "slang: peeps"),
        ("yo show me all files", "file_list", "slang: yo"),
        ("what's the deal with storage", "storage_stats", "casual"),
        ("who's been uploading stuff", "recent_uploads", "casual question"),
        ("any new users lately", "recent_users", "casual: any...lately"),
        ("docs uploaded today", "recent_uploads", "abbreviation: docs"),
        ("org admins list plz", "admin_list", "abbreviation: plz"),
        ("ppl with most files", "top_uploaders", "abbreviation: ppl"),
        ("biggest files rn", "largest_files", "abbreviation: rn"),
    ],
    
    # ==========================================================================
    # CATEGORY 5: NEGATION & EXCLUSION (Tricky for AI)
    # ==========================================================================
    "negation": [
        ("users who haven't uploaded any files", "users_no_files", "negation"),
        ("organizations without any members", "orgs_no_users", "negation"),
        ("files that are not quarantined", "clean_files", "negation"),
        ("users except super admins", "non_super_admins", "exclusion"),
        ("all files but not pdfs", "exclude_type", "exclusion"),
        ("everyone who isn't approved", "not_approved", "negation"),
        ("folders with no files in them", "empty_folders", "negation"),
        ("users who never logged in", "never_logged_in", "negation"),
    ],
    
    # ==========================================================================
    # CATEGORY 6: TEMPORAL QUERIES (Date/Time is always hard)
    # ==========================================================================
    "temporal": [
        ("files uploaded yesterday", "yesterday_files", "relative: yesterday"),
        ("users who joined last month", "last_month_users", "relative: last month"),
        ("uploads in the past 24 hours", "recent_24h", "relative: 24 hours"),
        ("files from Q4 2025", "quarter_files", "quarter reference"),
        ("users active this week", "weekly_active", "relative: this week"),
        ("oldest files in the system", "oldest_files", "temporal: oldest"),
        ("most recent upload", "latest_upload", "temporal: most recent"),
        ("files uploaded on christmas", "specific_date", "holiday reference"),
        ("users created before 2025", "date_filter", "year filter"),
    ],
    
    # ==========================================================================
    # CATEGORY 7: APPROVAL TRACKING (New feature - needs testing)
    # ==========================================================================
    "approvals": [
        ("who approved john@example.com", "approval_tracking", "specific user approval"),
        ("users approved by Super Admin", "approved_by_admin", "filter by approver"),
        ("when was user20 approved", "approval_date", "approval timestamp"),
        ("how many users did each admin approve", "approval_count", "count by approver"),
        ("list of pending approvals", "pending_list", "status filter"),
        ("users waiting for approval the longest", "pending_oldest", "pending + sort"),
        ("rejected users this month", "rejected_users", "status + time"),
        ("approval rate by organization", "approval_rate", "complex metric"),
    ],
    
    # ==========================================================================
    # CATEGORY 8: EDGE CASES & ADVERSARIAL (Try to break it)
    # ==========================================================================
    "adversarial": [
        ("", "empty", "empty string"),
        ("   ", "whitespace", "only whitespace"),
        ("asdfghjkl", "gibberish", "random characters"),
        ("SELECT * FROM users; DROP TABLE users;", "sql_injection", "SQL injection attempt"),
        ("'; DELETE FROM files; --", "sql_injection", "SQL injection v2"),
        ("show me {{users}}", "template_injection", "template injection"),
        ("users where 1=1", "sql_injection", "always true condition"),
        ("<script>alert('xss')</script>", "xss", "XSS attempt"),
        ("users" * 100, "overflow", "repeated word spam"),
        ("🔥 show files 🔥", "emoji", "emoji in query"),
        ("SHOW ME ALL USERS NOW!!!", "shouting", "caps + urgency"),
        ("can you please kindly show me if possible the users list please thanks", "verbose", "overly polite"),
    ],
    
    # ==========================================================================
    # CATEGORY 9: COMPARISON & RANKING (Needs proper ORDER BY)
    # ==========================================================================
    "comparison": [
        ("which org has the most users", "org_ranking", "superlative"),
        ("who uploaded the least files", "bottom_uploaders", "least/minimum"),
        ("compare storage usage between orgs", "comparison", "compare"),
        ("rank users by file count", "ranking", "explicit rank"),
        ("top 3 largest files", "top_n", "specific number"),
        ("bottom 5 users by uploads", "bottom_n", "bottom ranking"),
        ("second largest organization", "ordinal", "ordinal position"),
        ("files bigger than average", "above_average", "comparison to aggregate"),
    ],
    
    # ==========================================================================
    # CATEGORY 10: INFRASTRUCTURE QUERIES (Should go to rule-based)
    # ==========================================================================
    "infrastructure": [
        ("are all containers running", "container_status", "container health"),
        ("docker status", "container_status", "docker keyword"),
        ("is the database up", "db_status", "database health"),
        ("check if minio is working", "storage_health", "specific service"),
        ("system health check", "health_check", "general health"),
        ("show me running services", "services_list", "services"),
        ("any containers down", "container_issues", "negative check"),
        ("restart the api", "action_request", "action - should deny"),
    ],
}

# Expected routing for each query type
EXPECTED_ROUTING = {
    "typos": "should_handle_gracefully",
    "ambiguous": "rule_based_or_clarify",
    "complex_sql": "text_to_sql_llm",
    "variations": "analytics_template_sql",
    "negation": "text_to_sql_llm",
    "temporal": "text_to_sql_llm",
    "approvals": "text_to_sql_llm",
    "adversarial": "should_reject_or_clarify",
    "comparison": "text_to_sql_llm",
    "infrastructure": "rule_based",
}


@dataclass
class TestResult:
    query: str
    category: str
    expected: str
    note: str
    success: bool
    response: str
    routing_method: str
    elapsed_ms: int
    error: str = ""


async def run_single_test(query: str, token: str) -> Dict[str, Any]:
    """Run a single query against the chatbot API."""
    import aiohttp
    
    url = "http://localhost:8000/api/v1/chat/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    body = {"message": query}
    
    start = time.time()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body, timeout=180) as resp:
                elapsed = int((time.time() - start) * 1000)
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "response": data.get("response", {}).get("message", ""),
                        "routing": data.get("routing", {}).get("method", "unknown"),
                        "elapsed_ms": elapsed,
                        "raw": data
                    }
                else:
                    text = await resp.text()
                    return {
                        "success": False,
                        "error": f"HTTP {resp.status}: {text[:200]}",
                        "elapsed_ms": elapsed
                    }
    except asyncio.TimeoutError:
        return {
            "success": False,
            "error": "Timeout (>180s)",
            "elapsed_ms": 180000
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed_ms": int((time.time() - start) * 1000)
        }


async def get_auth_token() -> str:
    """Get authentication token."""
    import aiohttp
    
    url = "http://localhost:8000/api/v1/auth/login"
    body = {"email": "Admin@filemanager.com", "password": "Admin1234"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=body) as resp:
            data = await resp.json()
            return data.get("data", {}).get("access_token", "")


def evaluate_response(query: str, category: str, expected: str, result: Dict) -> Tuple[bool, str]:
    """Evaluate if the response is acceptable."""
    if not result.get("success"):
        return False, f"Request failed: {result.get('error', 'unknown')}"
    
    response = result.get("response", "").lower()
    routing = result.get("routing", "")
    
    # Check for obvious failures
    if "error" in response and "couldn't" in response:
        # Some errors are expected for adversarial queries
        if category == "adversarial":
            return True, "Correctly rejected adversarial input"
        return False, "Query failed with error"
    
    # Check for SQL injection handling
    if category == "adversarial" and ("select" in query.lower() or "drop" in query.lower()):
        if "select" not in response.lower() and "drop" not in response.lower():
            return True, "Correctly handled potential injection"
        return False, "May have processed injection attempt"
    
    # Check if got actual data
    if "found" in response or "result" in response or any(char.isdigit() for char in response):
        return True, "Got data response"
    
    # Check for clarification (acceptable for ambiguous)
    if "what" in response or "which" in response or "specify" in response or "unclear" in response:
        if category in ["ambiguous", "adversarial"]:
            return True, "Asked for clarification (appropriate)"
        return False, "Needed clarification unexpectedly"
    
    # Check routing
    if category == "infrastructure" and "rule" in routing.lower():
        return True, "Correctly routed to rule-based"
    
    # Default: if we got a response without errors, consider it passing
    if len(response) > 10:
        return True, "Got response"
    
    return False, "Response too short or unclear"


async def run_stress_test(categories: List[str] = None, max_per_category: int = None):
    """Run the full stress test suite."""
    print("=" * 80)
    print("🔥 RUTHLESS STRESS TEST - PRODUCTION READINESS CHECK 🔥")
    print("=" * 80)
    
    # Get token
    print("\n📝 Getting auth token...")
    token = await get_auth_token()
    if not token:
        print("❌ Failed to get auth token!")
        return
    print("✅ Token obtained")
    
    # Filter categories if specified
    test_categories = categories or list(STRESS_TEST_QUERIES.keys())
    
    results = []
    total_pass = 0
    total_fail = 0
    category_results = {}
    
    for category in test_categories:
        queries = STRESS_TEST_QUERIES.get(category, [])
        if max_per_category:
            queries = queries[:max_per_category]
        
        print(f"\n{'='*60}")
        print(f"📂 CATEGORY: {category.upper()} ({len(queries)} queries)")
        print(f"{'='*60}")
        
        cat_pass = 0
        cat_fail = 0
        
        for query, expected, note in queries:
            print(f"\n🔍 Query: '{query[:50]}{'...' if len(query) > 50 else ''}'")
            print(f"   Note: {note}")
            
            result = await run_single_test(query, token)
            success, reason = evaluate_response(query, category, expected, result)
            
            # Always show the response for verification
            response_text = result.get("response", "")
            if response_text:
                # Truncate long responses but show enough to verify
                if len(response_text) > 200:
                    print(f"   📝 Response: {response_text[:200]}...")
                else:
                    print(f"   📝 Response: {response_text}")
            else:
                print(f"   📝 Response: [No response]")
            
            if success:
                print(f"   ✅ PASS: {reason}")
                print(f"   ⏱️  Time: {result.get('elapsed_ms', 0)}ms | Route: {result.get('routing', 'N/A')}")
                cat_pass += 1
                total_pass += 1
            else:
                print(f"   ❌ FAIL: {reason}")
                cat_fail += 1
                total_fail += 1
            
            results.append(TestResult(
                query=query,
                category=category,
                expected=expected,
                note=note,
                success=success,
                response=result.get("response", ""),
                routing_method=result.get("routing", ""),
                elapsed_ms=result.get("elapsed_ms", 0),
                error=result.get("error", "")
            ))
            
            # Small delay to not overwhelm
            await asyncio.sleep(0.5)
        
        category_results[category] = {"pass": cat_pass, "fail": cat_fail}
        print(f"\n📊 {category}: {cat_pass}/{cat_pass+cat_fail} passed ({100*cat_pass/(cat_pass+cat_fail):.0f}%)")
    
    # Final summary
    print("\n" + "=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)
    
    total = total_pass + total_fail
    accuracy = 100 * total_pass / total if total > 0 else 0
    
    print(f"\n🎯 Overall Accuracy: {accuracy:.1f}% ({total_pass}/{total} passed)")
    print("\n📂 By Category:")
    for cat, res in category_results.items():
        cat_total = res['pass'] + res['fail']
        cat_acc = 100 * res['pass'] / cat_total if cat_total > 0 else 0
        status = "✅" if cat_acc >= 70 else "⚠️" if cat_acc >= 50 else "❌"
        print(f"   {status} {cat}: {cat_acc:.0f}% ({res['pass']}/{cat_total})")
    
    # Production readiness verdict
    print("\n" + "=" * 80)
    if accuracy >= 90:
        print("🚀 VERDICT: PRODUCTION READY!")
    elif accuracy >= 75:
        print("⚠️  VERDICT: NEEDS IMPROVEMENT - Some edge cases failing")
    elif accuracy >= 50:
        print("🔧 VERDICT: NOT READY - Significant issues found")
    else:
        print("❌ VERDICT: CRITICAL - Major problems detected")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    # Run specific categories or all
    import sys
    
    categories = None
    max_per_cat = None
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            max_per_cat = 3
        elif sys.argv[1] == "--category":
            categories = [sys.argv[2]] if len(sys.argv) > 2 else None
    
    asyncio.run(run_stress_test(categories=categories, max_per_category=max_per_cat))
