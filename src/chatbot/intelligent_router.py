"""
Intelligent Router - Multi-Level Confidence-Based Routing
==========================================================

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────┐
│  Level 1: FAST PATH (< 10ms)                                    │
│  - High-confidence regex patterns                               │
│  - Cached responses for repeated queries                        │
├─────────────────────────────────────────────────────────────────┤
│  Level 2: MEDIUM PATH (< 100ms)                                 │
│  - Embedding-based semantic classification                      │
│  - Intent decomposition for compound queries                    │
├─────────────────────────────────────────────────────────────────┤
│  Level 3: SLOW PATH (< 3s)                                      │
│  - GPT-4o intelligent routing with reasoning                    │
│  - Self-reflection and confidence calibration                   │
└─────────────────────────────────────────────────────────────────┘

IMPROVEMENTS OVER PREVIOUS APPROACH:
1. Proactive confidence scoring (not reactive error detection)
2. Semantic understanding (not just pattern matching)
3. Query decomposition for complex requests
4. Memory for repeated queries
5. Self-reflection loop
"""

import os
import re
import json
import logging
import asyncio
import hashlib
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTE TYPES
# ============================================================================

class RouteType(Enum):
    """All possible routing destinations."""
    NAVIGATION = "navigation"           # Go to a page
    SQL_QUERY = "sql_query"            # Data query (text-to-SQL)
    HELP = "help"                       # Help/documentation
    FILE_OPERATION = "file_operation"   # Upload/download/delete
    USER_MANAGEMENT = "user_management" # User actions
    GREETING = "greeting"               # Hello/hi/bye
    UNKNOWN = "unknown"                 # Can't determine
    COMPOUND = "compound"               # Multiple intents


@dataclass
class RouteDecision:
    """A routing decision with confidence and reasoning."""
    route: RouteType
    confidence: float
    reasoning: str
    sub_queries: List[str] = field(default_factory=list)  # For compound queries
    metadata: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    method: str = "unknown"  # Which level made the decision


@dataclass
class QueryMemory:
    """Memory of past queries for fast retrieval."""
    query_hash: str
    query: str
    route: RouteType
    success: bool
    timestamp: datetime
    response_quality: float = 1.0  # 0-1 rating


# ============================================================================
# CONFIDENCE PATTERNS - Level 1 (FAST)
# ============================================================================

