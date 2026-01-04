import asyncio
import time
import os
import sys

# Ensure required env vars are set
if not os.environ.get("NVIDIA_API_KEY"):
    print("ERROR: Set NVIDIA_API_KEY environment variable")
    sys.exit(1)
os.environ["LLM_PROVIDER"] = "nvidia"

from chatbot.text_to_sql_langchain import LangChainSQLAgent

async def test():
    print("=" * 60)
    print("TESTING CHATBOT WITH NVIDIA NIM API")
    print("=" * 60)
    
    agent = LangChainSQLAgent(model="gemma2:2b")
    print(f"Provider: {agent.llm_provider}")
    print()
    
    queries = [
        "How many users are there?",
        "Show top 5 largest files",
        "Which users have less than 3 files?"
    ]
    
    user_info = {"role": "super_admin"}
    
    for q in queries:
        print(f"Q: {q}")
        start = time.time()
        result = await agent.query(q, user_info)
        elapsed = time.time() - start
        response = result.get("response", "ERROR")
        print(f"A: {response[:300] if len(response) > 300 else response}")
        print(f"Time: {elapsed:.2f}s")
        print("-" * 40)

asyncio.run(test())
