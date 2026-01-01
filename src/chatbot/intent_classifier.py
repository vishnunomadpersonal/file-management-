"""
Intent Classifier - Production-Ready Query Router
==================================================
Fast pattern matching + semantic classification to route
user queries to the correct analytics tool.

Response time: ~1-5ms (no LLM needed)
"""

import re
import logging
from typing import Optional, List, Tuple, Dict, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class QueryCategory(Enum):
    """Categories of user queries."""
    COUNT = "count"
    LIST = "list"
    STATS = "stats"
    TREND = "trend"
    MY_DATA = "my_data"
    COMPARISON = "comparison"
    SEARCH = "search"
    UNKNOWN = "unknown"


class Entity(Enum):
    """Entities that can be queried."""
    USER = "user"
    FILE = "file"
    FOLDER = "folder"
    ORGANIZATION = "organization"
    STORAGE = "storage"
    UPLOAD = "upload"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedIntent:
    """Result of intent classification."""
    tool_name: str
    confidence: float
    category: QueryCategory
    entity: Entity
    params: Dict[str, Any]
    original_query: str
    timeframe: Optional[str] = None
    limit: Optional[int] = None


# =============================================================================
# INTENT PATTERNS
# =============================================================================

# Map of patterns to tool names with confidence scores
INTENT_PATTERNS: List[Tuple[str, str, float, Dict]] = [
    
    # =========================================================================
    # USER PATTERNS
    # =========================================================================
    
    # User count
    (r"how many (users|members|people|accounts)", "user_count", 0.95, {}),
    (r"(count|number|total).*(users|members|people|accounts)", "user_count", 0.95, {}),
    (r"(users|members|people|accounts).*(count|number|total)", "user_count", 0.90, {}),
    (r"^users\s*$", "user_count", 0.85, {}),
    
    # Users by role
    (r"users.*(by|per|group).*(role|type)", "users_by_role", 0.95, {}),
    (r"(role|type).*distribution", "users_by_role", 0.90, {}),
    (r"how many.*(admin|manager|user)s?", "users_by_role", 0.85, {}),
    
    # Users by status
    (r"users.*(by|per|group).*status", "users_by_status", 0.95, {}),
    (r"(active|inactive|pending).*users", "users_by_status", 0.85, {}),
    (r"user.*status.*distribution", "users_by_status", 0.90, {}),
    
    # Top uploaders
    (r"(top|best|most).*(uploader|active).*user", "top_uploaders", 0.95, {}),
    (r"who.*(upload|share).*most", "top_uploaders", 0.95, {}),
    (r"users.*most.*(file|upload)", "top_uploaders", 0.90, {}),
    (r"^top uploader", "top_uploaders", 0.95, {}),
    (r"top \d+ uploader", "top_uploaders", 0.95, {}),
    
    # Recent users
    (r"(recent|latest|new).*users", "recent_users", 0.95, {}),
    (r"users.*(sign.*up|register|creat).*recent", "recent_users", 0.90, {}),
    (r"who.*join.*recent", "recent_users", 0.85, {}),
    
    # =========================================================================
    # FILE PATTERNS
    # =========================================================================
    
    # File count
    (r"how many (files|documents|uploads)", "file_count", 0.95, {}),
    (r"(count|number|total).*(files|documents|uploads)", "file_count", 0.95, {}),
    (r"(files|documents|uploads).*(count|number|total)", "file_count", 0.90, {}),
    (r"^files?\s*$", "file_count", 0.85, {}),
    
    # Total storage
    (r"(total|how much).*storage", "total_storage", 0.95, {}),
    (r"storage.*(used|usage|consumption)", "total_storage", 0.95, {}),
    (r"(disk|space).*used", "total_storage", 0.90, {}),
    (r"how much.*space", "total_storage", 0.90, {}),
    
    # Storage by user
    (r"storage.*(by|per).*user", "storage_by_user", 0.95, {}),
    (r"user.*storage", "storage_by_user", 0.85, {}),
    (r"who.*using.*most.*storage", "storage_by_user", 0.95, {}),
    (r"(space|disk).*(by|per).*user", "storage_by_user", 0.90, {}),
    
    # Files by type
    (r"files?.*(by|per|group).*type", "files_by_type", 0.95, {}),
    (r"(file|content).*type.*distribution", "files_by_type", 0.90, {}),
    (r"(pdf|image|video|document).*files", "files_by_type", 0.85, {}),
    (r"what.*type.*files?", "files_by_type", 0.90, {}),
    
    # Largest files
    (r"(largest|biggest|heaviest).*files?", "largest_files", 0.95, {}),
    (r"files?.*(large|big|heavy)", "largest_files", 0.85, {}),
    (r"top.*files?.*size", "largest_files", 0.90, {}),
    (r"^largest files", "largest_files", 0.95, {}),
    (r"big files", "largest_files", 0.90, {}),
    
    # Recent uploads
    (r"(recent|latest|new).*upload", "recent_uploads", 0.95, {}),
    (r"(recent|latest|new).*files?", "recent_uploads", 0.90, {}),
    (r"upload.*(today|yesterday|this week|recent)", "recent_uploads", 0.95, {}),
    (r"what.*upload.*recent", "recent_uploads", 0.90, {}),
    (r"^recent uploads?$", "recent_uploads", 0.95, {}),
    (r"^latest uploads?$", "recent_uploads", 0.95, {}),
    
    # Virus scan
    (r"virus.*(scan|status)", "virus_scan_status", 0.95, {}),
    (r"(scan|infected|clean).*files?", "virus_scan_status", 0.90, {}),
    (r"files?.*virus", "virus_scan_status", 0.90, {}),
    
    # Quarantined files
    (r"quarantin", "quarantined_files", 0.95, {}),
    (r"infected.*files?", "quarantined_files", 0.90, {}),
    (r"blocked.*files?", "quarantined_files", 0.85, {}),
    
    # =========================================================================
    # ORGANIZATION PATTERNS
    # =========================================================================
    
    # Org count
    (r"how many.*(org|organization|compan|tenant)", "org_count", 0.95, {}),
    (r"(count|number|total).*(org|organization|compan|tenant)", "org_count", 0.95, {}),
    
    # Org list
    (r"(list|show|all).*(org|organization|compan|tenant)", "org_list", 0.95, {}),
    (r"^org(anization)?s?\s*$", "org_list", 0.85, {}),
    
    # Storage by org
    (r"storage.*(by|per).*(org|organization|compan|tenant)", "storage_by_org", 0.95, {}),
    (r"(org|organization).*(storage|space|disk)", "storage_by_org", 0.90, {}),
    
    # Most active org
    (r"(most|top).*active.*(org|organization|compan|tenant)", "most_active_org", 0.95, {}),
    (r"(org|organization).*(active|busy)", "most_active_org", 0.85, {}),
    
    # =========================================================================
    # FOLDER PATTERNS
    # =========================================================================
    
    # Folder count
    (r"how many.*folder", "folder_count", 0.95, {}),
    (r"(count|number|total).*folder", "folder_count", 0.95, {}),
    (r"^folders?\s*$", "folder_count", 0.85, {}),
    
    # Folder list
    (r"(list|show|all).*folder", "folder_list", 0.95, {}),
    (r"folder.*(list|name)", "folder_list", 0.90, {}),
    
    # =========================================================================
    # TREND PATTERNS
    # =========================================================================
    
    # Uploads by day
    (r"upload.*(trend|daily|by day|over time)", "uploads_by_day", 0.95, {}),
    (r"(daily|weekly).*upload", "uploads_by_day", 0.90, {}),
    (r"upload.*chart", "uploads_by_day", 0.85, {}),
    
    # Signups by day
    (r"signup.*(trend|daily|by day|over time)", "user_signups_by_day", 0.95, {}),
    (r"user.*(growth|trend)", "user_signups_by_day", 0.90, {}),
    (r"(new|registration).*by day", "user_signups_by_day", 0.85, {}),
    
    # =========================================================================
    # MY DATA PATTERNS
    # =========================================================================
    
    # My files
    (r"^my files?$", "my_files", 0.98, {}),
    (r"my files?", "my_files", 0.95, {}),
    (r"files? (i|I).*(upload|own|have)", "my_files", 0.95, {}),
    (r"show me my files?", "my_files", 0.95, {}),
    (r"list my files?", "my_files", 0.95, {}),
    
    # My storage
    (r"^my storage$", "my_storage", 0.98, {}),
    (r"my storage", "my_storage", 0.95, {}),
    (r"how much.*(space|storage).*(i|I).*us", "my_storage", 0.95, {}),
    (r"(i|I).*using.*storage", "my_storage", 0.90, {}),
    
    # My recent uploads
    (r"my.*(recent|latest).*upload", "my_recent_uploads", 0.95, {}),
    (r"what.*did.*(i|I).*upload", "my_recent_uploads", 0.90, {}),
]


