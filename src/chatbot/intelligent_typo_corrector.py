"""
Intelligent Typo Corrector - AI-Powered Query Correction
=========================================================
Uses a hybrid approach combining:
1. Fast vocabulary matching (~0ms) for known words
2. AI-powered contextual correction for ambiguous cases
3. Self-learning from user feedback

This provides intelligent, context-aware corrections while maintaining speed.
"""

import logging
import re
import asyncio
import json
from typing import List, Tuple, Optional, Dict, Set, Any
from dataclasses import dataclass, field
from datetime import datetime
from difflib import get_close_matches, SequenceMatcher

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class TypoCorrectorConfig:
    """Configuration for the intelligent typo corrector."""
    # Fast matching settings
    min_similarity: float = 0.8  # Higher threshold = fewer false positives
    min_word_length: int = 3
    
    # AI settings
    use_ai_fallback: bool = True
    ai_confidence_threshold: float = 0.6  # When to use AI
    ai_timeout: float = 2.0  # Max time for AI correction
    
    # Learning settings
    enable_learning: bool = True
    max_learned_corrections: int = 1000
    
    # Performance
    cache_corrections: bool = True
    max_cache_size: int = 500


# =============================================================================
# DOMAIN VOCABULARY - File Management System
# =============================================================================

# Core entities
ENTITY_WORDS = {
    'user', 'users', 'member', 'members', 'account', 'accounts',
    'people', 'person', 'admin', 'admins', 'administrator',
    'manager', 'managers', 'approver', 'approvers', 'uploader', 'uploaders',
    'file', 'files', 'document', 'documents', 'doc', 'docs',
    'upload', 'uploads', 'item', 'items', 'record', 'records',
    'pdf', 'image', 'images', 'video', 'videos',
    'storage', 'space', 'disk', 'size', 'bytes', 'megabytes', 'gigabytes',
    'mb', 'gb', 'kb',
    'organization', 'organizations', 'org', 'orgs', 'company', 'companies',
    'tenant', 'tenants', 'team', 'teams',
    'folder', 'folders', 'directory', 'directories',
    'status', 'active', 'inactive', 'pending', 'approved', 'rejected',
    'verified', 'unverified', 'quarantined', 'clean', 'infected',
    'role', 'roles', 'super', 'regular', 'viewer',
    'appointment', 'appointments', 'schedule', 'scheduled',
}

# Actions/Verbs
ACTION_WORDS = {
    'show', 'list', 'get', 'find', 'search', 'count', 'total',
    'display', 'view', 'give', 'fetch', 'retrieve', 'check',
    'upload', 'uploaded', 'download', 'downloaded',
    'create', 'created', 'delete', 'deleted', 'remove', 'removed',
    'approve', 'approved', 'reject', 'rejected',
    'join', 'joined', 'register', 'registered', 'login', 'logged',
    'navigate', 'go', 'take', 'open', 'close', 'start', 'stop',
}

# Descriptors
DESCRIPTOR_WORDS = {
    'many', 'much', 'all', 'every', 'each', 'some', 'any',
    'most', 'least', 'top', 'bottom', 'first', 'last',
    'largest', 'biggest', 'smallest', 'newest', 'oldest', 'recent', 'latest',
    'total', 'average', 'avg', 'maximum', 'minimum', 'max', 'min',
}

# Time-related
TIME_WORDS = {
    'today', 'yesterday', 'week', 'month', 'year', 'day', 'days',
    'weeks', 'months', 'years', 'recent', 'recently', 'latest',
    'last', 'past', 'previous', 'current', 'this',
    'before', 'after', 'since', 'between', 'during',
}

# Question words
QUESTION_WORDS = {
    'how', 'what', 'who', 'which', 'where', 'when', 'why',
    'whose', 'whom',
}

# Infrastructure
INFRA_WORDS = {
    'container', 'containers', 'docker', 'service', 'services',
    'database', 'mysql', 'redis', 'minio', 'rabbitmq',
    'health', 'status', 'running', 'stopped', 'restart',
    'log', 'logs', 'system', 'application', 'error', 'errors',
}

# Navigation
NAVIGATION_WORDS = {
    'dashboard', 'page', 'settings', 'home', 'profile',
    'notifications', 'quarantine', 'analytics', 'reports',
    'help', 'about', 'menu', 'sidebar', 'navigation',
}