class ConfidencePatterns:
    """
    High-confidence regex patterns with explicit confidence scores.
    Only matches if we're VERY sure about the intent.
    """
    
    # Navigation patterns with confidence
    NAVIGATION_PATTERNS: List[Tuple[re.Pattern, float, str]] = [
        # 0.99 confidence - very explicit
        (re.compile(r'^(go to|navigate to|take me to|open)\s+(my\s+)?(files?|documents?)(\s+page)?$', re.I), 0.99, "files"),
        (re.compile(r'^(go to|navigate to|take me to|open)\s+(my\s+)?(dashboard|home)$', re.I), 0.99, "dashboard"),
        (re.compile(r'^(go to|navigate to|take me to|open)\s+(user\s+)?(settings?|preferences?)$', re.I), 0.99, "settings"),
        (re.compile(r'^(go to|navigate to|take me to|open)\s+(the\s+)?(quarantine|quarantined)(\s+files?)?$', re.I), 0.99, "quarantine"),
        
        # 0.95 confidence - clear intent
        (re.compile(r'\b(show|view|see)\s+(my\s+)?(files?|documents?)\s*(page|section)?$', re.I), 0.95, "files"),
        (re.compile(r'^where\s+(are|can\s+i\s+(find|see|view))\s+(my\s+)?(files?|documents?)(\?)?$', re.I), 0.95, "files"),
        (re.compile(r'\bmy files?\b.*\b(page|section|area)\b', re.I), 0.95, "files"),
        
        # 0.90 confidence - likely navigation
        (re.compile(r'^(files?|documents?|my files?)$', re.I), 0.90, "files"),
        (re.compile(r'\b(check|look at)\s+(my\s+)?(files?|uploads?)\b', re.I), 0.90, "files"),
    ]
    
    # SQL/Analytics patterns with confidence  
    SQL_PATTERNS: List[Tuple[re.Pattern, float, str]] = [
        # 0.99 confidence - explicit data requests
        (re.compile(r'^(how many|count|total)\s+(files?|users?|documents?|uploads?)', re.I), 0.99, "count"),
        (re.compile(r'^(list|show)\s+(all\s+)?(users?|files?)\s+(with|where|who|that)', re.I), 0.99, "list_filtered"),
        (re.compile(r'\b(average|avg|mean|sum|total|max|min)\s+(file\s+)?(size|storage|count)', re.I), 0.99, "aggregation"),
        
        # 0.98 confidence - "give me" data requests (COMMON USER PATTERN)
        (re.compile(r'\b(give me|get me|show me|tell me|find)\s+(all\s+)?(users?|people|folks)\b.*(upload|file|document|storage)', re.I), 0.98, "user_file_query"),
        (re.compile(r'\b(give me|get me|show me|tell me|find)\s+(all\s+)?(files?|documents?)\b.*(user|upload|belong)', re.I), 0.98, "file_user_query"),
        (re.compile(r'\busers?\b.*(upload|file).*(less|fewer|more|greater|under|over|than|at least|at most)\s*\d+', re.I), 0.98, "user_file_count_filter"),
        (re.compile(r'\b(people|folks|users?)\b.*(register|approved|active).*(upload|file)', re.I), 0.98, "user_status_file_query"),
        
        # 0.97 confidence - organization/belonging queries
        (re.compile(r'\b(which|what)\s+organi[sz]ation\b', re.I), 0.97, "org_query"),
        (re.compile(r'\bbelong\s+to\b', re.I), 0.97, "belonging_query"),
        (re.compile(r'\b(their|which)\s+org(ani[sz]ation)?\b', re.I), 0.97, "org_affiliation"),
        
        # 0.95 confidence - clear analytics
        (re.compile(r'\b(who|which\s+user)\s+(uploaded?|has|created?)', re.I), 0.95, "who_query"),
        (re.compile(r'\b(most|highest|largest|biggest|top\s*\d*)\s+(files?|storage|uploads?)', re.I), 0.95, "ranking"),
        (re.compile(r'\b(between|from|since|until|before|after)\s+\w+\s+\d{4}', re.I), 0.95, "date_range"),
        (re.compile(r'\b(in|during)\s+(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{4}', re.I), 0.95, "date_filter"),
        (re.compile(r'\b(less|fewer|more|greater|under|over)\s+than\s+\d+\s+(files?|uploads?|documents?)', re.I), 0.95, "count_filter"),
        (re.compile(r'\b(uploaded?|has|have)\s+(less|fewer|more|under|over)\s+than\s+\d+', re.I), 0.95, "upload_count_filter"),
        
        # 0.93 confidence - user data queries with conditions
        (re.compile(r'\busers?\b.*(with|where|who|that|and)\b.*(upload|file|storage|approved|register|active)', re.I), 0.93, "user_conditional"),
        (re.compile(r'\b(approved|registered|active|pending)\s+(users?|people)\b', re.I), 0.93, "user_status_query"),
        
        # 0.90 confidence - likely analytics
        (re.compile(r'\b(storage|usage|quota)\s+(per|by|for)\s+(user|org)', re.I), 0.90, "storage_query"),
        (re.compile(r'\b(compare|comparison|versus|vs)\b', re.I), 0.90, "comparison"),
        (re.compile(r'\bper\s+(user|organization|org|day|week|month)\b', re.I), 0.90, "grouped"),
    ]
    
    # Help patterns
    HELP_PATTERNS: List[Tuple[re.Pattern, float, str]] = [
        (re.compile(r'^(help|how\s+do\s+i|what\s+can\s+you\s+do|commands?|features?)\b', re.I), 0.95, "help"),
        (re.compile(r'\b(tutorial|guide|documentation|docs)\b', re.I), 0.90, "docs"),
    ]
    
    # Greeting patterns
    GREETING_PATTERNS: List[Tuple[re.Pattern, float, str]] = [
        (re.compile(r'^(hi|hello|hey|greetings|good\s+(morning|afternoon|evening))(\s+there)?[!.]?$', re.I), 0.99, "greeting"),
        (re.compile(r'^(bye|goodbye|see\s+you|thanks?|thank\s+you)[!.]?$', re.I), 0.99, "farewell"),
    ]
    
    @classmethod
    def match_all(cls, query: str) -> Dict[RouteType, Tuple[float, str]]:
        """
        Match query against all patterns and return confidence scores.
        Returns dict of {RouteType: (confidence, sub_type)}
        """
        scores = {}
        
        # Check navigation
        for pattern, confidence, sub_type in cls.NAVIGATION_PATTERNS:
            if pattern.search(query):
                if RouteType.NAVIGATION not in scores or scores[RouteType.NAVIGATION][0] < confidence:
                    scores[RouteType.NAVIGATION] = (confidence, sub_type)
        
        # Check SQL
        for pattern, confidence, sub_type in cls.SQL_PATTERNS:
            if pattern.search(query):
                if RouteType.SQL_QUERY not in scores or scores[RouteType.SQL_QUERY][0] < confidence:
                    scores[RouteType.SQL_QUERY] = (confidence, sub_type)
        
        # Check help
        for pattern, confidence, sub_type in cls.HELP_PATTERNS:
            if pattern.search(query):
                if RouteType.HELP not in scores or scores[RouteType.HELP][0] < confidence:
                    scores[RouteType.HELP] = (confidence, sub_type)
        
        # Check greetings
        for pattern, confidence, sub_type in cls.GREETING_PATTERNS:
            if pattern.search(query):
                if RouteType.GREETING not in scores or scores[RouteType.GREETING][0] < confidence:
                    scores[RouteType.GREETING] = (confidence, sub_type)
        
        return scores


