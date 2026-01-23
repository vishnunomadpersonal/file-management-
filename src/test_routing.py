#!/usr/bin/env python
"""Test the navigation routing fix directly."""

import sys
sys.path.insert(0, '/var/www')

from chatbot.orchestrator import ChatbotOrchestrator

# Create orchestrator
orchestrator = ChatbotOrchestrator()

# Test queries that should NOT go to analytics (navigation)
navigation_queries = [
    "where can i see files i have uploaded",
    "take me to files i have uploaded",
    "files i have uploaded",
    "my files",
    "go to files",
    "where can i check my uploaded files",
]

# Test queries that SHOULD go to analytics (data queries)
analytics_queries = [
    "how many files do i have",
    "show my recent files",
    "what files did i upload today",
    "list my files",
]

print("=" * 70)
print("ROUTING TEST: Navigation vs Analytics")
print("=" * 70)

print("\n📍 NAVIGATION queries (should NOT use analytics):")
for q in navigation_queries:
    should_use_analytics = orchestrator._should_use_analytics(q)
    status = "❌ WRONG (analytics)" if should_use_analytics else "✅ CORRECT (not analytics)"
    print(f"  {status}: '{q}'")

print("\n📊 ANALYTICS queries (SHOULD use analytics):")
for q in analytics_queries:
    should_use_analytics = orchestrator._should_use_analytics(q)
    status = "✅ CORRECT (analytics)" if should_use_analytics else "❌ WRONG (not analytics)"
    print(f"  {status}: '{q}'")

print("\n" + "=" * 70)