# Common English (should never be "corrected")
COMMON_ENGLISH = {
    # Pronouns
    'i', 'me', 'my', 'mine', 'you', 'your', 'yours',
    'he', 'him', 'his', 'she', 'her', 'hers',
    'it', 'its', 'we', 'us', 'our', 'ours',
    'they', 'them', 'their', 'theirs',
    'this', 'that', 'these', 'those',
    # Verbs
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'done',
    'can', 'could', 'will', 'would', 'shall', 'should',
    'may', 'might', 'must', 'need', 'want', 'like',
    'know', 'think', 'see', 'make', 'take', 'go', 'get',
    # Prepositions
    'to', 'for', 'in', 'on', 'at', 'by', 'with', 'from',
    'of', 'about', 'into', 'through', 'during', 'before',
    'after', 'above', 'below', 'between', 'under', 'over',
    # Conjunctions
    'and', 'or', 'but', 'so', 'if', 'then', 'else',
    'because', 'although', 'while', 'when', 'where',
    # Articles
    'a', 'an', 'the',
    # Other common
    'not', 'no', 'yes', 'ok', 'okay',
    'please', 'thanks', 'thank', 'hello', 'hi', 'hey',
    'just', 'only', 'also', 'too', 'very', 'really',
}

# Combine all domain vocabulary
DOMAIN_VOCABULARY: Set[str] = (
    ENTITY_WORDS |
    ACTION_WORDS |
    DESCRIPTOR_WORDS |
    TIME_WORDS |
    QUESTION_WORDS |
    INFRA_WORDS |
    NAVIGATION_WORDS |
    COMMON_ENGLISH
)

# Common typo patterns (explicit mappings)
EXPLICIT_CORRECTIONS = {
    # User typos
    'usrs': 'users', 'usr': 'user', 'usres': 'users',
    # File typos
    'fiels': 'files', 'fiel': 'file', 'filles': 'files', 'fils': 'files',
    # Document typos
    'documets': 'documents', 'documnet': 'document', 'docuemnts': 'documents',
    # Organization typos
    'organizaton': 'organization', 'organizatons': 'organizations',
    'organisaton': 'organization', 'organziation': 'organization',
    # Storage typos
    'stoarge': 'storage', 'storge': 'storage', 'stroage': 'storage',
    # Upload/Download typos
    'uplaod': 'upload', 'uplaoded': 'uploaded', 'uplad': 'upload',
    'donwload': 'download', 'downlod': 'download',
    # Status typos
    'pendng': 'pending', 'pendig': 'pending',
    'aprroved': 'approved', 'aproved': 'approved', 'approvd': 'approved',
    'rejectd': 'rejected', 'rejcted': 'rejected',
    # Other common typos
    'admn': 'admin', 'floder': 'folder', 'floders': 'folders',
    'fodler': 'folder', 'qurantined': 'quarantined',
    'quarentined': 'quarantined', 'viurs': 'virus',
    'scna': 'scan', 'serach': 'search', 'searhc': 'search',
    'contianer': 'container', 'contianers': 'containers',
    'sevice': 'service', 'sevices': 'services',
    'runing': 'running', 'runnnig': 'running',
    'statsu': 'status', 'staus': 'status',
    'memebers': 'members', 'memebrs': 'members', 'mamber': 'member',
    'appoitment': 'appointment', 'appointmnet': 'appointment',
    'shwo': 'show', 'sohw': 'show',
    'lsit': 'list', 'lits': 'list',
    'hlep': 'help', 'hepl': 'help',
}


# =============================================================================
# CORRECTION RESULT
# =============================================================================

@dataclass
class CorrectionResult:
    """Result of a typo correction attempt."""
    original: str
    corrected: str
    was_corrected: bool
    corrections: List[Dict[str, Any]] = field(default_factory=list)
    method: str = "none"  # "vocabulary", "explicit", "fuzzy", "ai", "none"
    confidence: float = 1.0
    processing_time_ms: float = 0.0


# =============================================================================
# AI CORRECTION AGENT
# =============================================================================