# =============================================================================
# TIMEFRAME DETECTION
# =============================================================================

TIMEFRAME_PATTERNS = {
    "today": [r"today", r"this day"],
    "yesterday": [r"yesterday"],
    "this_week": [r"this week"],
    "last_week": [r"last week", r"previous week"],
    "this_month": [r"this month"],
    "last_month": [r"last month", r"previous month"],
    "this_year": [r"this year"],
    "last_7_days": [r"last 7 days", r"past week", r"past 7 days"],
    "last_30_days": [r"last 30 days", r"past month", r"past 30 days"],
    "last_90_days": [r"last 90 days", r"past 90 days", r"last quarter"],
}


def detect_timeframe(query: str) -> str:
    """Detect timeframe from query string."""
    query_lower = query.lower()
    
    for timeframe, patterns in TIMEFRAME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, query_lower):
                return timeframe
    
    return "all_time"


# =============================================================================
# LIMIT DETECTION
# =============================================================================

def detect_limit(query: str) -> int:
    """Detect result limit from query string."""
    query_lower = query.lower()
    
    # Look for explicit numbers
    match = re.search(r"(top|first|last|show|give me)\s*(\d+)", query_lower)
    if match:
        return min(int(match.group(2)), 100)  # Cap at 100
    
    match = re.search(r"(\d+)\s*(files?|users?|items?|results?)", query_lower)
    if match:
        return min(int(match.group(1)), 100)
    
    # Default limits based on context
    if any(word in query_lower for word in ["all", "every", "full list"]):
        return 50
    
    return 10  # Default


