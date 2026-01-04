"""
Analytics Tools - Pre-built SQL Templates for Production
=========================================================
Fast, secure, and reliable analytics queries.
These execute in ~50ms instead of 30s with LLM-SQL.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TimeFrame(Enum):
    """Supported timeframes for queries."""
    TODAY = "today"
    YESTERDAY = "yesterday"
    THIS_WEEK = "this_week"
    LAST_WEEK = "last_week"
    THIS_MONTH = "this_month"
    LAST_MONTH = "last_month"
    THIS_YEAR = "this_year"
    LAST_7_DAYS = "last_7_days"
    LAST_30_DAYS = "last_30_days"
    LAST_90_DAYS = "last_90_days"
    ALL_TIME = "all_time"


@dataclass
class ToolResult:
    """Result from an analytics tool."""
    success: bool
    data: Any
    message: str
    row_count: int = 0
    query_time_ms: int = 0
    tool_name: str = ""


@dataclass
class AnalyticsTool:
    """Definition of an analytics tool."""
    name: str
    description: str
    sql_template: str
    params: List[str]
    response_template: str
    requires_org_filter: bool = True
    requires_user_filter: bool = False


# =============================================================================
# TIME FILTER HELPERS
# =============================================================================

def get_time_filter(timeframe: str, column: str = "created_at") -> str:
    """Generate SQL time filter clause."""
    now = datetime.now()
    
    filters = {
        "today": f"DATE({column}) = CURDATE()",
        "yesterday": f"DATE({column}) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)",
        "this_week": f"{column} >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)",
        "last_week": f"{column} >= DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) + 7 DAY) AND {column} < DATE_SUB(CURDATE(), INTERVAL WEEKDAY(CURDATE()) DAY)",
        "this_month": f"MONTH({column}) = MONTH(CURDATE()) AND YEAR({column}) = YEAR(CURDATE())",
        "last_month": f"MONTH({column}) = MONTH(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) AND YEAR({column}) = YEAR(DATE_SUB(CURDATE(), INTERVAL 1 MONTH))",
        "this_year": f"YEAR({column}) = YEAR(CURDATE())",
        "last_7_days": f"{column} >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)",
        "last_30_days": f"{column} >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)",
        "last_90_days": f"{column} >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)",
        "all_time": "1=1"
    }
    
    return filters.get(timeframe, "1=1")


# =============================================================================
# ANALYTICS TOOLS DEFINITIONS
# =============================================================================

ANALYTICS_TOOLS: Dict[str, AnalyticsTool] = {
    
    # =========================================================================
    # USER ANALYTICS
    # =========================================================================
    
    "user_count": AnalyticsTool(
        name="user_count",
        description="Count total users",
        sql_template="""
            SELECT COUNT(*) as total_users
            FROM users u
            WHERE 1=1 {org_filter} {time_filter}
        """,
        params=["org_id", "timeframe"],
        response_template="There are **{total_users}** users{context}.",
        requires_org_filter=True
    ),
    
    "user_list": AnalyticsTool(
        name="user_list",
        description="List all users with details",
        sql_template="""
            SELECT u.name, u.email, u.role, u.status, u.created_at
            FROM users u
            WHERE 1=1 {org_filter}
            ORDER BY u.name
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_by_role": AnalyticsTool(
        name="users_by_role",
        description="Count users grouped by role",
        sql_template="""
            SELECT u.role, COUNT(*) as count
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY u.role
            ORDER BY count DESC
        """,
        params=["org_id"],
        response_template="User distribution by role:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_by_status": AnalyticsTool(
        name="users_by_status",
        description="Count users grouped by status",
        sql_template="""
            SELECT u.status, COUNT(*) as count
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY u.status
            ORDER BY count DESC
        """,
        params=["org_id"],
        response_template="User distribution by status:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "approved_users": AnalyticsTool(
        name="approved_users",
        description="List approved users",
        sql_template="""
            SELECT u.name, u.email, u.role, u.approved_at
            FROM users u
            WHERE u.status = 'approved' {org_filter}
            ORDER BY u.approved_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Approved users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "pending_users": AnalyticsTool(
        name="pending_users",
        description="List pending users",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE u.status = 'pending' {org_filter}
            ORDER BY u.created_at ASC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Pending users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "top_uploaders": AnalyticsTool(
        name="top_uploaders",
        description="Users who uploaded the most files",
        sql_template="""
            SELECT u.name, u.email, COUNT(f.id) as upload_count
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter} {time_filter}
            GROUP BY u.id, u.name, u.email
            ORDER BY upload_count DESC
            LIMIT {limit}
        """,
        params=["org_id", "timeframe", "limit"],
        response_template="Top uploaders:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "recent_users": AnalyticsTool(
        name="recent_users",
        description="Recently created users",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE 1=1 {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Recent users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_without_files": AnalyticsTool(
        name="users_without_files",
        description="Users who have not uploaded any files",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE f.id IS NULL {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users without files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_never_logged_in": AnalyticsTool(
        name="users_never_logged_in",
        description="Users who never logged in",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE u.last_login_at IS NULL {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users who never logged in:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "admin_users": AnalyticsTool(
        name="admin_users",
        description="List all admin users (super_admin and org_admin)",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE u.role IN ('super_admin', 'org_admin') {org_filter}
            ORDER BY u.role, u.name
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Admin users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "approvers_summary": AnalyticsTool(
        name="approvers_summary",
        description="Summary of who approved users",
        sql_template="""
            SELECT 
                approver.name as approved_by,
                COUNT(u.id) as users_approved
            FROM users u
            JOIN users approver ON u.approved_by = approver.id
            WHERE u.status = 'approved' {org_filter}
            GROUP BY approver.id, approver.name
            ORDER BY users_approved DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Approval summary:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # =========================================================================
    # FILE ANALYTICS
    # =========================================================================
    
    "file_count": AnalyticsTool(
        name="file_count",
        description="Count total files",
        sql_template="""
            SELECT COUNT(*) as total_files
            FROM files f
            WHERE 1=1 {org_filter} {user_filter} {time_filter}
        """,
        params=["org_id", "user_id", "timeframe"],
        response_template="There are **{total_files}** files{context}.",
        requires_org_filter=True
    ),
    
    "file_list": AnalyticsTool(
        name="file_list",
        description="List all files with details",
        sql_template="""
            SELECT 
                f.filename,
                f.size,
                f.content_type,
                u.name as uploaded_by,
                f.virus_scan_date
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE 1=1 {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "total_storage": AnalyticsTool(
        name="total_storage",
        description="Total storage used in bytes",
        sql_template="""
            SELECT 
                COALESCE(SUM(f.size), 0) as total_bytes,
                COUNT(*) as file_count
            FROM files f
            WHERE 1=1 {org_filter} {user_filter}
        """,
        params=["org_id", "user_id"],
        response_template="Storage used: **{formatted_size}** across {file_count} files.",
        requires_org_filter=True
    ),
    
    "storage_by_user": AnalyticsTool(
        name="storage_by_user",
        description="Storage used per user",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                COALESCE(SUM(f.size), 0) as bytes_used,
                COUNT(f.id) as file_count
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email
            ORDER BY bytes_used DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Storage by user:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_by_type": AnalyticsTool(
        name="files_by_type",
        description="Files grouped by content type",
        sql_template="""
            SELECT 
                f.content_type,
                COUNT(*) as count,
                COALESCE(SUM(f.size), 0) as total_size
            FROM files f
            WHERE 1=1 {org_filter}
            GROUP BY f.content_type
            ORDER BY count DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files by type:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "largest_files": AnalyticsTool(
        name="largest_files",
        description="Largest files by size",
        sql_template="""
            SELECT 
                f.filename,
                f.size,
                f.content_type,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE 1=1 {org_filter} {user_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "user_id", "limit"],
        response_template="Largest files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "recent_uploads": AnalyticsTool(
        name="recent_uploads",
        description="Recently uploaded files",
        sql_template="""
            SELECT 
                f.filename,
                f.size,
                f.content_type,
                u.name as uploaded_by,
                f.virus_scan_date as scan_date
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE 1=1 {org_filter} {user_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "user_id", "limit"],
        response_template="Recent uploads:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "virus_scan_status": AnalyticsTool(
        name="virus_scan_status",
        description="Files by virus scan status",
        sql_template="""
            SELECT 
                f.virus_scan_status,
                COUNT(*) as count
            FROM files f
            WHERE 1=1 {org_filter}
            GROUP BY f.virus_scan_status
            ORDER BY count DESC
        """,
        params=["org_id"],
        response_template="Virus scan status:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "quarantined_files": AnalyticsTool(
        name="quarantined_files",
        description="List quarantined files",
        sql_template="""
            SELECT 
                f.filename,
                f.quarantine_reason,
                u.name as uploaded_by,
                f.virus_scan_date
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.is_quarantined = 1 {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Quarantined files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # =========================================================================
    # ORGANIZATION ANALYTICS
    # =========================================================================
    
    "org_count": AnalyticsTool(
        name="org_count",
        description="Count total organizations",
        sql_template="""
            SELECT COUNT(*) as total_orgs
            FROM organizations o
            WHERE o.is_active = 1
        """,
        params=[],
        response_template="There are **{total_orgs}** active organizations.",
        requires_org_filter=False  # Super admin only
    ),
    
    "org_list": AnalyticsTool(
        name="org_list",
        description="List all organizations",
        sql_template="""
            SELECT 
                o.name,
                o.slug,
                o.plan,
                o.is_active,
                o.created_at
            FROM organizations o
            ORDER BY o.name
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Organizations:\n{formatted_data}",
        requires_org_filter=False  # Super admin only
    ),
    
    "storage_by_org": AnalyticsTool(
        name="storage_by_org",
        description="Storage used per organization",
        sql_template="""
            SELECT 
                o.name,
                o.plan,
                COALESCE(SUM(f.size), 0) as bytes_used,
                COUNT(f.id) as file_count,
                (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id) as user_count
            FROM organizations o
            LEFT JOIN files f ON o.id = f.organization_id
            WHERE o.is_active = 1
            GROUP BY o.id, o.name, o.plan
            ORDER BY bytes_used DESC
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Storage by organization:\n{formatted_data}",
        requires_org_filter=False  # Super admin only
    ),
    
    "most_active_org": AnalyticsTool(
        name="most_active_org",
        description="Organizations with most activity",
        sql_template="""
            SELECT 
                o.name,
                COUNT(f.id) as file_count,
                COALESCE(SUM(f.size), 0) as total_storage,
                (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id) as user_count
            FROM organizations o
            LEFT JOIN files f ON o.id = f.organization_id
            WHERE o.is_active = 1
            GROUP BY o.id, o.name
            ORDER BY file_count DESC
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Most active organizations:\n{formatted_data}",
        requires_org_filter=False  # Super admin only
    ),
    
    # =========================================================================
    # FOLDER ANALYTICS
    # =========================================================================
    
    "folder_count": AnalyticsTool(
        name="folder_count",
        description="Count total folders",
        sql_template="""
            SELECT COUNT(*) as total_folders
            FROM folders fo
            WHERE 1=1 {org_filter}
        """,
        params=["org_id"],
        response_template="There are **{total_folders}** folders{context}.",
        requires_org_filter=True
    ),
    
    "folder_list": AnalyticsTool(
        name="folder_list",
        description="List folders",
        sql_template="""
            SELECT 
                fo.name,
                u.name as created_by,
                fo.created_at,
                (SELECT COUNT(*) FROM files f WHERE f.folder_id = fo.id) as file_count
            FROM folders fo
            LEFT JOIN users u ON fo.created_by_user_id = u.id
            WHERE 1=1 {org_filter}
            ORDER BY fo.name
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Folders:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # =========================================================================
    # TRENDS / TIME-BASED
    # =========================================================================
    
    "uploads_by_day": AnalyticsTool(
        name="uploads_by_day",
        description="File uploads grouped by day",
        sql_template="""
            SELECT 
                DATE(f.virus_scan_date) as date,
                COUNT(*) as uploads,
                COALESCE(SUM(f.size), 0) as bytes_uploaded
            FROM files f
            WHERE f.virus_scan_date IS NOT NULL {org_filter}
            GROUP BY DATE(f.virus_scan_date)
            ORDER BY date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Uploads by day:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "user_signups_by_day": AnalyticsTool(
        name="user_signups_by_day",
        description="User signups grouped by day",
        sql_template="""
            SELECT 
                DATE(u.created_at) as date,
                COUNT(*) as signups
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY DATE(u.created_at)
            ORDER BY date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="User signups by day:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # =========================================================================
    # MY DATA (User-specific)
    # =========================================================================
    
    "my_files": AnalyticsTool(
        name="my_files",
        description="Current user's files",
        sql_template="""
            SELECT 
                f.filename,
                f.size,
                f.content_type,
                f.virus_scan_date
            FROM files f
            WHERE f.user_id = '{user_id}' {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["user_id", "org_id", "limit"],
        response_template="Your files:\n{formatted_data}",
        requires_org_filter=True,
        requires_user_filter=True
    ),
    
    "my_storage": AnalyticsTool(
        name="my_storage",
        description="Current user's storage usage",
        sql_template="""
            SELECT 
                COALESCE(SUM(f.size), 0) as bytes_used,
                COUNT(*) as file_count
            FROM files f
            WHERE f.user_id = '{user_id}' {org_filter}
        """,
        params=["user_id", "org_id"],
        response_template="You're using **{formatted_size}** across {file_count} files.",
        requires_org_filter=True,
        requires_user_filter=True
    ),
    
    "my_recent_uploads": AnalyticsTool(
        name="my_recent_uploads",
        description="Current user's recent uploads",
        sql_template="""
            SELECT 
                f.filename,
                f.size,
                f.content_type,
                f.virus_scan_date
            FROM files f
            WHERE f.user_id = '{user_id}' {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["user_id", "org_id", "limit"],
        response_template="Your recent uploads:\n{formatted_data}",
        requires_org_filter=True,
        requires_user_filter=True
    ),
    
    # =========================================================================
    # COMPLEX MULTI-CONDITION QUERIES (NEW - avoid LLM fallback)
    # =========================================================================
    
    "users_with_more_than_n_files": AnalyticsTool(
        name="users_with_more_than_n_files",
        description="Users who have uploaded more than N files",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                u.role,
                COUNT(f.id) as file_count
            FROM users u
            JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email, u.role
            HAVING COUNT(f.id) > {min_files}
            ORDER BY file_count DESC
            LIMIT {limit}
        """,
        params=["org_id", "min_files", "limit"],
        response_template="Users with more than {min_files} files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_with_range_files": AnalyticsTool(
        name="users_with_range_files",
        description="Users who have uploaded between N and M files",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                COUNT(f.id) as file_count
            FROM users u
            JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email
            HAVING COUNT(f.id) >= {min_files} AND COUNT(f.id) <= {max_files}
            ORDER BY file_count DESC
            LIMIT {limit}
        """,
        params=["org_id", "min_files", "max_files", "limit"],
        response_template="Users with between {min_files} and {max_files} files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_by_user_role": AnalyticsTool(
        name="files_by_user_role",
        description="Files uploaded by users with specific role (admin/user)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by,
                u.role
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE u.role = '{role}' {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "role", "limit"],
        response_template="Files uploaded by {role}s:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "large_files_by_role": AnalyticsTool(
        name="large_files_by_role",
        description="Large files uploaded by admins or specific role",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by,
                u.role
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.size > {min_size} AND u.role IN ('super_admin', 'org_admin') {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "min_size", "limit"],
        response_template="Large files uploaded by admins:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "orgs_with_min_users": AnalyticsTool(
        name="orgs_with_min_users",
        description="Organizations with more than N users",
        sql_template="""
            SELECT 
                o.name,
                o.plan,
                COUNT(u.id) as user_count
            FROM organizations o
            LEFT JOIN users u ON o.id = u.organization_id
            WHERE o.is_active = 1
            GROUP BY o.id, o.name, o.plan
            HAVING COUNT(u.id) > {min_users}
            ORDER BY user_count DESC
            LIMIT {limit}
        """,
        params=["min_users", "limit"],
        response_template="Organizations with more than {min_users} users:\n{formatted_data}",
        requires_org_filter=False  # Super admin only
    ),
    
    "orgs_without_files": AnalyticsTool(
        name="orgs_without_files",
        description="Organizations with no files",
        sql_template="""
            SELECT 
                o.name,
                o.plan,
                (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id) as user_count
            FROM organizations o
            LEFT JOIN files f ON o.id = f.organization_id
            WHERE o.is_active = 1 AND f.id IS NULL
            GROUP BY o.id, o.name, o.plan
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Organizations with no files:\n{formatted_data}",
        requires_org_filter=False  # Super admin only
    ),
    
    "approved_users_without_files": AnalyticsTool(
        name="approved_users_without_files",
        description="Approved users who never uploaded any files",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                u.approved_at,
                u.created_at
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE u.status = 'approved' AND f.id IS NULL {org_filter}
            ORDER BY u.approved_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Approved users without files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_in_org": AnalyticsTool(
        name="users_in_org",
        description="Users in a specific organization by name",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                u.role,
                u.status
            FROM users u
            JOIN organizations o ON u.organization_id = o.id
            WHERE o.name LIKE '%{org_name}%'
            ORDER BY u.name
            LIMIT {limit}
        """,
        params=["org_name", "limit"],
        response_template="Users in organization:\n{formatted_data}",
        requires_org_filter=False  # Custom org filter
    ),
    
    "files_in_org": AnalyticsTool(
        name="files_in_org",
        description="Files in a specific organization by name",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            JOIN organizations o ON f.organization_id = o.id
            JOIN users u ON f.user_id = u.id
            WHERE o.name LIKE '%{org_name}%'
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_name", "limit"],
        response_template="Files in organization:\n{formatted_data}",
        requires_org_filter=False  # Custom org filter
    ),
    
    "pdf_files": AnalyticsTool(
        name="pdf_files",
        description="List PDF files",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.content_type LIKE '%pdf%' {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="PDF files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "image_files": AnalyticsTool(
        name="image_files",
        description="List image files",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.content_type LIKE '%image%' {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Image files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "average_file_size": AnalyticsTool(
        name="average_file_size",
        description="Average file size",
        sql_template="""
            SELECT 
                ROUND(AVG(f.size)/1048576, 2) as avg_size_mb,
                COUNT(*) as file_count,
                ROUND(MIN(f.size)/1024, 2) as min_size_kb,
                ROUND(MAX(f.size)/1048576, 2) as max_size_mb
            FROM files f
            WHERE 1=1 {org_filter}
        """,
        params=["org_id"],
        response_template="Average file size: **{avg_size_mb} MB** ({file_count} files, min: {min_size_kb} KB, max: {max_size_mb} MB)",
        requires_org_filter=True
    ),
    
    "files_not_quarantined": AnalyticsTool(
        name="files_not_quarantined",
        description="Files that are not quarantined (clean)",
        sql_template="""
            SELECT 
                f.filename,
                f.virus_scan_status,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE (f.is_quarantined = 0 OR f.is_quarantined IS NULL) {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Clean files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "empty_folders": AnalyticsTool(
        name="empty_folders",
        description="Folders with no files",
        sql_template="""
            SELECT 
                fo.name,
                fo.path,
                fo.created_at
            FROM folders fo
            LEFT JOIN files f ON fo.id = f.folder_id
            WHERE f.id IS NULL {org_filter}
            ORDER BY fo.name
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Empty folders:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "active_vs_inactive_users": AnalyticsTool(
        name="active_vs_inactive_users",
        description="Count of active vs inactive users",
        sql_template="""
            SELECT 
                CASE WHEN u.is_active = 1 THEN 'Active' ELSE 'Inactive' END as status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM users), 2) as percentage
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY u.is_active
        """,
        params=["org_id"],
        response_template="Active vs Inactive users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "monthly_upload_trend": AnalyticsTool(
        name="monthly_upload_trend",
        description="File uploads grouped by month",
        sql_template="""
            SELECT 
                DATE_FORMAT(f.virus_scan_date, '%Y-%m') as month,
                COUNT(*) as uploads,
                ROUND(SUM(f.size)/1048576, 2) as total_mb
            FROM files f
            WHERE f.virus_scan_date IS NOT NULL {org_filter}
            GROUP BY DATE_FORMAT(f.virus_scan_date, '%Y-%m')
            ORDER BY month DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Monthly upload trend:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "monthly_signup_trend": AnalyticsTool(
        name="monthly_signup_trend",
        description="User signups grouped by month",
        sql_template="""
            SELECT 
                DATE_FORMAT(u.created_at, '%Y-%m') as month,
                COUNT(*) as signups
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY DATE_FORMAT(u.created_at, '%Y-%m')
            ORDER BY month DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Monthly signup trend:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # =========================================================================
    # EXPANDED TEMPLATES v4.0 - COMPREHENSIVE COVERAGE
    # =========================================================================
    
    # ----- FILE SIZE QUERIES -----
    "smallest_files": AnalyticsTool(
        name="smallest_files",
        description="Smallest files by size",
        sql_template="""
            SELECT 
                f.filename,
                f.size,
                f.content_type,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.size > 0 {org_filter}
            ORDER BY f.size ASC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Smallest files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_larger_than": AnalyticsTool(
        name="files_larger_than",
        description="Files larger than N MB",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.size > {min_size_bytes} {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "min_size_bytes", "limit"],
        response_template="Files larger than specified size:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_smaller_than": AnalyticsTool(
        name="files_smaller_than",
        description="Files smaller than N MB",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.size < {max_size_bytes} AND f.size > 0 {org_filter}
            ORDER BY f.size ASC
            LIMIT {limit}
        """,
        params=["org_id", "max_size_bytes", "limit"],
        response_template="Files smaller than specified size:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- FILE TYPE QUERIES -----
    "video_files": AnalyticsTool(
        name="video_files",
        description="List video files",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.content_type LIKE '%video%' {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Video files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "audio_files": AnalyticsTool(
        name="audio_files",
        description="List audio files",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.content_type LIKE '%audio%' {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Audio files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "document_files": AnalyticsTool(
        name="document_files",
        description="List document files (doc, docx, txt, rtf)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE (f.content_type LIKE '%document%' 
                   OR f.content_type LIKE '%msword%'
                   OR f.content_type LIKE '%text%'
                   OR f.filename LIKE '%.doc%'
                   OR f.filename LIKE '%.txt'
                   OR f.filename LIKE '%.rtf') {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Document files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "spreadsheet_files": AnalyticsTool(
        name="spreadsheet_files",
        description="List spreadsheet files (xls, xlsx, csv)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE (f.content_type LIKE '%spreadsheet%' 
                   OR f.content_type LIKE '%excel%'
                   OR f.content_type LIKE '%csv%'
                   OR f.filename LIKE '%.xls%'
                   OR f.filename LIKE '%.csv') {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Spreadsheet files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "archive_files": AnalyticsTool(
        name="archive_files",
        description="List archive/compressed files (zip, rar, 7z, tar, gz)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE (f.content_type LIKE '%zip%' 
                   OR f.content_type LIKE '%rar%'
                   OR f.content_type LIKE '%compressed%'
                   OR f.content_type LIKE '%archive%'
                   OR f.filename LIKE '%.zip'
                   OR f.filename LIKE '%.rar'
                   OR f.filename LIKE '%.7z'
                   OR f.filename LIKE '%.tar%'
                   OR f.filename LIKE '%.gz') {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Archive files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- USER STATUS QUERIES -----
    "rejected_users": AnalyticsTool(
        name="rejected_users",
        description="List rejected users",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE u.status = 'rejected' {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Rejected users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "suspended_users": AnalyticsTool(
        name="suspended_users",
        description="List suspended/deactivated users",
        sql_template="""
            SELECT u.name, u.email, u.role, u.is_active, u.created_at
            FROM users u
            WHERE u.is_active = 0 {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Suspended/Inactive users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "active_users": AnalyticsTool(
        name="active_users",
        description="List active users",
        sql_template="""
            SELECT u.name, u.email, u.role, u.last_login_at
            FROM users u
            WHERE u.is_active = 1 {org_filter}
            ORDER BY u.last_login_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Active users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- TIME-BASED USER QUERIES -----
    "users_created_today": AnalyticsTool(
        name="users_created_today",
        description="Users created today",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE DATE(u.created_at) = CURDATE() {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users created today:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_created_this_week": AnalyticsTool(
        name="users_created_this_week",
        description="Users created this week",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE u.created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users created this week:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_created_this_month": AnalyticsTool(
        name="users_created_this_month",
        description="Users created this month",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE MONTH(u.created_at) = MONTH(CURDATE()) 
            AND YEAR(u.created_at) = YEAR(CURDATE()) {org_filter}
            ORDER BY u.created_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users created this month:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "oldest_users": AnalyticsTool(
        name="oldest_users",
        description="Oldest user accounts (first to sign up)",
        sql_template="""
            SELECT u.name, u.email, u.role, u.created_at
            FROM users u
            WHERE 1=1 {org_filter}
            ORDER BY u.created_at ASC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Oldest user accounts:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- TIME-BASED FILE QUERIES -----
    "files_uploaded_today": AnalyticsTool(
        name="files_uploaded_today",
        description="Files uploaded today",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE DATE(f.virus_scan_date) = CURDATE() {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files uploaded today:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_uploaded_this_week": AnalyticsTool(
        name="files_uploaded_this_week",
        description="Files uploaded this week",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.virus_scan_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files uploaded this week:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_uploaded_this_month": AnalyticsTool(
        name="files_uploaded_this_month",
        description="Files uploaded this month",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE MONTH(f.virus_scan_date) = MONTH(CURDATE()) 
            AND YEAR(f.virus_scan_date) = YEAR(CURDATE()) {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files uploaded this month:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "oldest_files": AnalyticsTool(
        name="oldest_files",
        description="Oldest files (first uploaded)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by,
                f.virus_scan_date
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.virus_scan_date IS NOT NULL {org_filter}
            ORDER BY f.virus_scan_date ASC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Oldest files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- LOGIN/ACTIVITY QUERIES -----
    "recently_logged_in_users": AnalyticsTool(
        name="recently_logged_in_users",
        description="Users who recently logged in",
        sql_template="""
            SELECT u.name, u.email, u.last_login_at
            FROM users u
            WHERE u.last_login_at IS NOT NULL {org_filter}
            ORDER BY u.last_login_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Recently logged in users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "dormant_users": AnalyticsTool(
        name="dormant_users",
        description="Users who haven't logged in for 30+ days",
        sql_template="""
            SELECT u.name, u.email, u.last_login_at, u.created_at
            FROM users u
            WHERE (u.last_login_at IS NULL OR u.last_login_at < DATE_SUB(CURDATE(), INTERVAL 30 DAY)) {org_filter}
            ORDER BY u.last_login_at ASC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Dormant users (30+ days inactive):\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_logged_in_today": AnalyticsTool(
        name="users_logged_in_today",
        description="Users who logged in today",
        sql_template="""
            SELECT u.name, u.email, u.last_login_at
            FROM users u
            WHERE DATE(u.last_login_at) = CURDATE() {org_filter}
            ORDER BY u.last_login_at DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users logged in today:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- STORAGE QUERIES -----
    "users_with_most_storage": AnalyticsTool(
        name="users_with_most_storage",
        description="Users using the most storage",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                COALESCE(SUM(f.size), 0) as bytes_used,
                COUNT(f.id) as file_count
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email
            HAVING bytes_used > 0
            ORDER BY bytes_used DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users with most storage:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "users_with_least_storage": AnalyticsTool(
        name="users_with_least_storage",
        description="Users using the least storage",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                COALESCE(SUM(f.size), 0) as bytes_used,
                COUNT(f.id) as file_count
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email
            HAVING bytes_used > 0
            ORDER BY bytes_used ASC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Users with least storage:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "storage_by_file_type": AnalyticsTool(
        name="storage_by_file_type",
        description="Storage breakdown by file type",
        sql_template="""
            SELECT 
                f.content_type,
                COUNT(*) as file_count,
                ROUND(SUM(f.size)/1048576, 2) as total_mb,
                ROUND(AVG(f.size)/1024, 2) as avg_kb
            FROM files f
            WHERE 1=1 {org_filter}
            GROUP BY f.content_type
            ORDER BY total_mb DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Storage by file type:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- VIRUS/SECURITY QUERIES -----
    "files_pending_scan": AnalyticsTool(
        name="files_pending_scan",
        description="Files that haven't been scanned yet",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE (f.virus_scan_status IS NULL OR f.virus_scan_status = 'pending') {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files pending scan:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "virus_detected_count": AnalyticsTool(
        name="virus_detected_count",
        description="Count of files with virus detected",
        sql_template="""
            SELECT 
                f.virus_scan_status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM files), 2) as percentage
            FROM files f
            WHERE f.virus_scan_status IS NOT NULL {org_filter}
            GROUP BY f.virus_scan_status
        """,
        params=["org_id"],
        response_template="Virus scan results:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "infected_files": AnalyticsTool(
        name="infected_files",
        description="Files that have virus detected",
        sql_template="""
            SELECT 
                f.filename,
                f.virus_scan_status,
                f.quarantine_reason,
                u.name as uploaded_by,
                f.virus_scan_date
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE (f.virus_scan_status = 'infected' OR f.is_quarantined = 1) {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Infected files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "clean_files": AnalyticsTool(
        name="clean_files",
        description="Files that passed virus scan (clean)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.virus_scan_status = 'clean' AND (f.is_quarantined = 0 OR f.is_quarantined IS NULL) {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Clean files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- AGGREGATE/STATISTICS QUERIES -----
    "average_files_per_user": AnalyticsTool(
        name="average_files_per_user",
        description="Average number of files per user",
        sql_template="""
            SELECT 
                ROUND(AVG(file_count), 2) as avg_files_per_user,
                MAX(file_count) as max_files,
                MIN(file_count) as min_files
            FROM (
                SELECT u.id, COUNT(f.id) as file_count
                FROM users u
                LEFT JOIN files f ON u.id = f.user_id
                WHERE 1=1 {org_filter}
                GROUP BY u.id
            ) as user_files
        """,
        params=["org_id"],
        response_template="Average files per user: **{avg_files_per_user}** (min: {min_files}, max: {max_files})",
        requires_org_filter=True
    ),
    
    "average_storage_per_user": AnalyticsTool(
        name="average_storage_per_user",
        description="Average storage per user",
        sql_template="""
            SELECT 
                ROUND(AVG(bytes_used)/1048576, 2) as avg_mb_per_user,
                ROUND(MAX(bytes_used)/1048576, 2) as max_mb,
                ROUND(MIN(bytes_used)/1024, 2) as min_kb
            FROM (
                SELECT u.id, COALESCE(SUM(f.size), 0) as bytes_used
                FROM users u
                LEFT JOIN files f ON u.id = f.user_id
                WHERE 1=1 {org_filter}
                GROUP BY u.id
            ) as user_storage
        """,
        params=["org_id"],
        response_template="Average storage per user: **{avg_mb_per_user} MB** (max: {max_mb} MB)",
        requires_org_filter=True
    ),
    
    "files_per_folder": AnalyticsTool(
        name="files_per_folder",
        description="Files count per folder",
        sql_template="""
            SELECT 
                fo.name as folder_name,
                COUNT(f.id) as file_count,
                ROUND(COALESCE(SUM(f.size), 0)/1048576, 2) as total_mb
            FROM folders fo
            LEFT JOIN files f ON fo.id = f.folder_id
            WHERE 1=1 {org_filter}
            GROUP BY fo.id, fo.name
            ORDER BY file_count DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files per folder:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "folders_with_most_files": AnalyticsTool(
        name="folders_with_most_files",
        description="Folders with the most files",
        sql_template="""
            SELECT 
                fo.name as folder_name,
                COUNT(f.id) as file_count,
                ROUND(COALESCE(SUM(f.size), 0)/1048576, 2) as total_mb
            FROM folders fo
            LEFT JOIN files f ON fo.id = f.folder_id
            WHERE 1=1 {org_filter}
            GROUP BY fo.id, fo.name
            HAVING file_count > 0
            ORDER BY file_count DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Folders with most files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- ROLE-BASED QUERIES -----
    "user_role_count": AnalyticsTool(
        name="user_role_count",
        description="Count users per role",
        sql_template="""
            SELECT 
                u.role,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM users), 2) as percentage
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY u.role
            ORDER BY count DESC
        """,
        params=["org_id"],
        response_template="Users by role:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "regular_users": AnalyticsTool(
        name="regular_users",
        description="List regular (non-admin) users",
        sql_template="""
            SELECT u.name, u.email, u.status, u.created_at
            FROM users u
            WHERE u.role = 'user' {org_filter}
            ORDER BY u.name
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Regular users:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "super_admins": AnalyticsTool(
        name="super_admins",
        description="List super admin users",
        sql_template="""
            SELECT u.name, u.email, u.created_at, u.last_login_at
            FROM users u
            WHERE u.role = 'super_admin'
            ORDER BY u.name
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Super admins:\n{formatted_data}",
        requires_org_filter=False
    ),
    
    "org_admins": AnalyticsTool(
        name="org_admins",
        description="List organization admin users",
        sql_template="""
            SELECT u.name, u.email, o.name as organization, u.created_at
            FROM users u
            LEFT JOIN organizations o ON u.organization_id = o.id
            WHERE u.role = 'org_admin' {org_filter}
            ORDER BY u.name
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Organization admins:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- ORGANIZATION QUERIES -----
    "inactive_organizations": AnalyticsTool(
        name="inactive_organizations",
        description="Inactive organizations",
        sql_template="""
            SELECT 
                o.name,
                o.slug,
                o.plan,
                o.created_at
            FROM organizations o
            WHERE o.is_active = 0
            ORDER BY o.created_at DESC
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Inactive organizations:\n{formatted_data}",
        requires_org_filter=False
    ),
    
    "newest_organizations": AnalyticsTool(
        name="newest_organizations",
        description="Most recently created organizations",
        sql_template="""
            SELECT 
                o.name,
                o.slug,
                o.plan,
                o.created_at,
                (SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id) as user_count
            FROM organizations o
            WHERE o.is_active = 1
            ORDER BY o.created_at DESC
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Newest organizations:\n{formatted_data}",
        requires_org_filter=False
    ),
    
    "organizations_by_plan": AnalyticsTool(
        name="organizations_by_plan",
        description="Organizations grouped by plan type",
        sql_template="""
            SELECT 
                o.plan,
                COUNT(*) as org_count,
                SUM((SELECT COUNT(*) FROM users u WHERE u.organization_id = o.id)) as total_users
            FROM organizations o
            WHERE o.is_active = 1
            GROUP BY o.plan
            ORDER BY org_count DESC
        """,
        params=[],
        response_template="Organizations by plan:\n{formatted_data}",
        requires_org_filter=False
    ),
    
    "users_per_organization": AnalyticsTool(
        name="users_per_organization",
        description="Count of users per organization",
        sql_template="""
            SELECT 
                o.name as organization,
                o.plan,
                COUNT(u.id) as user_count
            FROM organizations o
            LEFT JOIN users u ON o.id = u.organization_id
            WHERE o.is_active = 1
            GROUP BY o.id, o.name, o.plan
            ORDER BY user_count DESC
            LIMIT {limit}
        """,
        params=["limit"],
        response_template="Users per organization:\n{formatted_data}",
        requires_org_filter=False
    ),
    
    # ----- TREND QUERIES -----
    "weekly_upload_trend": AnalyticsTool(
        name="weekly_upload_trend",
        description="File uploads grouped by week",
        sql_template="""
            SELECT 
                YEARWEEK(f.virus_scan_date) as year_week,
                COUNT(*) as uploads,
                ROUND(SUM(f.size)/1048576, 2) as total_mb
            FROM files f
            WHERE f.virus_scan_date IS NOT NULL {org_filter}
            GROUP BY YEARWEEK(f.virus_scan_date)
            ORDER BY year_week DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Weekly upload trend:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "yearly_upload_trend": AnalyticsTool(
        name="yearly_upload_trend",
        description="File uploads grouped by year",
        sql_template="""
            SELECT 
                YEAR(f.virus_scan_date) as year,
                COUNT(*) as uploads,
                ROUND(SUM(f.size)/1048576, 2) as total_mb
            FROM files f
            WHERE f.virus_scan_date IS NOT NULL {org_filter}
            GROUP BY YEAR(f.virus_scan_date)
            ORDER BY year DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Yearly upload trend:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "weekly_signup_trend": AnalyticsTool(
        name="weekly_signup_trend",
        description="User signups grouped by week",
        sql_template="""
            SELECT 
                YEARWEEK(u.created_at) as year_week,
                COUNT(*) as signups
            FROM users u
            WHERE 1=1 {org_filter}
            GROUP BY YEARWEEK(u.created_at)
            ORDER BY year_week DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Weekly signup trend:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- COMPARATIVE QUERIES -----
    "uploads_vs_users": AnalyticsTool(
        name="uploads_vs_users",
        description="Compare total uploads to total users",
        sql_template="""
            SELECT 
                (SELECT COUNT(*) FROM users WHERE 1=1 {org_filter}) as total_users,
                (SELECT COUNT(*) FROM files WHERE 1=1 {org_filter}) as total_files,
                (SELECT COUNT(DISTINCT user_id) FROM files WHERE 1=1 {org_filter}) as users_with_uploads,
                ROUND((SELECT COUNT(DISTINCT user_id) FROM files WHERE 1=1 {org_filter}) * 100.0 / 
                      NULLIF((SELECT COUNT(*) FROM users WHERE 1=1 {org_filter}), 0), 2) as upload_rate_pct
        """,
        params=["org_id"],
        response_template="Upload summary: **{total_files}** files by **{users_with_uploads}** users out of **{total_users}** total ({upload_rate_pct}% upload rate)",
        requires_org_filter=True
    ),
    
    "approved_vs_pending": AnalyticsTool(
        name="approved_vs_pending",
        description="Compare approved vs pending users",
        sql_template="""
            SELECT 
                u.status,
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM users), 2) as percentage
            FROM users u
            WHERE u.status IN ('approved', 'pending') {org_filter}
            GROUP BY u.status
        """,
        params=["org_id"],
        response_template="User approval status:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- SEARCH/LOOKUP QUERIES -----
    "user_by_email": AnalyticsTool(
        name="user_by_email",
        description="Find user by email address",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                u.role,
                u.status,
                u.is_active,
                u.created_at,
                u.last_login_at,
                (SELECT COUNT(*) FROM files f WHERE f.user_id = u.id) as file_count
            FROM users u
            WHERE u.email LIKE '%{email}%' {org_filter}
            LIMIT {limit}
        """,
        params=["email", "org_id", "limit"],
        response_template="User details:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "user_by_name": AnalyticsTool(
        name="user_by_name",
        description="Find user by name",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                u.role,
                u.status,
                u.is_active,
                u.created_at,
                (SELECT COUNT(*) FROM files f WHERE f.user_id = u.id) as file_count
            FROM users u
            WHERE u.name LIKE '%{name}%' {org_filter}
            LIMIT {limit}
        """,
        params=["name", "org_id", "limit"],
        response_template="User details:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "files_by_user": AnalyticsTool(
        name="files_by_user",
        description="Files uploaded by a specific user (by name or email)",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                f.content_type,
                f.virus_scan_date
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE (u.name LIKE '%{user_search}%' OR u.email LIKE '%{user_search}%') {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["user_search", "org_id", "limit"],
        response_template="Files by user:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "file_by_name": AnalyticsTool(
        name="file_by_name",
        description="Find file by filename",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                f.content_type,
                u.name as uploaded_by,
                f.virus_scan_status,
                f.virus_scan_date
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.filename LIKE '%{filename}%' {org_filter}
            ORDER BY f.virus_scan_date DESC
            LIMIT {limit}
        """,
        params=["filename", "org_id", "limit"],
        response_template="File details:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- COUNT QUERIES -----
    "pending_user_count": AnalyticsTool(
        name="pending_user_count",
        description="Count of pending users",
        sql_template="""
            SELECT COUNT(*) as pending_count
            FROM users u
            WHERE u.status = 'pending' {org_filter}
        """,
        params=["org_id"],
        response_template="There are **{pending_count}** pending users.",
        requires_org_filter=True
    ),
    
    "approved_user_count": AnalyticsTool(
        name="approved_user_count",
        description="Count of approved users",
        sql_template="""
            SELECT COUNT(*) as approved_count
            FROM users u
            WHERE u.status = 'approved' {org_filter}
        """,
        params=["org_id"],
        response_template="There are **{approved_count}** approved users.",
        requires_org_filter=True
    ),
    
    "admin_count": AnalyticsTool(
        name="admin_count",
        description="Count of admin users",
        sql_template="""
            SELECT COUNT(*) as admin_count
            FROM users u
            WHERE u.role IN ('super_admin', 'org_admin') {org_filter}
        """,
        params=["org_id"],
        response_template="There are **{admin_count}** admin users.",
        requires_org_filter=True
    ),
    
    "quarantined_file_count": AnalyticsTool(
        name="quarantined_file_count",
        description="Count of quarantined files",
        sql_template="""
            SELECT COUNT(*) as quarantined_count
            FROM files f
            WHERE f.is_quarantined = 1 {org_filter}
        """,
        params=["org_id"],
        response_template="There are **{quarantined_count}** quarantined files.",
        requires_org_filter=True
    ),
    
    "clean_file_count": AnalyticsTool(
        name="clean_file_count",
        description="Count of clean (non-quarantined) files",
        sql_template="""
            SELECT COUNT(*) as clean_count
            FROM files f
            WHERE (f.is_quarantined = 0 OR f.is_quarantined IS NULL) 
            AND f.virus_scan_status = 'clean' {org_filter}
        """,
        params=["org_id"],
        response_template="There are **{clean_count}** clean files.",
        requires_org_filter=True
    ),
    
    # ----- TOP N QUERIES -----
    "top_n_files_by_size": AnalyticsTool(
        name="top_n_files_by_size",
        description="Top N largest files",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1048576, 2) as size_mb,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE 1=1 {org_filter}
            ORDER BY f.size DESC
            LIMIT {limit}
        """,
        params=["org_id"],
        response_template="Top {limit} largest files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "bottom_n_files_by_size": AnalyticsTool(
        name="bottom_n_files_by_size",
        description="Bottom N smallest files",
        sql_template="""
            SELECT 
                f.filename,
                ROUND(f.size/1024, 2) as size_kb,
                u.name as uploaded_by
            FROM files f
            LEFT JOIN users u ON f.user_id = u.id
            WHERE f.size > 0 {org_filter}
            ORDER BY f.size ASC
            LIMIT {n}
        """,
        params=["org_id", "n"],
        response_template="Bottom {n} smallest files:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "top_n_users_by_storage": AnalyticsTool(
        name="top_n_users_by_storage",
        description="Top N users by storage usage",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                ROUND(COALESCE(SUM(f.size), 0)/1048576, 2) as storage_mb,
                COUNT(f.id) as file_count
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email
            ORDER BY storage_mb DESC
            LIMIT {n}
        """,
        params=["org_id", "n"],
        response_template="Top {n} users by storage:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "top_n_users_by_files": AnalyticsTool(
        name="top_n_users_by_files",
        description="Top N users by file count",
        sql_template="""
            SELECT 
                u.name,
                u.email,
                COUNT(f.id) as file_count
            FROM users u
            LEFT JOIN files f ON u.id = f.user_id
            WHERE 1=1 {org_filter}
            GROUP BY u.id, u.name, u.email
            ORDER BY file_count DESC
            LIMIT {n}
        """,
        params=["org_id", "n"],
        response_template="Top {n} users by file count:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- DAILY COUNTS -----
    "uploads_today_count": AnalyticsTool(
        name="uploads_today_count",
        description="Count of files uploaded today",
        sql_template="""
            SELECT COUNT(*) as today_uploads
            FROM files f
            WHERE DATE(f.virus_scan_date) = CURDATE() {org_filter}
        """,
        params=["org_id"],
        response_template="**{today_uploads}** files uploaded today.",
        requires_org_filter=True
    ),
    
    "signups_today_count": AnalyticsTool(
        name="signups_today_count",
        description="Count of users signed up today",
        sql_template="""
            SELECT COUNT(*) as today_signups
            FROM users u
            WHERE DATE(u.created_at) = CURDATE() {org_filter}
        """,
        params=["org_id"],
        response_template="**{today_signups}** users signed up today.",
        requires_org_filter=True
    ),
    
    "logins_today_count": AnalyticsTool(
        name="logins_today_count",
        description="Count of users logged in today",
        sql_template="""
            SELECT COUNT(*) as today_logins
            FROM users u
            WHERE DATE(u.last_login_at) = CURDATE() {org_filter}
        """,
        params=["org_id"],
        response_template="**{today_logins}** users logged in today.",
        requires_org_filter=True
    ),
    
    # ----- EXTENSION-BASED FILE QUERIES -----
    "files_by_extension": AnalyticsTool(
        name="files_by_extension",
        description="Files grouped by extension",
        sql_template="""
            SELECT 
                SUBSTRING_INDEX(f.filename, '.', -1) as extension,
                COUNT(*) as count,
                ROUND(SUM(f.size)/1048576, 2) as total_mb
            FROM files f
            WHERE f.filename LIKE '%.%' {org_filter}
            GROUP BY SUBSTRING_INDEX(f.filename, '.', -1)
            ORDER BY count DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Files by extension:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    "most_common_file_types": AnalyticsTool(
        name="most_common_file_types",
        description="Most common file types/extensions",
        sql_template="""
            SELECT 
                f.content_type,
                COUNT(*) as count,
                ROUND(SUM(f.size)/1048576, 2) as total_mb
            FROM files f
            WHERE 1=1 {org_filter}
            GROUP BY f.content_type
            ORDER BY count DESC
            LIMIT {limit}
        """,
        params=["org_id", "limit"],
        response_template="Most common file types:\n{formatted_data}",
        requires_org_filter=True
    ),
    
    # ----- DASHBOARD/SUMMARY QUERIES -----
    "system_summary": AnalyticsTool(
        name="system_summary",
        description="Overall system summary statistics",
        sql_template="""
            SELECT 
                (SELECT COUNT(*) FROM users) as total_users,
                (SELECT COUNT(*) FROM files) as total_files,
                (SELECT COUNT(*) FROM organizations WHERE is_active = 1) as total_orgs,
                (SELECT COUNT(*) FROM folders) as total_folders,
                (SELECT ROUND(SUM(size)/1073741824, 2) FROM files) as total_storage_gb
        """,
        params=[],
        response_template="System Summary:\n• **{total_users}** users\n• **{total_files}** files\n• **{total_orgs}** organizations\n• **{total_folders}** folders\n• **{total_storage_gb} GB** storage used",
        requires_org_filter=False
    ),
    
    "org_summary": AnalyticsTool(
        name="org_summary",
        description="Organization-specific summary statistics",
        sql_template="""
            SELECT 
                (SELECT COUNT(*) FROM users u WHERE 1=1 {org_filter}) as total_users,
                (SELECT COUNT(*) FROM files f WHERE 1=1 {org_filter}) as total_files,
                (SELECT COUNT(*) FROM folders fo WHERE 1=1 {org_filter}) as total_folders,
                (SELECT ROUND(COALESCE(SUM(size), 0)/1048576, 2) FROM files f WHERE 1=1 {org_filter}) as storage_mb,
                (SELECT COUNT(*) FROM users u WHERE u.status = 'pending' {org_filter}) as pending_users
        """,
        params=["org_id"],
        response_template="Organization Summary:\n• **{total_users}** users ({pending_users} pending)\n• **{total_files}** files\n• **{total_folders}** folders\n• **{storage_mb} MB** storage used",
        requires_org_filter=True
    ),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_bytes(bytes_val: int) -> str:
    """Format bytes to human readable string."""
    if bytes_val is None:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_val < 1024:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024
    return f"{bytes_val:.2f} PB"


def format_data_as_list(rows: List[Dict], max_items: int = 10) -> str:
    """Format query results as a bulleted list."""
    if not rows:
        return "No data found."
    
    lines = []
    for i, row in enumerate(rows[:max_items]):
        parts = []
        for key, value in row.items():
            if key in ['bytes_used', 'total_bytes', 'total_size', 'size', 'bytes_uploaded', 'total_storage']:
                parts.append(f"{format_bytes(value or 0)}")
            elif key in ['created_at', 'date']:
                if value:
                    parts.append(str(value)[:10])
            elif key not in ['id']:
                parts.append(str(value) if value else 'N/A')
        lines.append(f"• {' | '.join(parts)}")
    
    if len(rows) > max_items:
        lines.append(f"...and {len(rows) - max_items} more")
    
    return "\n".join(lines)


def format_data_as_table(rows: List[Dict], columns: List[str] = None) -> str:
    """Format query results as a markdown table."""
    if not rows:
        return "No data found."
    
    if columns is None:
        columns = list(rows[0].keys())
    
    # Header
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    
    # Rows
    data_rows = []
    for row in rows[:20]:
        values = []
        for col in columns:
            val = row.get(col, "")
            if col in ['bytes_used', 'total_bytes', 'total_size', 'size']:
                val = format_bytes(val or 0)
            elif col in ['created_at', 'date']:
                val = str(val)[:10] if val else ""
            else:
                val = str(val) if val else ""
            values.append(val)
        data_rows.append("| " + " | ".join(values) + " |")
    
    return "\n".join([header, separator] + data_rows)


def get_tool_names() -> List[str]:
    """Get list of all tool names."""
    return list(ANALYTICS_TOOLS.keys())


def get_tool(name: str) -> Optional[AnalyticsTool]:
    """Get a tool by name."""
    return ANALYTICS_TOOLS.get(name)