# ============================================================================
# EMBEDDING CLASSIFIER - Level 2 (MEDIUM)
# ============================================================================

class EmbeddingClassifier:
    """
    Semantic classification using embeddings.
    Understands meaning, not just keywords.
    """
    
    # Example queries for each route type (for similarity matching)
    ROUTE_EXAMPLES = {
        RouteType.NAVIGATION: [
            "go to my files",
            "show me the files page",
            "navigate to documents",
            "take me to settings",
            "open the dashboard",
            "where can I see my uploads",
            "I want to go to the quarantine section",
        ],
        RouteType.SQL_QUERY: [
            "how many files do we have",
            "who uploaded the most files",
            "show me total storage per user",
            "list users who never logged in",
            "count files uploaded in december",
            "average file size by organization",
            "which user has the largest storage",
            "compare uploads between months",
            "give me users who uploaded less than 5 files",
            "show me people with more than 10 uploads",
            "users registered and approved with less than five files",
            "which organization do they belong to",
            "tell me users with upload count under 5",
            "find users who have uploaded fewer than 5 documents",
            "people who uploaded less than five files and their organization",
            "approved users with file count below 5",
            "give me all users and their organization",
            "users with their organization info",
        ],
        RouteType.HELP: [
            "help me",
            "what can you do",
            "how do I upload files",
            "show me the commands",
            "I need assistance",
        ],
        RouteType.GREETING: [
            "hello",
            "hi there",
            "good morning",
            "bye",
            "thanks",
        ],
        RouteType.FILE_OPERATION: [
            "upload a file",
            "download my document",
            "delete this file",
            "rename the file",
            "move file to folder",
        ],
        RouteType.USER_MANAGEMENT: [
            "create a new user",
            "approve pending users",
            "change user role",
            "delete user account",
            "invite someone",
        ],
    }
    
    # Confidence threshold - lower means more queries go to GPT-4o fallback
    CONFIDENCE_THRESHOLD = 0.70  # Lowered from default for better accuracy
    
    def __init__(self):
        self.model = None
        self.embeddings_cache = {}
        self._initialized = False
    
    async def initialize(self):
        """Lazy load the embedding model."""
        if self._initialized:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Pre-compute embeddings for examples
            for route_type, examples in self.ROUTE_EXAMPLES.items():
                self.embeddings_cache[route_type] = self.model.encode(examples)
            
            self._initialized = True
            logger.info("✅ Embedding classifier initialized")
        except ImportError:
            logger.warning("sentence-transformers not available, embedding classification disabled")
    
    async def classify(self, query: str) -> Dict[RouteType, float]:
        """
        Classify query using semantic similarity.
        Returns confidence scores for each route type.
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.model:
            return {}
        
        import numpy as np
        
        # Embed the query
        query_embedding = self.model.encode([query])[0]
        
        scores = {}
        for route_type, example_embeddings in self.embeddings_cache.items():
            # Cosine similarity with each example
            similarities = np.dot(example_embeddings, query_embedding) / (
                np.linalg.norm(example_embeddings, axis=1) * np.linalg.norm(query_embedding)
            )
            # Use max similarity as confidence
            scores[route_type] = float(np.max(similarities))
        
        return scores


# ============================================================================
# GPT-4o ROUTER - Level 3 (SLOW BUT ACCURATE)
# ============================================================================

class GPT4oRouter:
    """
    Intelligent routing using GPT-4o with reasoning.
    Only used for ambiguous queries where Level 1 & 2 are uncertain.
    """
    
    SYSTEM_PROMPT = """You are an intelligent query router for a file management system.

