"""
Typo Corrector - Fuzzy Matching for User Queries
=================================================
Fixes common misspellings using difflib's SequenceMatcher.

This is a lightweight solution (~1ms overhead) that:
1. Identifies misspelled words
2. Suggests corrections from a known vocabulary
3. Returns corrected query for better intent matching

Target: Fix queries like "usrs" → "users", "fiels" → "files"
"""

import logging
import re
from difflib import get_close_matches, SequenceMatcher
from typing import List, Tuple, Optional, Dict, Set

logger = logging.getLogger(__name__)


# =============================================================================
# KNOWN VOCABULARY - Words the system understands
# =============================================================================

# Core entities
ENTITY_WORDS = {
    # Users
    'user', 'users', 'member', 'members', 'account', 'accounts', 
    'people', 'person', 'admin', 'admins', 'administrator',
    'manager', 'managers', 'approver', 'approvers', 'uploader', 'uploaders',
    
    # Files
    'file', 'files', 'document', 'documents', 'doc', 'docs',
    'upload', 'uploads', 'item', 'items', 'record', 'records',
    'pdf', 'image', 'images', 'video', 'videos',
    
    # Storage
    'storage', 'space', 'disk', 'size', 'bytes', 'megabytes', 'gigabytes',
    'mb', 'gb', 'kb',
    
    # Organizations
    'organization', 'organizations', 'org', 'orgs', 'company', 'companies',
    'tenant', 'tenants', 'team', 'teams',
    
    # Folders
    'folder', 'folders', 'directory', 'directories',
    
    # Status
    'status', 'active', 'inactive', 'pending', 'approved', 'rejected',
    'verified', 'unverified', 'quarantined', 'clean', 'infected',
    
    # Roles
    'role', 'roles', 'super', 'regular', 'viewer',
}

# Actions/Verbs
ACTION_WORDS = {
    'show', 'list', 'get', 'find', 'search', 'count', 'total',
    'display', 'view', 'give', 'fetch', 'retrieve',
    'upload', 'uploaded', 'download', 'downloaded', 
    'create', 'created', 'delete', 'deleted', 'remove', 'removed',
    'approve', 'approved', 'reject', 'rejected', 'pending',
    'join', 'joined', 'register', 'registered', 'login', 'logged',
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
}

# Navigation words - should NOT be corrected
NAVIGATION_WORDS = {
    'check', 'can', 'see', 'go', 'take', 'navigate', 'open', 'logs', 'log',
    'application', 'system', 'dashboard', 'page', 'settings', 'home',
    'help', 'about', 'profile', 'notifications', 'quarantine', 'analytics',
}

# Common English words that should NOT be corrected
COMMON_ENGLISH = {
    # Verbs
    'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'done',
    'can', 'could', 'will', 'would', 'shall', 'should', 'may', 'might', 'must',
    'need', 'want', 'like', 'know', 'think', 'see', 'make', 'take', 'go', 'get',
    # Prepositions
    'to', 'for', 'in', 'on', 'at', 'by', 'with', 'from', 'of', 'about',
    # Articles/Pronouns
    'the', 'this', 'that', 'these', 'those', 'it', 'its',
    'my', 'your', 'our', 'their', 'his', 'her',
    'me', 'you', 'us', 'them', 'him', 'her',
    # Other
    'and', 'or', 'but', 'so', 'if', 'then', 'else',
    'please', 'thanks', 'thank', 'hello', 'hi', 'hey',
}

# Combine all vocabularies
ALL_KNOWN_WORDS: Set[str] = (
    ENTITY_WORDS | 
    ACTION_WORDS | 
    DESCRIPTOR_WORDS | 
    TIME_WORDS | 
    QUESTION_WORDS |
    INFRA_WORDS |
    NAVIGATION_WORDS |
    COMMON_ENGLISH
)

# Common typo patterns (explicit mappings for very common typos)
EXPLICIT_CORRECTIONS = {
    'usrs': 'users',
    'usr': 'user',
    'usres': 'users',
    'fiels': 'files',
    'fiel': 'file',
    'filles': 'files',
    'fils': 'files',
    'documets': 'documents',
    'documnet': 'document',
    'docuemnts': 'documents',
    'organizaton': 'organization',
    'organizatons': 'organizations',
    'organisaton': 'organization',
    'organziation': 'organization',
    'stoarge': 'storage',
    'storge': 'storage',
    'stroage': 'storage',
    'uplaod': 'upload',
    'uplaoded': 'uploaded',
    'uplad': 'upload',
    'donwload': 'download',
    'downlod': 'download',
    'pendng': 'pending',
    'pendig': 'pending',
    'aprroved': 'approved',
    'aproved': 'approved',
    'approvd': 'approved',
    'rejectd': 'rejected',
    'rejcted': 'rejected',
    'admn': 'admin',
    'admins': 'admins',
    'floder': 'folder',
    'floders': 'folders',
    'fodler': 'folder',
    'qurantined': 'quarantined',
    'quarentined': 'quarantined',
    'viurs': 'virus',
    'scna': 'scan',
    'serach': 'search',
    'searhc': 'search',
    'contianer': 'container',
    'contianers': 'containers',
    'sevice': 'service',
    'sevices': 'services',
    'runing': 'running',
    'runnnig': 'running',
    'statsu': 'status',
    'staus': 'status',
    'memebers': 'members',
    'memebrs': 'members',
    'mamber': 'member',
}


# =============================================================================
# TYPO CORRECTOR CLASS
# =============================================================================

