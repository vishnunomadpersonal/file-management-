#!/usr/bin/env python
"""
Test NVIDIA NIM API directly.
Requires NVIDIA_API_KEY environment variable to be set.
"""
import asyncio
import os
import sys

# Ensure required env vars are set
if not os.environ.get("NVIDIA_API_KEY"):
    print("ERROR: Set NVIDIA_API_KEY environment variable")
    sys.exit(1)
os.environ["LLM_PROVIDER"] = "nvidia"

sys.path.insert(0, '/var/www')

from chatbot.providers.nvidia_provider import NvidiaProvider, NvidiaLangChainLLM

async def test_nvidia():
    print("="*60)
    print("TESTING NVIDIA NIM API")
    print("="*60)
    
    # Test basic chat
    provider = NvidiaProvider()
    print(f"Model: {provider.model}")
    
    # Simple test
    print("\n1. Simple test:")
    response = await provider.chat("What is 2+2?")
    print(f"   Success: {response.success}")
    print(f"   Response: {response.message[:200]}...")
    
    # SQL generation test
    print("\n2. SQL Generation test:")
    schema = """
    TABLE: users - columns: id, name, email, status, approved_by
    TABLE: files - columns: id, filename, size, user_id
    """
    sql = await provider.generate_sql(
        "Show me users who uploaded less than 3 files with their approver names",
        schema
    )
    print(f"   SQL: {sql}")
    
    print("\n" + "="*60)
    print("NVIDIA NIM TEST COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_nvidia())