Your job is to classify user queries into one of these categories:
1. NAVIGATION - User wants to go to a page (files, settings, dashboard, quarantine)
2. SQL_QUERY - User wants data/analytics (counts, lists, comparisons, aggregations)
3. HELP - User wants help or documentation
4. GREETING - User is saying hello/goodbye
5. FILE_OPERATION - User wants to perform an action on files (upload, download, delete)
6. USER_MANAGEMENT - User wants to manage users (create, approve, delete)
7. COMPOUND - Query contains MULTIPLE distinct intents (decompose into sub-queries)
8. UNKNOWN - Cannot determine intent

CRITICAL RULES:
- "where can I see my files" → NAVIGATION (going to view files page)
- "how many files do I have" → SQL_QUERY (counting files)
- "show me files larger than 1MB" → SQL_QUERY (filtering files with criteria)
- "my files" → NAVIGATION (just viewing the page)
- "files uploaded by john in december" → SQL_QUERY (filtered data request)

For COMPOUND queries, break them into sub-queries.
Example: "show me my files and tell me how many I have"
→ Sub-queries: ["show me my files", "how many files do I have"]

Respond in JSON format:
{
    "route": "NAVIGATION|SQL_QUERY|HELP|GREETING|FILE_OPERATION|USER_MANAGEMENT|COMPOUND|UNKNOWN",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation",
    "sub_queries": ["list", "of", "sub-queries"] // Only for COMPOUND
}"""

    def __init__(self):
        self.client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize OpenAI client."""
        if self._initialized:
            return
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found, GPT-4o routing disabled")
            return
        
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(api_key=api_key)
            self._initialized = True
            logger.info("✅ GPT-4o router initialized")
        except ImportError:
            logger.warning("openai package not available")
    
    async def route(self, query: str, context: Optional[Dict] = None) -> RouteDecision:
        """
        Use GPT-4o to intelligently route the query.
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.client:
            return RouteDecision(
                route=RouteType.UNKNOWN,
                confidence=0.0,
                reasoning="GPT-4o not available",
                method="gpt4o_unavailable"
            )
        
        import time
        start = time.time()
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": f"Classify this query: \"{query}\""}
                ],
                temperature=0,
                max_tokens=300,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            latency = (time.time() - start) * 1000
            
            route_str = result.get("route", "UNKNOWN").upper()
            route_type = RouteType[route_str] if route_str in RouteType.__members__ else RouteType.UNKNOWN
            
            return RouteDecision(
                route=route_type,
                confidence=result.get("confidence", 0.5),
                reasoning=result.get("reasoning", ""),
                sub_queries=result.get("sub_queries", []),
                latency_ms=latency,
                method="gpt4o"
            )
            
        except Exception as e:
            logger.error(f"GPT-4o routing error: {e}")
            return RouteDecision(
                route=RouteType.UNKNOWN,
                confidence=0.0,
                reasoning=f"Error: {str(e)}",
                method="gpt4o_error"
            )


# ============================================================================
# QUERY MEMORY - Learn from past interactions
# ============================================================================

class QueryMemoryStore:
    """
    Remembers past queries and their outcomes.
    Enables fast retrieval of repeated/similar queries.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.memories: Dict[str, QueryMemory] = {}
        self.query_to_hash: Dict[str, str] = {}
    
    def _hash_query(self, query: str) -> str:
        """Create a hash for normalized query."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def remember(self, query: str, route: RouteType, success: bool, quality: float = 1.0):
        """Store a query and its outcome."""
        query_hash = self._hash_query(query)
        
        memory = QueryMemory(
            query_hash=query_hash,
            query=query,
            route=route,
            success=success,
            timestamp=datetime.now(),
            response_quality=quality
        )
        
        self.memories[query_hash] = memory
        self.query_to_hash[query.lower().strip()] = query_hash
        
        # Evict old memories if over capacity
        if len(self.memories) > self.max_size:
            oldest = min(self.memories.values(), key=lambda m: m.timestamp)
            del self.memories[oldest.query_hash]
    
    def recall(self, query: str) -> Optional[QueryMemory]:
        """Try to recall a past query."""
        query_hash = self._hash_query(query)
        return self.memories.get(query_hash)
    
    def get_success_rate(self, route: RouteType) -> float:
        """Get success rate for a route type."""
        route_memories = [m for m in self.memories.values() if m.route == route]
        if not route_memories:
            return 0.5  # No data
        return sum(m.success for m in route_memories) / len(route_memories)


# ============================================================================
# INTELLIGENT ROUTER - Main orchestrator
# ============================================================================

class IntelligentRouter:
    """
    Multi-level intelligent router with confidence scoring.
    
    Level 1: Fast regex patterns (< 10ms) - Only for HIGH confidence
    Level 2: Embedding classification (< 100ms) - For medium confidence
    Level 3: GPT-4o routing (< 3s) - For low confidence / ambiguous
    
    Plus:
    - Memory for repeated queries (instant)
    - Self-reflection loop for quality improvement
    """
    
    # Confidence thresholds
    HIGH_CONFIDENCE = 0.90   # Use Level 1 decision
    MEDIUM_CONFIDENCE = 0.75  # Use Level 2 decision
    
    def __init__(self):
        self.embedding_classifier = EmbeddingClassifier()
        self.gpt4o_router = GPT4oRouter()
        self.memory = QueryMemoryStore()
        self._initialized = False
    
    async def initialize(self):
        """Initialize all components."""
        if self._initialized:
            return
        
        await asyncio.gather(
            self.embedding_classifier.initialize(),
            self.gpt4o_router.initialize()
        )
        self._initialized = True
        logger.info("✅ Intelligent Router initialized")
    
    async def route(self, query: str, user_context: Optional[Dict] = None) -> RouteDecision:
        """
        Route a query through the multi-level system.
        
        Returns the first high-confidence decision.
        """
        import time
        total_start = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        # ===== LEVEL 0: Memory Check (Instant) =====
        memory = self.memory.recall(query)
        if memory and memory.success and memory.response_quality > 0.8:
            logger.info(f"🧠 Memory hit: {query[:50]}... → {memory.route.value}")
            return RouteDecision(
                route=memory.route,
                confidence=memory.response_quality,
                reasoning=f"Cached from previous successful interaction",
                latency_ms=(time.time() - total_start) * 1000,
                method="memory"
            )
        
        # ===== LEVEL 1: Fast Regex Patterns (< 10ms) =====
        level1_start = time.time()
        pattern_scores = ConfidencePatterns.match_all(query)
        level1_time = (time.time() - level1_start) * 1000
        
        if pattern_scores:
            best_route = max(pattern_scores, key=lambda r: pattern_scores[r][0])
            best_confidence, best_subtype = pattern_scores[best_route]
            
            if best_confidence >= self.HIGH_CONFIDENCE:
                logger.info(f"⚡ Level 1 (regex): {query[:50]}... → {best_route.value} ({best_confidence:.0%})")
                return RouteDecision(
                    route=best_route,
                    confidence=best_confidence,
                    reasoning=f"High-confidence pattern match: {best_subtype}",
                    metadata={"pattern_type": best_subtype},
                    latency_ms=level1_time,
                    method="regex"
                )
        
        # ===== LEVEL 2: Embedding Classification (< 100ms) =====
        level2_start = time.time()
        embedding_scores = await self.embedding_classifier.classify(query)
        level2_time = (time.time() - level2_start) * 1000
        
        if embedding_scores:
            best_route = max(embedding_scores, key=embedding_scores.get)
            best_confidence = embedding_scores[best_route]
            
            # Combine with pattern scores if available
            if best_route in pattern_scores:
                pattern_conf = pattern_scores[best_route][0]
                # Weighted average
                best_confidence = 0.4 * pattern_conf + 0.6 * best_confidence
            
            if best_confidence >= self.MEDIUM_CONFIDENCE:
                logger.info(f"🎯 Level 2 (embedding): {query[:50]}... → {best_route.value} ({best_confidence:.0%})")
                return RouteDecision(
                    route=best_route,
                    confidence=best_confidence,
                    reasoning=f"Semantic similarity match",
                    metadata={"embedding_scores": {k.value: v for k, v in embedding_scores.items()}},
                    latency_ms=level1_time + level2_time,
                    method="embedding"
                )
        
        # ===== LEVEL 3: GPT-4o Intelligent Routing (< 3s) =====
        logger.info(f"🧠 Level 3 (GPT-4o): {query[:50]}... (ambiguous query)")
        decision = await self.gpt4o_router.route(query, user_context)
        decision.latency_ms = (time.time() - total_start) * 1000
        
        return decision
    
    def learn(self, query: str, route: RouteType, success: bool, quality: float = 1.0):
        """Learn from an interaction outcome."""
        self.memory.remember(query, route, success, quality)
    
    async def route_with_reflection(self, query: str, user_context: Optional[Dict] = None) -> RouteDecision:
        """
        Route with self-reflection loop.
        
        If the initial decision has low confidence, ask GPT-4o to verify.
        """
        decision = await self.route(query, user_context)
        
        # Self-reflection for medium-confidence decisions
        if 0.5 < decision.confidence < 0.85 and decision.method != "gpt4o":
            logger.info(f"🔄 Self-reflection: Verifying {decision.route.value} ({decision.confidence:.0%})")
            
            gpt4o_decision = await self.gpt4o_router.route(query, user_context)
            
            if gpt4o_decision.route != decision.route and gpt4o_decision.confidence > decision.confidence:
                logger.info(f"🔄 Corrected: {decision.route.value} → {gpt4o_decision.route.value}")
                return gpt4o_decision
        
        return decision


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_router_instance: Optional[IntelligentRouter] = None

def get_intelligent_router() -> IntelligentRouter:
    """Get or create the intelligent router singleton."""
    global _router_instance
    if _router_instance is None:
        _router_instance = IntelligentRouter()
    return _router_instance


async def intelligent_route(query: str, user_context: Optional[Dict] = None) -> RouteDecision:
    """Convenience function for routing a query."""
    router = get_intelligent_router()
    return await router.route(query, user_context)


# ============================================================================
# TEST / DEMO
# ============================================================================

async def demo():
    """Demo the intelligent router."""
    router = IntelligentRouter()
    await router.initialize()
    
    test_queries = [
        # Clear navigation
        "go to my files",
        "where can I see my documents",
        
        # Clear SQL
        "how many files do we have",
        "who uploaded the most files in december 2025",
        "show me users with more than 5 files",
        
        # Ambiguous (need GPT-4o)
        "files",
        "show me files",
        "users",
        
        # Compound
        "go to my files and tell me how many I have",
        
        # Typos
        "howmany usrs do we have",
        "gimme all da files",
    ]
    
    print("=" * 70)
    print("INTELLIGENT ROUTER DEMO")
    print("=" * 70)
    
    for query in test_queries:
        decision = await router.route(query)
        print(f"\nQ: {query}")
        print(f"   Route: {decision.route.value}")
        print(f"   Confidence: {decision.confidence:.0%}")
        print(f"   Method: {decision.method}")
        print(f"   Latency: {decision.latency_ms:.0f}ms")
        print(f"   Reasoning: {decision.reasoning[:60]}...")


if __name__ == "__main__":
    import asyncio
    asyncio.run(demo())
