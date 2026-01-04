"""Test the three fixed queries."""
import asyncio
from chatbot.orchestrator import ChatbotOrchestrator
from chatbot.providers.base import UserContext


async def test():
    chatbot = ChatbotOrchestrator()
    ctx = UserContext(user_id='1', email='admin@test.com', role='super_admin', organization_id='1')
    
    tests = [
        'show me running services',
        'top 3 largest files',
        'users created before 2025'
    ]
    
    for q in tests:
        print(f'Q: {q}')
        result = await chatbot.chat(q, ctx)
        response = result['response']
        routing = result.get('routing', {})
        method = routing.get('method', 'unknown')
        msg = response['message'][:150]
        print(f'   Route: {method}')
        print(f'   Response: {msg}...')
        print()


if __name__ == '__main__':
    asyncio.run(test())
