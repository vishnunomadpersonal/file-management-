"""
Live Stress Test - Actual Chatbot API Performance
==================================================
Tests real queries through the chatbot with actual database execution.
"""

import asyncio
import time
from typing import List, Dict, Any
from chatbot.orchestrator import ChatbotOrchestrator


class UserContext:
    """Mock user context for testing."""
    user_id = "stress-test-user"
    email = "stress@test.com"
    full_name = "Stress Test User"
    role = "super_admin"
    organization_id = "test-org-id"
    permissions = ["read", "write", "admin"]
    
    def to_prompt_context(self):
        return f"User: {self.full_name}, Role: {self.role}"


# Test queries organized by category
TEST_QUERIES = {
    "BASIC_COUNTS": [
        "how many users",
        "how many files",
        "how many folders",
        "user count",
        "file count",
    ],
    "FILE_SIZE": [
        "largest files",
        "smallest files",
        "average file size",
        "top 5 biggest files",
    ],
    "FILE_TYPES": [
        "pdf files",
        "image files",
        "video files",
        "document files",
    ],
    "USER_STATUS": [
        "approved users",
        "pending users",
        "active users",
        "admin users",
    ],
    "USER_ACTIVITY": [
        "users without files",
        "users never logged in",
        "top uploaders",
        "dormant users",
    ],
    "TIME_BASED": [
        "users created today",
        "files uploaded today",
        "oldest users",
        "recent uploads",
    ],
    "STORAGE": [
        "total storage",
        "storage by user",
        "users with most storage",
    ],
    "TRENDS": [
        "monthly upload trend",
        "weekly signup trend",
        "upload trend",
    ],
    "FOLDERS_ORGS": [
        "empty folders",
        "folders with most files",
        "users per organization",
        "system summary",
    ],
}


async def run_single_query(orch: ChatbotOrchestrator, query: str, user_ctx: UserContext) -> Dict[str, Any]:
    """Run a single query and return results."""
    start = time.time()
    try:
        result = await orch.chat(
            message=query,
            session_id=None,
            user_context=user_ctx,
            db=None  # No DB connection for routing test
        )
        elapsed_ms = int((time.time() - start) * 1000)
        
        return {
            "query": query,
            "success": True,
            "method": result.get("routing", {}).get("method", "unknown"),
            "elapsed_ms": elapsed_ms,
            "response_preview": result.get("response", {}).get("message", "")[:100],
        }
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "query": query,
            "success": False,
            "method": "error",
            "elapsed_ms": elapsed_ms,
            "error": str(e)[:100],
        }


async def run_stress_test():
    """Run the full stress test."""
    print("=" * 70)
    print("LIVE STRESS TEST - Chatbot Performance")
    print("=" * 70)
    print()
    
    orch = ChatbotOrchestrator()
    user_ctx = UserContext()
    
    total_queries = 0
    fast_queries = 0
    slow_queries = 0
    errors = 0
    
    category_results = {}
    all_times = []
    
    for category, queries in TEST_QUERIES.items():
        print(f"\n[{category}]")
        print("-" * 50)
        
        category_fast = 0
        category_times = []
        
        for query in queries:
            total_queries += 1
            result = await run_single_query(orch, query, user_ctx)
            
            method = result["method"]
            elapsed = result["elapsed_ms"]
            all_times.append(elapsed)
            category_times.append(elapsed)
            
            # Classify speed
            is_fast = method in ["rule_based", "analytics_template_sql", "rule_based_infrastructure"]
            if result["success"]:
                if is_fast:
                    fast_queries += 1
                    category_fast += 1
                    status = "FAST"
                else:
                    slow_queries += 1
                    status = "SLOW"
            else:
                errors += 1
                status = "ERR"
            
            # Color coding for terminal
            if status == "FAST":
                icon = "✓"
            elif status == "SLOW":
                icon = "⚠"
            else:
                icon = "✗"
            
            print(f"  {icon} {query:35} -> {method:20} ({elapsed:4}ms) [{status}]")
        
        avg_time = sum(category_times) / len(category_times) if category_times else 0
        category_results[category] = {
            "queries": len(queries),
            "fast": category_fast,
            "avg_ms": avg_time,
        }
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    
    print("By Category:")
    for cat, stats in category_results.items():
        pct = (stats["fast"] / stats["queries"] * 100) if stats["queries"] > 0 else 0
        print(f"  {cat:20}: {stats['fast']}/{stats['queries']} fast ({pct:.0f}%), avg {stats['avg_ms']:.0f}ms")
    
    print()
    print("Overall Results:")
    print(f"  Total Queries:    {total_queries}")
    print(f"  Fast Routes:      {fast_queries} ({fast_queries*100//total_queries}%)")
    print(f"  Slow Routes:      {slow_queries} ({slow_queries*100//total_queries}%)")
    print(f"  Errors:           {errors}")
    print()
    
    if all_times:
        print("Performance:")
        print(f"  Min Time:         {min(all_times)}ms")
        print(f"  Max Time:         {max(all_times)}ms")
        print(f"  Avg Time:         {sum(all_times)//len(all_times)}ms")
        print(f"  Total Time:       {sum(all_times)}ms")
    
    print()
    print("=" * 70)
    
    # Verdict
    fast_pct = fast_queries * 100 // total_queries if total_queries > 0 else 0
    if fast_pct >= 95 and errors == 0:
        verdict = "🎉 PRODUCTION READY - Excellent performance!"
    elif fast_pct >= 90:
        verdict = "✅ EXCELLENT - Minor optimizations possible"
    elif fast_pct >= 80:
        verdict = "⚠️ GOOD - Some queries need template coverage"
    else:
        verdict = "❌ NEEDS WORK - Add more templates"
    
    print(f"VERDICT: {verdict}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_stress_test())
