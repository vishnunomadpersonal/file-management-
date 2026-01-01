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
