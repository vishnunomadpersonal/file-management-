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
    
    # =========================================================================
    # COMPLEX / MULTI-CONDITION PATTERNS (NEW)
    # =========================================================================
    
    # Users with N files
    (r"users?.*(more than|over|greater than|>\s*)\s*\d+\s*files?", "users_with_more_than_n_files", 0.95, {}),
    (r"who.*(uploaded|has|have).*more than\s*\d+", "users_with_more_than_n_files", 0.95, {}),
    (r"users?.*with.*at least\s*\d+\s*files?", "users_with_more_than_n_files", 0.90, {}),
    
    # Range file queries
    (r"users?.*between\s*\d+\s*and\s*\d+\s*files?", "users_with_range_files", 0.95, {}),
    (r"users?.*\d+\s*to\s*\d+\s*files?", "users_with_range_files", 0.90, {}),
    
    # Approved users patterns
    (r"(approved|accepted).*users?", "approved_users", 0.90, {}),
    (r"users?.*approved", "approved_users", 0.85, {}),
    (r"who.*approved", "approved_users", 0.80, {}),
    
    # Pending users patterns
    (r"(pending|waiting).*users?", "pending_users", 0.90, {}),
    (r"users?.*pending", "pending_users", 0.85, {}),
    (r"users?.*await", "pending_users", 0.85, {}),
    
    # Users without files
    (r"users?.*without.*files?", "users_without_files", 0.95, {}),
    (r"users?.*(haven.t|have not|never).*upload", "users_without_files", 0.95, {}),
    (r"who.*never.*upload", "users_without_files", 0.90, {}),
    (r"users?.*no.*files?", "users_without_files", 0.85, {}),
    
    # Users never logged in
    (r"users?.*(never|not).*log", "users_never_logged_in", 0.95, {}),
    (r"never.*logged.*in", "users_never_logged_in", 0.90, {}),
    (r"users?.*without.*login", "users_never_logged_in", 0.85, {}),
    
    # Admin users
    (r"(admin|administrator)s?\s*(list|users?)?$", "admin_users", 0.95, {}),
    (r"(all|show|list).*admins?", "admin_users", 0.95, {}),
    (r"super.*admins?", "admin_users", 0.90, {}),
    (r"org.*admins?", "admin_users", 0.90, {}),
    
    # Approvers summary
    (r"who.*approved.*user", "approvers_summary", 0.95, {}),
    (r"approval.*summary", "approvers_summary", 0.90, {}),
    (r"approvers?", "approvers_summary", 0.85, {}),
    
    # Organizations with N users
    (r"org.*(more than|over|>\s*)\s*\d+\s*users?", "orgs_with_min_users", 0.95, {}),
    (r"org.*with.*at least\s*\d+\s*users?", "orgs_with_min_users", 0.90, {}),
    
    # Organizations without files
    (r"org.*(no|without|empty).*files?", "orgs_without_files", 0.95, {}),
    (r"empty.*org", "orgs_without_files", 0.90, {}),
    (r"org.*no.*files?", "orgs_without_files", 0.85, {}),
    
    # Approved users without files
    (r"approved.*without.*files?", "approved_users_without_files", 0.95, {}),
    (r"approved.*(never|no).*upload", "approved_users_without_files", 0.95, {}),
    
    # Users in specific org
    (r"users?.*in.*(org|organization)", "users_in_org", 0.85, {}),
    
    # Files in specific org
    (r"files?.*in.*(org|organization)", "files_in_org", 0.85, {}),
    
    # File type filters
    (r"pdf\s*files?", "pdf_files", 0.95, {}),
    (r"files?.*pdf", "pdf_files", 0.90, {}),
    (r"image\s*files?", "image_files", 0.95, {}),
    (r"files?.*image", "image_files", 0.90, {}),
    (r"(picture|photo)s?\s*files?", "image_files", 0.90, {}),
    
    # Average file size
    (r"average.*file.*size", "average_file_size", 0.95, {}),
    (r"avg.*file.*size", "average_file_size", 0.95, {}),
    (r"mean.*file.*size", "average_file_size", 0.90, {}),
    
    # Files not quarantined
    (r"files?.*(not|clean|safe).*quarantin", "files_not_quarantined", 0.95, {}),
    (r"clean.*files?", "files_not_quarantined", 0.85, {}),
    (r"safe.*files?", "files_not_quarantined", 0.85, {}),
    
    # Empty folders
    (r"empty.*folders?", "empty_folders", 0.95, {}),
    (r"folders?.*no.*files?", "empty_folders", 0.95, {}),
    (r"folders?.*without.*files?", "empty_folders", 0.95, {}),
    
    # Active vs inactive
    (r"active.*vs.*inactive", "active_vs_inactive_users", 0.95, {}),
    (r"active.*inactive.*users?", "active_vs_inactive_users", 0.90, {}),
    (r"(percentage|ratio).*active", "active_vs_inactive_users", 0.85, {}),
    
    # Monthly trends
    (r"monthly.*upload.*trend", "monthly_upload_trend", 0.95, {}),
    (r"upload.*by.*month", "monthly_upload_trend", 0.90, {}),
    (r"files?.*grouped.*month", "monthly_upload_trend", 0.90, {}),
    (r"monthly.*signup.*trend", "monthly_signup_trend", 0.95, {}),
    (r"signup.*by.*month", "monthly_signup_trend", 0.90, {}),
    (r"users?.*by.*month", "monthly_signup_trend", 0.85, {}),
    
    # User list
    (r"^list\s*(all)?\s*users?$", "user_list", 0.95, {}),
    (r"^show\s*(all)?\s*users?$", "user_list", 0.95, {}),
    (r"^all\s*users?$", "user_list", 0.90, {}),
    
    # File list  
    (r"^list\s*(all)?\s*files?$", "file_list", 0.95, {}),
    (r"^show\s*(all)?\s*files?$", "file_list", 0.95, {}),
    (r"^all\s*files?$", "file_list", 0.90, {}),
    
    # =========================================================================
    # EXPANDED PATTERNS v4.0 - COMPREHENSIVE COVERAGE
    # =========================================================================
    
    # ----- SMALLEST FILES -----
    (r"(smallest|tiniest|lightest).*files?", "smallest_files", 0.95, {}),
    (r"files?.*(small|tiny|light)", "smallest_files", 0.85, {}),
    (r"bottom.*files?.*size", "smallest_files", 0.90, {}),
    
    # ----- SIZE COMPARISON FILES -----
    (r"files?.*(larger|bigger|greater|more) than\s*\d+", "files_larger_than", 0.95, {}),
    (r"files?.*(over|above)\s*\d+", "files_larger_than", 0.90, {}),
    (r"files?.*(smaller|less) than\s*\d+", "files_smaller_than", 0.95, {}),
    (r"files?.*(under|below)\s*\d+", "files_smaller_than", 0.90, {}),
    
    # ----- VIDEO FILES -----
    (r"video\s*files?", "video_files", 0.95, {}),
    (r"files?.*video", "video_files", 0.90, {}),
    (r"(movie|mp4|avi|mkv)\s*files?", "video_files", 0.90, {}),
    
    # ----- AUDIO FILES -----
    (r"audio\s*files?", "audio_files", 0.95, {}),
    (r"files?.*audio", "audio_files", 0.90, {}),
    (r"(music|mp3|wav|sound)\s*files?", "audio_files", 0.90, {}),
    
    # ----- DOCUMENT FILES -----
    (r"document\s*files?", "document_files", 0.95, {}),
    (r"(doc|docx|word)\s*files?", "document_files", 0.95, {}),
    (r"(txt|text)\s*files?", "document_files", 0.90, {}),
    (r"word.*documents?", "document_files", 0.90, {}),
    
    # ----- SPREADSHEET FILES -----
    (r"spreadsheet\s*files?", "spreadsheet_files", 0.95, {}),
    (r"(xls|xlsx|excel)\s*files?", "spreadsheet_files", 0.95, {}),
    (r"csv\s*files?", "spreadsheet_files", 0.90, {}),
    (r"excel.*files?", "spreadsheet_files", 0.90, {}),
    
    # ----- ARCHIVE FILES -----
    (r"archive\s*files?", "archive_files", 0.95, {}),
    (r"(zip|rar|compressed)\s*files?", "archive_files", 0.95, {}),
    (r"files?.*compressed", "archive_files", 0.85, {}),
    
    # ----- USER STATUS -----
    (r"rejected.*users?", "rejected_users", 0.95, {}),
    (r"users?.*rejected", "rejected_users", 0.90, {}),
    
    (r"suspended.*users?", "suspended_users", 0.95, {}),
    (r"deactivated.*users?", "suspended_users", 0.95, {}),
    (r"inactive.*users?", "suspended_users", 0.90, {}),
    (r"disabled.*users?", "suspended_users", 0.90, {}),
    
    (r"active.*users?$", "active_users", 0.90, {}),
    (r"users?.*currently.*active", "active_users", 0.90, {}),
    
    # ----- TIME-BASED USERS -----
    (r"users?.*created.*today", "users_created_today", 0.95, {}),
    (r"users?.*signed.*up.*today", "users_created_today", 0.95, {}),
    (r"new.*users?.*today", "users_created_today", 0.90, {}),
    (r"today.*(new|signups?)", "users_created_today", 0.85, {}),
    
    (r"users?.*created.*this.*week", "users_created_this_week", 0.95, {}),
    (r"users?.*signed.*up.*this.*week", "users_created_this_week", 0.95, {}),
    (r"new.*users?.*this.*week", "users_created_this_week", 0.90, {}),
    
    (r"users?.*created.*this.*month", "users_created_this_month", 0.95, {}),
    (r"users?.*signed.*up.*this.*month", "users_created_this_month", 0.95, {}),
    (r"new.*users?.*this.*month", "users_created_this_month", 0.90, {}),
    
    (r"(oldest|first).*users?", "oldest_users", 0.95, {}),
    (r"users?.*sign.*up.*first", "oldest_users", 0.90, {}),
    (r"earliest.*users?", "oldest_users", 0.90, {}),
    
    # ----- TIME-BASED FILES -----
    (r"files?.*upload.*today", "files_uploaded_today", 0.95, {}),
    (r"today.*upload", "files_uploaded_today", 0.90, {}),
    (r"files?.*today", "files_uploaded_today", 0.85, {}),
    
    (r"files?.*upload.*this.*week", "files_uploaded_this_week", 0.95, {}),
    (r"this.*week.*upload", "files_uploaded_this_week", 0.90, {}),
    
    (r"files?.*upload.*this.*month", "files_uploaded_this_month", 0.95, {}),
    (r"this.*month.*upload", "files_uploaded_this_month", 0.90, {}),
    
    (r"(oldest|first).*files?", "oldest_files", 0.95, {}),
    (r"files?.*upload.*first", "oldest_files", 0.90, {}),
    (r"earliest.*files?", "oldest_files", 0.90, {}),
    
    # ----- LOGIN/ACTIVITY -----
    (r"recently.*logged.*in", "recently_logged_in_users", 0.95, {}),
    (r"users?.*logged.*in.*recent", "recently_logged_in_users", 0.95, {}),
    (r"recent.*login", "recently_logged_in_users", 0.90, {}),
    (r"last.*login", "recently_logged_in_users", 0.85, {}),
    
    (r"dormant.*users?", "dormant_users", 0.95, {}),
    (r"users?.*not.*logged.*in", "dormant_users", 0.90, {}),
    (r"users?.*inactive.*30.*day", "dormant_users", 0.90, {}),
    (r"stale.*users?", "dormant_users", 0.85, {}),
    
    (r"users?.*logged.*in.*today", "users_logged_in_today", 0.95, {}),
    (r"who.*logged.*in.*today", "users_logged_in_today", 0.95, {}),
    (r"today.*login", "users_logged_in_today", 0.90, {}),
    
    # ----- STORAGE -----
    (r"users?.*(most|highest).*storage", "users_with_most_storage", 0.95, {}),
    (r"who.*using.*most.*storage", "users_with_most_storage", 0.95, {}),
    (r"top.*storage.*users?", "users_with_most_storage", 0.90, {}),
    (r"storage.*hogs?", "users_with_most_storage", 0.85, {}),
    
    (r"users?.*(least|lowest).*storage", "users_with_least_storage", 0.95, {}),
    (r"who.*using.*least.*storage", "users_with_least_storage", 0.95, {}),
    
    (r"storage.*by.*file.*type", "storage_by_file_type", 0.95, {}),
    (r"storage.*per.*type", "storage_by_file_type", 0.90, {}),
    (r"(space|disk).*by.*type", "storage_by_file_type", 0.90, {}),
    
    # ----- VIRUS/SECURITY -----
    (r"files?.*(pending|waiting).*scan", "files_pending_scan", 0.95, {}),
    (r"files?.*not.*scanned", "files_pending_scan", 0.95, {}),
    (r"unscanned.*files?", "files_pending_scan", 0.90, {}),
    
    (r"virus.*detected.*count", "virus_detected_count", 0.95, {}),
    (r"how many.*(virus|infected)", "virus_detected_count", 0.90, {}),
    (r"infected.*count", "virus_detected_count", 0.90, {}),
    
    (r"infected.*files?", "infected_files", 0.95, {}),
    (r"files?.*virus", "infected_files", 0.90, {}),
    (r"malware.*files?", "infected_files", 0.90, {}),
    
    (r"clean.*files?", "clean_files", 0.90, {}),
    (r"safe.*files?", "clean_files", 0.85, {}),
    (r"files?.*passed.*scan", "clean_files", 0.90, {}),
    
    # ----- STATISTICS/AVERAGES -----
    (r"average.*files?.*per.*user", "average_files_per_user", 0.95, {}),
    (r"files?.*per.*user.*average", "average_files_per_user", 0.90, {}),
    (r"avg.*files?.*per.*user", "average_files_per_user", 0.95, {}),
    
    (r"average.*storage.*per.*user", "average_storage_per_user", 0.95, {}),
    (r"storage.*per.*user.*average", "average_storage_per_user", 0.90, {}),
    (r"avg.*storage.*per.*user", "average_storage_per_user", 0.95, {}),
    
    (r"files?.*per.*folder", "files_per_folder", 0.95, {}),
    (r"folder.*file.*count", "files_per_folder", 0.90, {}),
    
    (r"folders?.*most.*files?", "folders_with_most_files", 0.95, {}),
    (r"(biggest|largest).*folders?", "folders_with_most_files", 0.90, {}),
    (r"folders?.*by.*file.*count", "folders_with_most_files", 0.85, {}),
    
    # ----- ROLES -----
    (r"users?.*per.*role", "user_role_count", 0.95, {}),
    (r"role.*count", "user_role_count", 0.90, {}),
    (r"role.*distribution", "user_role_count", 0.90, {}),
    (r"how many.*of each.*role", "user_role_count", 0.85, {}),
    
    (r"regular.*users?", "regular_users", 0.95, {}),
    (r"(non-admin|non admin).*users?", "regular_users", 0.90, {}),
    (r"normal.*users?", "regular_users", 0.85, {}),
    
    (r"super.*admins?", "super_admins", 0.95, {}),
    (r"superadmins?", "super_admins", 0.90, {}),
    
    (r"org.*admins?", "org_admins", 0.95, {}),
    (r"organization.*admins?", "org_admins", 0.90, {}),
    
    # ----- ORGANIZATIONS -----
    (r"inactive.*org", "inactive_organizations", 0.95, {}),
    (r"org.*inactive", "inactive_organizations", 0.90, {}),
    (r"disabled.*org", "inactive_organizations", 0.85, {}),
    
    (r"(newest|recent|latest).*org", "newest_organizations", 0.95, {}),
    (r"org.*recent", "newest_organizations", 0.90, {}),
    (r"new.*org", "newest_organizations", 0.85, {}),
    
    (r"org.*by.*plan", "organizations_by_plan", 0.95, {}),
    (r"plan.*distribution", "organizations_by_plan", 0.90, {}),
    
    (r"users?.*per.*org", "users_per_organization", 0.95, {}),
    (r"org.*user.*count", "users_per_organization", 0.90, {}),
    
    # ----- TRENDS -----
    (r"weekly.*upload.*trend", "weekly_upload_trend", 0.95, {}),
    (r"upload.*by.*week", "weekly_upload_trend", 0.90, {}),
    
    (r"yearly.*upload.*trend", "yearly_upload_trend", 0.95, {}),
    (r"upload.*by.*year", "yearly_upload_trend", 0.90, {}),
    (r"annual.*upload", "yearly_upload_trend", 0.85, {}),
    
    (r"weekly.*signup.*trend", "weekly_signup_trend", 0.95, {}),
    (r"signup.*by.*week", "weekly_signup_trend", 0.90, {}),
    
    # ----- COMPARISONS -----
    (r"uploads?.*vs.*users?", "uploads_vs_users", 0.95, {}),
    (r"upload.*rate", "uploads_vs_users", 0.90, {}),
    (r"how many.*users?.*upload", "uploads_vs_users", 0.85, {}),
    
    (r"approved.*vs.*pending", "approved_vs_pending", 0.95, {}),
    (r"pending.*vs.*approved", "approved_vs_pending", 0.95, {}),
    (r"approval.*status", "approved_vs_pending", 0.85, {}),
    
    # ----- SEARCH/LOOKUP -----
    (r"(find|search|lookup).*user.*email", "user_by_email", 0.95, {}),
    (r"user.*with.*email", "user_by_email", 0.90, {}),
    (r"who.*email.*is", "user_by_email", 0.85, {}),
    
    (r"(find|search|lookup).*user.*name", "user_by_name", 0.95, {}),
    (r"user.*named", "user_by_name", 0.90, {}),
    (r"user.*called", "user_by_name", 0.85, {}),
    
    (r"files?.*by.*user", "files_by_user", 0.85, {}),
    (r"files?.*uploaded.*by", "files_by_user", 0.90, {}),
    (r"(user|person).*files?", "files_by_user", 0.80, {}),
    
    (r"(find|search|lookup).*file.*name", "file_by_name", 0.95, {}),
    (r"file.*named", "file_by_name", 0.90, {}),
    (r"file.*called", "file_by_name", 0.85, {}),
    
    # ----- COUNTS -----
    (r"pending.*user.*count", "pending_user_count", 0.95, {}),
    (r"how many.*pending", "pending_user_count", 0.90, {}),
    (r"count.*pending.*user", "pending_user_count", 0.90, {}),
    
    (r"approved.*user.*count", "approved_user_count", 0.95, {}),
    (r"how many.*approved", "approved_user_count", 0.90, {}),
    (r"count.*approved.*user", "approved_user_count", 0.90, {}),
    
    (r"admin.*count", "admin_count", 0.95, {}),
    (r"how many.*admin", "admin_count", 0.90, {}),
    (r"count.*admin", "admin_count", 0.90, {}),
    
    (r"quarantine.*count", "quarantined_file_count", 0.95, {}),
    (r"how many.*quarantine", "quarantined_file_count", 0.90, {}),
    
    (r"clean.*file.*count", "clean_file_count", 0.95, {}),
    (r"how many.*clean.*file", "clean_file_count", 0.90, {}),
    
    # ----- TOP N -----
    (r"top\s*\d+.*(files?|largest)", "top_n_files_by_size", 0.95, {}),
    (r"top\s*\d+.*biggest", "top_n_files_by_size", 0.95, {}),
    
    (r"bottom\s*\d+.*(files?|smallest)", "bottom_n_files_by_size", 0.95, {}),
    
    (r"top\s*\d+.*users?.*storage", "top_n_users_by_storage", 0.95, {}),
    (r"top\s*\d+.*storage.*users?", "top_n_users_by_storage", 0.90, {}),
    
    (r"top\s*\d+.*users?.*files?", "top_n_users_by_files", 0.95, {}),
    (r"top\s*\d+.*uploaders?", "top_n_users_by_files", 0.90, {}),
    
    # ----- TODAY COUNTS -----
    (r"uploads?.*today.*count", "uploads_today_count", 0.95, {}),
    (r"how many.*upload.*today", "uploads_today_count", 0.95, {}),
    (r"files?.*today.*count", "uploads_today_count", 0.90, {}),
    
    (r"signups?.*today.*count", "signups_today_count", 0.95, {}),
    (r"how many.*sign.*up.*today", "signups_today_count", 0.95, {}),
    (r"new.*users?.*today.*count", "signups_today_count", 0.90, {}),
    
    (r"logins?.*today.*count", "logins_today_count", 0.95, {}),
    (r"how many.*log.*in.*today", "logins_today_count", 0.95, {}),
    
    # ----- EXTENSION-BASED -----
    (r"files?.*by.*extension", "files_by_extension", 0.95, {}),
    (r"extension.*distribution", "files_by_extension", 0.90, {}),
    (r"file.*types?.*count", "files_by_extension", 0.85, {}),
    
    (r"(most|common).*file.*types?", "most_common_file_types", 0.95, {}),
    (r"popular.*file.*types?", "most_common_file_types", 0.90, {}),
    
    # ----- SUMMARIES -----
    (r"system.*summary", "system_summary", 0.95, {}),
    (r"(overall|total).*summary", "system_summary", 0.90, {}),
    (r"dashboard.*stats?", "system_summary", 0.85, {}),
    (r"all.*stats?", "system_summary", 0.80, {}),
    
    (r"org.*summary", "org_summary", 0.95, {}),
    (r"organization.*summary", "org_summary", 0.90, {}),
    (r"my.*org.*stats?", "org_summary", 0.85, {}),
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