class AITypoCorrectionAgent:
    """
    AI-powered typo correction agent using LangChain.
    
    Only invoked for ambiguous cases where vocabulary matching fails
    but the word looks like it might be a typo.
    """
    
    def __init__(self, config: TypoCorrectorConfig):
        self.config = config
        self._llm = None
        self._initialized = False
    
    def _get_llm(self):
        """Lazy initialization of LLM."""
        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI
                import os
                
                # Try NVIDIA NIM first, then OpenAI
                nvidia_key = os.getenv("NVIDIA_API_KEY")
                openai_key = os.getenv("OPENAI_API_KEY")
                
                if nvidia_key:
                    self._llm = ChatOpenAI(
                        model="meta/llama-3.1-70b-instruct",
                        base_url="https://integrate.api.nvidia.com/v1",
                        api_key=nvidia_key,
                        temperature=0,
                        max_tokens=100,
                    )
                    logger.info("AI Typo Corrector using NVIDIA NIM")
                elif openai_key:
                    self._llm = ChatOpenAI(
                        model="gpt-3.5-turbo",
                        api_key=openai_key,
                        temperature=0,
                        max_tokens=100,
                    )
                    logger.info("AI Typo Corrector using OpenAI")
                else:
                    logger.warning("No AI API key found, AI correction disabled")
                    
                self._initialized = True
            except Exception as e:
                logger.error(f"Failed to initialize AI corrector: {e}")
                self._initialized = True  # Mark as tried
        
        return self._llm
    
    async def correct_query(
        self,
        query: str,
        suspicious_words: List[str],
        context: Optional[str] = None
    ) -> Tuple[str, List[Dict], float]:
        """
        Use AI to correct suspicious words in context.
        
        Args:
            query: The full query
            suspicious_words: Words that might be typos
            context: Optional context about the domain
            
        Returns:
            Tuple of (corrected_query, corrections_made, confidence)
        """
        llm = self._get_llm()
        if llm is None:
            return query, [], 0.0
        
        try:
            prompt = f"""You are a typo correction assistant for a file management system.

Given the query: "{query}"

The following words might be typos: {suspicious_words}

Domain context: This is a file management system with users, files, folders, organizations, appointments, uploads, downloads, virus scanning, quarantine, and system logs.

Instructions:
1. Only correct words that are CLEARLY typos
2. Do NOT change words that are valid English or domain terms
3. Preserve the user's intent
4. Return ONLY the corrected query, nothing else

If no corrections needed, return the original query exactly.

Corrected query:"""

            response = await asyncio.wait_for(
                llm.ainvoke(prompt),
                timeout=self.config.ai_timeout
            )
            
            corrected = response.content.strip().strip('"\'')
            
            # Validate correction
            if not corrected or len(corrected) < 3:
                return query, [], 0.0
            
            # Check if actually changed
            if corrected.lower() == query.lower():
                return query, [], 1.0
            
            # Build corrections list
            corrections = []
            original_words = query.lower().split()
            corrected_words = corrected.lower().split()
            
            for orig, corr in zip(original_words, corrected_words):
                if orig != corr:
                    corrections.append({
                        'original': orig,
                        'corrected': corr,
                        'method': 'ai',
                        'confidence': 0.85
                    })
            
            logger.info(f"AI corrected: '{query}' → '{corrected}'")
            return corrected, corrections, 0.85
            
        except asyncio.TimeoutError:
            logger.warning(f"AI correction timed out for: {query}")
            return query, [], 0.0
        except Exception as e:
            logger.error(f"AI correction failed: {e}")
            return query, [], 0.0


# =============================================================================
# INTELLIGENT TYPO CORRECTOR
# =============================================================================