class TypoCorrector:
    """
    Fuzzy matching typo corrector.
    
    Uses a combination of:
    1. Explicit correction mappings (for known typos)
    2. Fuzzy matching via difflib (for unknown typos)
    """
    
    def __init__(
        self, 
        vocabulary: Set[str] = None,
        explicit_corrections: Dict[str, str] = None,
        min_similarity: float = 0.75,  # Minimum similarity for fuzzy match
        min_word_length: int = 3,  # Only correct words >= this length
    ):
        self.vocabulary = vocabulary or ALL_KNOWN_WORDS
        self.explicit_corrections = explicit_corrections or EXPLICIT_CORRECTIONS
        self.min_similarity = min_similarity
        self.min_word_length = min_word_length
        
        # Build lowercase vocabulary for matching
        self._vocab_lower = {w.lower() for w in self.vocabulary}
        self._explicit_lower = {k.lower(): v.lower() for k, v in self.explicit_corrections.items()}
        
        logger.info(f"TypoCorrector initialized with {len(self._vocab_lower)} vocabulary words")
    
    def correct_word(self, word: str) -> Tuple[str, bool, float]:
        """
        Correct a single word.
        
        Returns:
            Tuple of (corrected_word, was_corrected, confidence)
        """
        word_lower = word.lower()
        
        # Skip short words
        if len(word_lower) < self.min_word_length:
            return word, False, 1.0
        
        # Skip if word is already known
        if word_lower in self._vocab_lower:
            return word, False, 1.0
        
        # Check explicit corrections first
        if word_lower in self._explicit_lower:
            corrected = self._explicit_lower[word_lower]
            # Preserve original casing style
            if word.isupper():
                corrected = corrected.upper()
            elif word[0].isupper():
                corrected = corrected.capitalize()
            logger.debug(f"Explicit correction: '{word}' → '{corrected}'")
            return corrected, True, 0.95
        
        # Try fuzzy matching
        matches = get_close_matches(
            word_lower, 
            self._vocab_lower, 
            n=1, 
            cutoff=self.min_similarity
        )
        
        if matches:
            corrected = matches[0]
            similarity = SequenceMatcher(None, word_lower, corrected).ratio()
            
            # Preserve original casing style
            if word.isupper():
                corrected = corrected.upper()
            elif word[0].isupper():
                corrected = corrected.capitalize()
            
            logger.debug(f"Fuzzy correction: '{word}' → '{corrected}' (similarity: {similarity:.2f})")
            return corrected, True, similarity
        
        # No correction found
        return word, False, 1.0
    
    def correct_query(self, query: str) -> Tuple[str, List[Dict], bool]:
        """
        Correct all words in a query.
        
        Returns:
            Tuple of (corrected_query, corrections_made, any_corrections)
        """
        # Split into words, preserving punctuation
        words = re.findall(r'\b\w+\b|\S', query)
        
        corrected_words = []
        corrections = []
        any_corrected = False
        
        for word in words:
            # Skip non-alphanumeric
            if not word.isalnum():
                corrected_words.append(word)
                continue
            
            corrected, was_corrected, confidence = self.correct_word(word)
            corrected_words.append(corrected)
            
            if was_corrected:
                any_corrected = True
                corrections.append({
                    'original': word,
                    'corrected': corrected,
                    'confidence': confidence
                })
        
        # Reconstruct query
        corrected_query = ' '.join(corrected_words)
        # Clean up spacing around punctuation
        corrected_query = re.sub(r'\s+([?.!,])', r'\1', corrected_query)
        
        if any_corrected:
            logger.info(f"Query corrected: '{query}' → '{corrected_query}'")
            logger.debug(f"Corrections: {corrections}")
        
        return corrected_query, corrections, any_corrected
    
    def add_to_vocabulary(self, words: List[str]):
        """Add new words to the vocabulary."""
        for word in words:
            self._vocab_lower.add(word.lower())
        logger.info(f"Added {len(words)} words to vocabulary")
    
    def add_explicit_correction(self, typo: str, correction: str):
        """Add an explicit typo → correction mapping."""
        self._explicit_lower[typo.lower()] = correction.lower()
        logger.info(f"Added explicit correction: '{typo}' → '{correction}'")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_typo_corrector: Optional[TypoCorrector] = None


def get_typo_corrector() -> TypoCorrector:
    """Get or create the singleton TypoCorrector instance."""
    global _typo_corrector
    if _typo_corrector is None:
        _typo_corrector = TypoCorrector()
    return _typo_corrector


def correct_query(query: str) -> Tuple[str, bool]:
    """
    Convenience function to correct a query.
    
    Returns:
        Tuple of (corrected_query, was_corrected)
    """
    corrector = get_typo_corrector()
    corrected, corrections, any_corrected = corrector.correct_query(query)
    return corrected, any_corrected


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    # Test the corrector
    corrector = TypoCorrector()
    
    test_queries = [
        "how many usrs are there",
        "show me all the fiels",
        "organizatons with most users",
        "stoarge used by each user",
        "who uplaoded the most files",
        "pendng users list",
        "aprroved users",
        "show me runing services",
        "contianer status",
        "list all documets",
    ]
    
    print("=" * 60)
    print("TYPO CORRECTOR TEST")
    print("=" * 60)
    
    for query in test_queries:
        corrected, corrections, any_corrected = corrector.correct_query(query)
        status = "✅ CORRECTED" if any_corrected else "➖ NO CHANGE"
        print(f"\n{status}")
        print(f"  Original:  {query}")
        print(f"  Corrected: {corrected}")
        if corrections:
            for c in corrections:
                print(f"    • '{c['original']}' → '{c['corrected']}' ({c['confidence']:.0%})")
