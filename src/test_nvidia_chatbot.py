"""Test NVIDIA NIM API with full chatbot.
Requires NVIDIA_API_KEY environment variable to be set.
"""
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
    print("Provider:", agent.llm_provider)
    print()
    
    queries = [
        "How many users are there?",
        "Show top 5 largest files",
        "Which users have less than 3 files?"
    ]
    
    user_info = {"role": "super_admin"}
    
    for q in queries:
        print("Q:", q)
        start = time.time()
        try:
            result = await agent.ask(q, user_info)
            elapsed = time.time() - start
            
            sql = result.get("query", "N/A")
            answer = result.get("answer", "ERROR")
            success = result.get("success", False)
            error = result.get("error", "")
            
            print("Success:", success)
            if sql:
                print("SQL:", sql)
            if error:
                print("Error:", error)
            print("Answer:", answer[:300] if len(answer) > 300 else answer)
            print("Time: %.2fs" % elapsed)
        except Exception as e:
            print("Exception:", str(e))
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(test())