class IntelligentTypoCorrector:
    """
    Hybrid typo corrector combining fast vocabulary matching with AI fallback.
    
    Processing flow:
    1. Check explicit corrections (fastest, 0ms)
    2. Check vocabulary (fast, ~0.1ms)
    3. Fuzzy matching for close matches (~1ms)
    4. AI fallback for ambiguous cases (~100-500ms, optional)
    """
    
    def __init__(
        self,
        config: Optional[TypoCorrectorConfig] = None,
        vocabulary: Optional[Set[str]] = None,
        explicit_corrections: Optional[Dict[str, str]] = None
    ):
        self.config = config or TypoCorrectorConfig()
        self.vocabulary = vocabulary or DOMAIN_VOCABULARY
        self.explicit_corrections = explicit_corrections or EXPLICIT_CORRECTIONS
        
        # Lowercase versions for matching
        self._vocab_lower = {w.lower() for w in self.vocabulary}
        self._explicit_lower = {k.lower(): v.lower() for k, v in self.explicit_corrections.items()}
        
        # AI agent (lazy initialized)
        self._ai_agent = AITypoCorrectionAgent(self.config) if self.config.use_ai_fallback else None
        
        # Learning storage
        self._learned_corrections: Dict[str, str] = {}
        
        # Cache for repeated queries
        self._cache: Dict[str, CorrectionResult] = {}
        
        logger.info(
            f"IntelligentTypoCorrector initialized: "
            f"{len(self._vocab_lower)} vocabulary words, "
            f"{len(self._explicit_lower)} explicit corrections, "
            f"AI fallback: {self.config.use_ai_fallback}"
        )
    
    def _correct_word_fast(self, word: str) -> Tuple[str, bool, str, float]:
        """
        Fast path: vocabulary and explicit correction check.
        
        Returns: (corrected_word, was_corrected, method, confidence)
        """
        word_lower = word.lower()
        
        # Skip short words
        if len(word_lower) < self.config.min_word_length:
            return word, False, "skip_short", 1.0
        
        # Check if already in vocabulary
        if word_lower in self._vocab_lower:
            return word, False, "vocabulary", 1.0
        
        # Check learned corrections
        if word_lower in self._learned_corrections:
            corrected = self._learned_corrections[word_lower]
            return self._preserve_case(word, corrected), True, "learned", 0.95
        
        # Check explicit corrections
        if word_lower in self._explicit_lower:
            corrected = self._explicit_lower[word_lower]
            return self._preserve_case(word, corrected), True, "explicit", 0.98
        
        return word, False, "unknown", 0.0
    
    def _correct_word_fuzzy(self, word: str) -> Tuple[str, bool, float]:
        """
        Fuzzy matching for unknown words.
        
        Returns: (corrected_word, was_corrected, confidence)
        """
        word_lower = word.lower()
        
        matches = get_close_matches(
            word_lower,
            self._vocab_lower,
            n=1,
            cutoff=self.config.min_similarity
        )
        
        if matches:
            corrected = matches[0]
            similarity = SequenceMatcher(None, word_lower, corrected).ratio()
            return self._preserve_case(word, corrected), True, similarity
        
        return word, False, 0.0
    
    def _preserve_case(self, original: str, corrected: str) -> str:
        """Preserve the original word's casing style."""
        if original.isupper():
            return corrected.upper()
        elif original[0].isupper():
            return corrected.capitalize()
        return corrected
    
    def correct_query_sync(self, query: str) -> CorrectionResult:
        """
        Synchronous query correction (no AI).
        
        Use this for fast, non-blocking correction.
        """
        import time
        start = time.time()
        
        # Check cache
        cache_key = query.lower()
        if self.config.cache_corrections and cache_key in self._cache:
            cached = self._cache[cache_key]
            cached.processing_time_ms = 0.1  # Cache hit
            return cached
        
        words = re.findall(r'\b\w+\b|\S', query)
        corrected_words = []
        corrections = []
        any_corrected = False
        method_used = "none"
        min_confidence = 1.0
        
        for word in words:
            if not word.isalnum():
                corrected_words.append(word)
                continue
            
            # Fast path
            corrected, was_corrected, method, confidence = self._correct_word_fast(word)
            
            if was_corrected:
                corrected_words.append(corrected)
                corrections.append({
                    'original': word,
                    'corrected': corrected,
                    'method': method,
                    'confidence': confidence
                })
                any_corrected = True
                method_used = method
                min_confidence = min(min_confidence, confidence)
            elif method == "unknown" and len(word) >= self.config.min_word_length:
                # Try fuzzy matching for unknown words
                fuzzy_corrected, fuzzy_changed, fuzzy_conf = self._correct_word_fuzzy(word)
                if fuzzy_changed:
                    corrected_words.append(fuzzy_corrected)
                    corrections.append({
                        'original': word,
                        'corrected': fuzzy_corrected,
                        'method': 'fuzzy',
                        'confidence': fuzzy_conf
                    })
                    any_corrected = True
                    method_used = "fuzzy"
                    min_confidence = min(min_confidence, fuzzy_conf)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        # Reconstruct query
        corrected_query = ' '.join(corrected_words)
        corrected_query = re.sub(r'\s+([?.!,])', r'\1', corrected_query)
        
        elapsed = (time.time() - start) * 1000
        
        result = CorrectionResult(
            original=query,
            corrected=corrected_query,
            was_corrected=any_corrected,
            corrections=corrections,
            method=method_used if any_corrected else "none",
            confidence=min_confidence if any_corrected else 1.0,
            processing_time_ms=elapsed
        )
        
        # Cache result
        if self.config.cache_corrections and len(self._cache) < self.config.max_cache_size:
            self._cache[cache_key] = result
        
        if any_corrected:
            logger.info(f"[TYPO] Corrected ({method_used}): '{query}' → '{corrected_query}'")
        
        return result
    
    async def correct_query_async(self, query: str) -> CorrectionResult:
        """
        Asynchronous query correction with AI fallback.
        
        Use this when you need the most accurate corrections.
        """
        import time
        start = time.time()
        
        # First, try sync correction
        sync_result = self.correct_query_sync(query)
        
        # If confident or AI disabled, return sync result
        if not self.config.use_ai_fallback or not self._ai_agent:
            return sync_result
        
        # Check if there are suspicious words that need AI
        suspicious_words = []
        words = re.findall(r'\b\w+\b', query)
        
        for word in words:
            word_lower = word.lower()
            if len(word_lower) >= self.config.min_word_length:
                if word_lower not in self._vocab_lower:
                    if word_lower not in self._explicit_lower:
                        if word_lower not in self._learned_corrections:
                            # This word is unknown - might be a typo
                            suspicious_words.append(word)
        
        # If no suspicious words or sync already corrected well, return
        if not suspicious_words:
            return sync_result
        
        # Use AI for suspicious words
        try:
            ai_corrected, ai_corrections, ai_confidence = await self._ai_agent.correct_query(
                query=sync_result.corrected,  # Use any sync corrections as base
                suspicious_words=suspicious_words
            )
            
            if ai_corrections:
                elapsed = (time.time() - start) * 1000
                
                # Merge corrections
                all_corrections = sync_result.corrections + ai_corrections
                
                result = CorrectionResult(
                    original=query,
                    corrected=ai_corrected,
                    was_corrected=True,
                    corrections=all_corrections,
                    method="ai",
                    confidence=ai_confidence,
                    processing_time_ms=elapsed
                )
                
                # Learn from AI corrections
                if self.config.enable_learning:
                    for corr in ai_corrections:
                        self.learn_correction(corr['original'], corr['corrected'])
                
                return result
                
        except Exception as e:
            logger.warning(f"AI correction failed, using sync result: {e}")
        
        return sync_result
    
    def learn_correction(self, typo: str, correction: str):
        """Learn a new correction from feedback or AI."""
        if len(self._learned_corrections) >= self.config.max_learned_corrections:
            # Remove oldest entry
            if self._learned_corrections:
                oldest_key = next(iter(self._learned_corrections))
                del self._learned_corrections[oldest_key]
        
        self._learned_corrections[typo.lower()] = correction.lower()
        logger.info(f"Learned correction: '{typo}' → '{correction}'")
    
    def add_to_vocabulary(self, words: List[str]):
        """Add new words to the vocabulary."""
        for word in words:
            self._vocab_lower.add(word.lower())
        logger.info(f"Added {len(words)} words to vocabulary")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get corrector statistics."""
        return {
            "vocabulary_size": len(self._vocab_lower),
            "explicit_corrections": len(self._explicit_lower),
            "learned_corrections": len(self._learned_corrections),
            "cache_size": len(self._cache),
            "ai_enabled": self.config.use_ai_fallback and self._ai_agent is not None
        }


# =============================================================================
# SINGLETON AND CONVENIENCE FUNCTIONS
# =============================================================================

_intelligent_corrector: Optional[IntelligentTypoCorrector] = None


def get_intelligent_corrector() -> IntelligentTypoCorrector:
    """Get or create the singleton IntelligentTypoCorrector instance."""
    global _intelligent_corrector
    if _intelligent_corrector is None:
        _intelligent_corrector = IntelligentTypoCorrector()
    return _intelligent_corrector


def correct_query_intelligent(query: str) -> Tuple[str, bool]:
    """
    Fast synchronous correction with intelligent vocabulary.
    
    Returns:
        Tuple of (corrected_query, was_corrected)
    """
    corrector = get_intelligent_corrector()
    result = corrector.correct_query_sync(query)
    return result.corrected, result.was_corrected


async def correct_query_intelligent_async(query: str) -> Tuple[str, bool, List[Dict]]:
    """
    Async correction with AI fallback for ambiguous cases.
    
    Returns:
        Tuple of (corrected_query, was_corrected, corrections)
    """
    corrector = get_intelligent_corrector()
    result = await corrector.correct_query_async(query)
    return result.corrected, result.was_corrected, result.corrections


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    corrector = IntelligentTypoCorrector()
    
    test_queries = [
        "where can i check this application logs",
        "shwo me all usrs",
        "lsit fiels uploaded today",
        "how meny users are ther",
        "whats the stoarge used",
        "take me to qurantined files",
        "show me pending appoitments",
    ]
    
    print("\n" + "="*60)
    print("INTELLIGENT TYPO CORRECTOR TEST")
    print("="*60)
    
    for query in test_queries:
        result = corrector.correct_query_sync(query)
        status = "✓" if result.was_corrected else "○"
        print(f"\n{status} Input:  '{query}'")
        print(f"  Output: '{result.corrected}'")
        if result.corrections:
            print(f"  Method: {result.method}, Confidence: {result.confidence:.2f}")
            for c in result.corrections:
                print(f"    - '{c['original']}' → '{c['corrected']}'")
    
    print("\n" + "="*60)
    print(f"Stats: {corrector.get_stats()}")