# =============================================================================
# MAIN CLASSIFIER
# =============================================================================

class IntentClassifier:
    """
    Fast intent classifier using pattern matching.
    No LLM needed - runs in ~1-5ms.
    """
    
    def __init__(self):
        self.patterns = INTENT_PATTERNS
        logger.info(f"Intent classifier initialized with {len(self.patterns)} patterns")
    
    def classify(self, query: str) -> Optional[ClassifiedIntent]:
        """
        Classify user query into an intent with tool name.
        
        Returns:
            ClassifiedIntent if matched, None otherwise
        """
        query_lower = query.lower().strip()
        
        best_match: Optional[ClassifiedIntent] = None
        best_confidence = 0.0
        
        for pattern, tool_name, base_confidence, extra_params in self.patterns:
            if re.search(pattern, query_lower, re.IGNORECASE):
                # Calculate confidence boost based on query specificity
                confidence = base_confidence
                
                # Boost confidence for exact matches
                if re.fullmatch(pattern, query_lower, re.IGNORECASE):
                    confidence = min(confidence + 0.05, 1.0)
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    
                    # Detect additional parameters
                    timeframe = detect_timeframe(query)
                    limit = detect_limit(query)
                    
                    # Determine category and entity from tool name
                    category = self._get_category(tool_name)
                    entity = self._get_entity(tool_name)
                    
                    best_match = ClassifiedIntent(
                        tool_name=tool_name,
                        confidence=confidence,
                        category=category,
                        entity=entity,
                        params={**extra_params},
                        original_query=query,
                        timeframe=timeframe,
                        limit=limit
                    )
        
        if best_match:
            logger.info(
                f"Classified '{query}' -> tool={best_match.tool_name}, "
                f"confidence={best_match.confidence:.2f}"
            )
        else:
            logger.info(f"No match for '{query}' - will use LLM fallback")
        
        return best_match
    
    def _get_category(self, tool_name: str) -> QueryCategory:
        """Get query category from tool name."""
        if "count" in tool_name:
            return QueryCategory.COUNT
        if "list" in tool_name or "recent" in tool_name:
            return QueryCategory.LIST
        if "by_" in tool_name or "storage" in tool_name:
            return QueryCategory.STATS
        if "trend" in tool_name or "by_day" in tool_name:
            return QueryCategory.TREND
        if "my_" in tool_name:
            return QueryCategory.MY_DATA
        return QueryCategory.UNKNOWN
    
    def _get_entity(self, tool_name: str) -> Entity:
        """Get entity type from tool name."""
        if "user" in tool_name or "uploader" in tool_name or "signup" in tool_name:
            return Entity.USER
        if "file" in tool_name or "upload" in tool_name:
            return Entity.FILE
        if "folder" in tool_name:
            return Entity.FOLDER
        if "org" in tool_name:
            return Entity.ORGANIZATION
        if "storage" in tool_name:
            return Entity.STORAGE
        return Entity.UNKNOWN
    
    def get_suggestions(self, query: str, top_k: int = 3) -> List[str]:
        """
        Get suggested queries similar to user input.
        Useful for autocomplete or "did you mean?" features.
        """
        # Find partially matching patterns
        suggestions = []
        query_lower = query.lower()
        
        tool_suggestions = {
            "user": ["How many users?", "Users by role", "Top uploaders"],
            "file": ["How many files?", "Recent uploads", "Largest files"],
            "storage": ["Total storage used", "Storage by user", "Storage by organization"],
            "folder": ["How many folders?", "List folders"],
            "org": ["How many organizations?", "Most active organization"],
        }
        
        for keyword, sug_list in tool_suggestions.items():
            if keyword in query_lower:
                suggestions.extend(sug_list)
        
        return suggestions[:top_k]


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_classifier_instance: Optional[IntentClassifier] = None


def get_intent_classifier() -> IntentClassifier:
    """Get singleton intent classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance


# =============================================================================
# QUICK TEST
# =============================================================================

if __name__ == "__main__":
    # Quick test
    classifier = get_intent_classifier()
    
    test_queries = [
        "how many users?",
        "How many files do we have?",
        "show me storage by user",
        "what are my recent uploads",
        "top 5 largest files",
        "users by role",
        "uploads today",
        "quarantined files",
        "who uploaded the most files this week?",
    ]
    
    for query in test_queries:
        result = classifier.classify(query)
        if result:
            print(f"✅ '{query}' -> {result.tool_name} ({result.confidence:.2f})")
        else:
            print(f"❌ '{query}' -> No match")
