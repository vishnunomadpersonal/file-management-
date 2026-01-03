"""
DSPy Prompt Optimizer for Text-to-SQL
======================================
Uses Stanford's DSPy framework to automatically optimize prompts
for better SQL generation accuracy.

Instead of manual rules, DSPy learns optimal prompts from examples.
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import DSPy
try:
    import dspy
    from dspy.teleprompt import BootstrapFewShot, BootstrapFewShotWithRandomSearch
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False
    logger.warning("DSPy not installed. Run: pip install dspy-ai")


# =============================================================================
# TRAINING DATA - Examples for DSPy to learn from
# =============================================================================

TRAINING_EXAMPLES = [
    # ==========================================================================
    # CATEGORY 1: BASIC COUNTS (Single table aggregates)
    # ==========================================================================
    {"question": "how many users are there", "sql": "SELECT COUNT(*) as user_count FROM users LIMIT 50"},
    {"question": "total user count", "sql": "SELECT COUNT(*) as user_count FROM users LIMIT 50"},
    {"question": "count all users", "sql": "SELECT COUNT(*) as user_count FROM users LIMIT 50"},
    {"question": "number of users", "sql": "SELECT COUNT(*) as user_count FROM users LIMIT 50"},
    {"question": "how many files", "sql": "SELECT COUNT(*) as file_count FROM files LIMIT 50"},
    {"question": "total files in system", "sql": "SELECT COUNT(*) as file_count FROM files LIMIT 50"},
    {"question": "how many organizations", "sql": "SELECT COUNT(*) as org_count FROM organizations LIMIT 50"},
    {"question": "count organizations", "sql": "SELECT COUNT(*) as org_count FROM organizations LIMIT 50"},
    {"question": "how many folders", "sql": "SELECT COUNT(*) as folder_count FROM folders LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 2: BASIC LISTS (Single table selects)
    # ==========================================================================
    {"question": "list all users", "sql": "SELECT u.name, u.email, u.role, u.status FROM users u LIMIT 50"},
    {"question": "show me all users", "sql": "SELECT u.name, u.email, u.role, u.status FROM users u LIMIT 50"},
    {"question": "show all files", "sql": "SELECT f.filename, f.content_type, ROUND(f.size/1024,2) as size_kb, f.virus_scan_date FROM files f LIMIT 50"},
    {"question": "list all organizations", "sql": "SELECT o.name, o.email, o.plan, o.is_active FROM organizations o LIMIT 50"},
    {"question": "show all folders", "sql": "SELECT fo.name, fo.path FROM folders fo LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 3: STATUS-BASED FILTERS (Users)
    # ==========================================================================
    {"question": "approved users", "sql": "SELECT u.name, u.email, u.role, o.name as org_name FROM users u LEFT JOIN organizations o ON u.organization_id = o.id WHERE u.status = 'approved' LIMIT 50"},
    {"question": "pending users", "sql": "SELECT u.name, u.email, u.role, o.name as org_name FROM users u LEFT JOIN organizations o ON u.organization_id = o.id WHERE u.status = 'pending' LIMIT 50"},
    {"question": "rejected users", "sql": "SELECT u.name, u.email, u.role, o.name as org_name FROM users u LEFT JOIN organizations o ON u.organization_id = o.id WHERE u.status = 'rejected' LIMIT 50"},
    {"question": "active users", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.is_active = 1 LIMIT 50"},
    {"question": "inactive users", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.is_active = 0 LIMIT 50"},
    {"question": "verified users", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.is_verified = 1 LIMIT 50"},
    {"question": "unverified users", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.is_verified = 0 LIMIT 50"},
    {"question": "locked users", "sql": "SELECT u.name, u.email, u.locked_until FROM users u WHERE u.locked_until IS NOT NULL AND u.locked_until > NOW() LIMIT 50"},
    {"question": "users by status", "sql": "SELECT u.status, COUNT(*) as count FROM users u GROUP BY u.status LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 4: ROLE-BASED FILTERS
    # ==========================================================================
    {"question": "all admins", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.role IN ('super_admin', 'org_admin') LIMIT 50"},
    {"question": "super admins", "sql": "SELECT u.name, u.email FROM users u WHERE u.role = 'super_admin' LIMIT 50"},
    {"question": "org admins", "sql": "SELECT u.name, u.email, o.name as org_name FROM users u LEFT JOIN organizations o ON u.organization_id = o.id WHERE u.role = 'org_admin' LIMIT 50"},
    {"question": "regular users", "sql": "SELECT u.name, u.email FROM users u WHERE u.role = 'user' LIMIT 50"},
    {"question": "managers", "sql": "SELECT u.name, u.email FROM users u WHERE u.role = 'manager' LIMIT 50"},
    {"question": "users by role", "sql": "SELECT u.role, COUNT(*) as count FROM users u GROUP BY u.role LIMIT 50"},
    {"question": "how many admins", "sql": "SELECT COUNT(*) as admin_count FROM users u WHERE u.role IN ('super_admin', 'org_admin') LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 5: APPROVAL TRACKING (Complex joins)
    # ==========================================================================
    {"question": "who approved user20@gmail.com", "sql": "SELECT u.name, u.email, u.status, approver.name as approved_by, approver.email as approver_email, u.approved_at FROM users u LEFT JOIN users approver ON u.approved_by = approver.id WHERE u.email = 'user20@gmail.com' LIMIT 50"},
    {"question": "who approved each user", "sql": "SELECT u.name, u.email, approver.name as approved_by, u.approved_at FROM users u LEFT JOIN users approver ON u.approved_by = approver.id WHERE u.status = 'approved' AND u.approved_by IS NOT NULL LIMIT 50"},
    {"question": "users approved by Super Admin", "sql": "SELECT u.name, u.email, u.approved_at FROM users u LEFT JOIN users approver ON u.approved_by = approver.id WHERE approver.name LIKE '%Super Admin%' LIMIT 50"},
    {"question": "count of users approved by each admin", "sql": "SELECT approver.name as approved_by, COUNT(u.id) as users_approved FROM users u JOIN users approver ON u.approved_by = approver.id GROUP BY approver.id, approver.name LIMIT 50"},
    {"question": "users waiting for approval", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE u.status = 'pending' ORDER BY u.created_at ASC LIMIT 50"},
    {"question": "recently approved users", "sql": "SELECT u.name, u.email, approver.name as approved_by, u.approved_at FROM users u LEFT JOIN users approver ON u.approved_by = approver.id WHERE u.status = 'approved' ORDER BY u.approved_at DESC LIMIT 50"},
    {"question": "approval rate", "sql": "SELECT u.status, COUNT(*) as count, ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM users), 2) as percentage FROM users u GROUP BY u.status LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 6: FILE QUERIES (Size, type, status)
    # ==========================================================================
    {"question": "largest files", "sql": "SELECT f.filename, ROUND(f.size/1048576,2) as size_mb, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id ORDER BY f.size DESC LIMIT 50"},
    {"question": "smallest files", "sql": "SELECT f.filename, f.size as size_bytes, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id ORDER BY f.size ASC LIMIT 50"},
    {"question": "files larger than 1MB", "sql": "SELECT f.filename, ROUND(f.size/1048576,2) as size_mb FROM files f WHERE f.size > 1048576 LIMIT 50"},
    {"question": "files smaller than 100KB", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb FROM files f WHERE f.size < 102400 LIMIT 50"},
    {"question": "total storage used", "sql": "SELECT ROUND(SUM(f.size)/1048576, 2) as total_mb FROM files f LIMIT 50"},
    {"question": "average file size", "sql": "SELECT ROUND(AVG(f.size)/1024, 2) as avg_size_kb FROM files f LIMIT 50"},
    {"question": "average file size in mb", "sql": "SELECT ROUND(AVG(f.size)/1048576, 2) as avg_size_mb FROM files f LIMIT 50"},
    {"question": "pdf files", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE f.content_type LIKE '%pdf%' LIMIT 50"},
    {"question": "image files", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE f.content_type LIKE '%image%' LIMIT 50"},
    {"question": "document files", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb FROM files f WHERE f.content_type LIKE '%document%' OR f.content_type LIKE '%word%' OR f.content_type LIKE '%text%' LIMIT 50"},
    {"question": "quarantined files", "sql": "SELECT f.filename, f.quarantine_reason, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE f.is_quarantined = 1 LIMIT 50"},
    {"question": "clean files", "sql": "SELECT f.filename, f.virus_scan_status FROM files f WHERE f.is_quarantined = 0 OR f.is_quarantined IS NULL LIMIT 50"},
    {"question": "files pending virus scan", "sql": "SELECT f.filename, f.virus_scan_status FROM files f WHERE f.virus_scan_status = 'pending' OR f.virus_scan_status IS NULL LIMIT 50"},
    {"question": "files by type", "sql": "SELECT f.content_type, COUNT(*) as count FROM files f GROUP BY f.content_type LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 7: USER-FILE JOINS (Who uploaded what)
    # ==========================================================================
    {"question": "files uploaded by Super Admin", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id WHERE u.name LIKE '%Super Admin%' LIMIT 50"},
    {"question": "who uploaded the most files", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name ORDER BY file_count DESC LIMIT 50"},
    {"question": "who uploaded the least files", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name ORDER BY file_count ASC LIMIT 50"},
    {"question": "users with more than 5 files", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name HAVING COUNT(f.id) > 5 LIMIT 50"},
    {"question": "users with more than 10 files", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name HAVING COUNT(f.id) > 10 LIMIT 50"},
    {"question": "users with less than 3 files", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name HAVING COUNT(f.id) < 3 LIMIT 50"},
    {"question": "users who have not uploaded any files", "sql": "SELECT u.name, u.email FROM users u LEFT JOIN files f ON u.id = f.user_id WHERE f.id IS NULL LIMIT 50"},
    {"question": "users without files", "sql": "SELECT u.name, u.email FROM users u LEFT JOIN files f ON u.id = f.user_id WHERE f.id IS NULL LIMIT 50"},
    {"question": "storage used by each user", "sql": "SELECT u.name, ROUND(SUM(f.size)/1048576, 2) as total_mb FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name ORDER BY total_mb DESC LIMIT 50"},
    {"question": "users with more than 1MB storage", "sql": "SELECT u.name, ROUND(SUM(f.size)/1048576, 2) as total_mb FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name HAVING SUM(f.size) > 1048576 LIMIT 50"},
    {"question": "file count per user", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM users u LEFT JOIN files f ON u.id = f.user_id GROUP BY u.id, u.name LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 8: ORGANIZATION QUERIES
    # ==========================================================================
    {"question": "users in organization vedirobotics", "sql": "SELECT u.name, u.email, u.role FROM users u JOIN organizations o ON u.organization_id = o.id WHERE o.name LIKE '%vedirobotics%' LIMIT 50"},
    {"question": "users in organization mycompany", "sql": "SELECT u.name, u.email, u.role FROM users u JOIN organizations o ON u.organization_id = o.id WHERE o.name LIKE '%mycompany%' LIMIT 50"},
    {"question": "users per organization", "sql": "SELECT o.name as org_name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name LIMIT 50"},
    {"question": "organizations with more than 2 users", "sql": "SELECT o.name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name HAVING COUNT(u.id) > 2 LIMIT 50"},
    {"question": "organizations with more than 5 users", "sql": "SELECT o.name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name HAVING COUNT(u.id) > 5 LIMIT 50"},
    {"question": "organizations with no users", "sql": "SELECT o.name FROM organizations o LEFT JOIN users u ON o.id = u.organization_id WHERE u.id IS NULL LIMIT 50"},
    {"question": "empty organizations", "sql": "SELECT o.name FROM organizations o LEFT JOIN users u ON o.id = u.organization_id WHERE u.id IS NULL LIMIT 50"},
    {"question": "which org has the most users", "sql": "SELECT o.name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name ORDER BY user_count DESC LIMIT 1"},
    {"question": "largest organization", "sql": "SELECT o.name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name ORDER BY user_count DESC LIMIT 1"},
    {"question": "smallest organization", "sql": "SELECT o.name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name ORDER BY user_count ASC LIMIT 1"},
    {"question": "active organizations", "sql": "SELECT o.name, o.plan FROM organizations o WHERE o.is_active = 1 LIMIT 50"},
    {"question": "inactive organizations", "sql": "SELECT o.name, o.plan FROM organizations o WHERE o.is_active = 0 LIMIT 50"},
    {"question": "verified organizations", "sql": "SELECT o.name, o.plan FROM organizations o WHERE o.is_verified = 1 LIMIT 50"},
    {"question": "organizations by plan", "sql": "SELECT o.plan, COUNT(*) as count FROM organizations o GROUP BY o.plan LIMIT 50"},
    {"question": "enterprise organizations", "sql": "SELECT o.name FROM organizations o WHERE o.plan = 'enterprise' LIMIT 50"},
    {"question": "free plan organizations", "sql": "SELECT o.name FROM organizations o WHERE o.plan = 'free' LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 9: ORGANIZATION-FILE QUERIES
    # ==========================================================================
    {"question": "files per organization", "sql": "SELECT o.name as org_name, COUNT(f.id) as file_count FROM organizations o LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name LIMIT 50"},
    {"question": "storage per organization", "sql": "SELECT o.name, ROUND(SUM(f.size)/1048576, 2) as storage_mb FROM organizations o LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name LIMIT 50"},
    {"question": "organizations with no files", "sql": "SELECT o.name FROM organizations o LEFT JOIN files f ON o.id = f.organization_id WHERE f.id IS NULL LIMIT 50"},
    {"question": "organizations with more than 10 files", "sql": "SELECT o.name, COUNT(f.id) as file_count FROM organizations o LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name HAVING COUNT(f.id) > 10 LIMIT 50"},
    {"question": "organizations exceeding storage quota", "sql": "SELECT o.name, o.storage_used_bytes, o.storage_quota_bytes FROM organizations o WHERE o.storage_used_bytes > o.storage_quota_bytes LIMIT 50"},
    {"question": "storage quota usage", "sql": "SELECT o.name, ROUND(o.storage_used_bytes/1048576, 2) as used_mb, ROUND(o.storage_quota_bytes/1048576, 2) as quota_mb, ROUND(o.storage_used_bytes * 100.0 / o.storage_quota_bytes, 2) as percent_used FROM organizations o WHERE o.storage_quota_bytes > 0 LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 10: TEMPORAL QUERIES (Date-based)
    # ==========================================================================
    {"question": "users who joined today", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE DATE(u.created_at) = CURDATE() LIMIT 50"},
    {"question": "users who joined yesterday", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE DATE(u.created_at) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) LIMIT 50"},
    {"question": "users who joined this week", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE u.created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) LIMIT 50"},
    {"question": "users who joined this month", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE MONTH(u.created_at) = MONTH(CURDATE()) AND YEAR(u.created_at) = YEAR(CURDATE()) LIMIT 50"},
    {"question": "users who joined last month", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE u.created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) AND u.created_at < CURDATE() LIMIT 50"},
    {"question": "users created in 2025", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE YEAR(u.created_at) = 2025 LIMIT 50"},
    {"question": "users created before 2025", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE YEAR(u.created_at) < 2025 LIMIT 50"},
    {"question": "files uploaded today", "sql": "SELECT f.filename, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE DATE(f.virus_scan_date) = CURDATE() LIMIT 50"},
    {"question": "files uploaded yesterday", "sql": "SELECT f.filename, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE DATE(f.virus_scan_date) = DATE_SUB(CURDATE(), INTERVAL 1 DAY) LIMIT 50"},
    {"question": "files uploaded this week", "sql": "SELECT f.filename, u.name as uploader, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id WHERE f.virus_scan_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) LIMIT 50"},
    {"question": "files uploaded this month", "sql": "SELECT f.filename, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE MONTH(f.virus_scan_date) = MONTH(CURDATE()) AND YEAR(f.virus_scan_date) = YEAR(CURDATE()) LIMIT 50"},
    {"question": "recent uploads", "sql": "SELECT f.filename, u.name as uploader, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id ORDER BY f.virus_scan_date DESC LIMIT 50"},
    {"question": "oldest files", "sql": "SELECT f.filename, u.name as uploader, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id ORDER BY f.virus_scan_date ASC LIMIT 50"},
    {"question": "files uploaded between December 2025 and January 2026", "sql": "SELECT f.filename, u.name as uploader, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id WHERE f.virus_scan_date BETWEEN '2025-12-01' AND '2026-01-31' LIMIT 50"},
    {"question": "users who logged in today", "sql": "SELECT u.name, u.email, u.last_login_at FROM users u WHERE DATE(u.last_login_at) = CURDATE() LIMIT 50"},
    {"question": "users who logged in this week", "sql": "SELECT u.name, u.email, u.last_login_at FROM users u WHERE u.last_login_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) LIMIT 50"},
    {"question": "users who never logged in", "sql": "SELECT u.name, u.email FROM users u WHERE u.last_login_at IS NULL LIMIT 50"},
    {"question": "users inactive for 30 days", "sql": "SELECT u.name, u.email, u.last_login_at FROM users u WHERE u.last_login_at < DATE_SUB(CURDATE(), INTERVAL 30 DAY) LIMIT 50"},
    {"question": "users inactive for 90 days", "sql": "SELECT u.name, u.email, u.last_login_at FROM users u WHERE u.last_login_at < DATE_SUB(CURDATE(), INTERVAL 90 DAY) LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 11: COMPLEX MULTI-CONDITION QUERIES
    # ==========================================================================
    {"question": "users who uploaded more than 5 files but less than 10", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name HAVING COUNT(f.id) > 5 AND COUNT(f.id) < 10 LIMIT 50"},
    {"question": "files larger than 1MB uploaded by admins", "sql": "SELECT f.filename, ROUND(f.size/1048576,2) as size_mb, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE f.size > 1048576 AND u.role IN ('super_admin', 'org_admin') LIMIT 50"},
    {"question": "approved users who never uploaded", "sql": "SELECT u.name, u.email FROM users u LEFT JOIN files f ON u.id = f.user_id WHERE u.status = 'approved' AND f.id IS NULL LIMIT 50"},
    {"question": "active admins with files", "sql": "SELECT u.name, u.role, COUNT(f.id) as file_count FROM users u JOIN files f ON u.id = f.user_id WHERE u.is_active = 1 AND u.role IN ('super_admin', 'org_admin') GROUP BY u.id, u.name, u.role LIMIT 50"},
    {"question": "organizations with more than 3 users but no files", "sql": "SELECT o.name, COUNT(DISTINCT u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name HAVING COUNT(DISTINCT u.id) > 3 AND COUNT(f.id) = 0 LIMIT 50"},
    {"question": "users in active organizations who uploaded this week", "sql": "SELECT u.name, o.name as org_name, COUNT(f.id) as files_this_week FROM users u JOIN organizations o ON u.organization_id = o.id JOIN files f ON u.id = f.user_id WHERE o.is_active = 1 AND f.virus_scan_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY u.id, u.name, o.name LIMIT 50"},
    {"question": "pdf files larger than 500KB uploaded by org admins", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE f.content_type LIKE '%pdf%' AND f.size > 512000 AND u.role = 'org_admin' LIMIT 50"},
    {"question": "users who registered last month but never logged in", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE u.created_at >= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) AND u.last_login_at IS NULL LIMIT 50"},
    {"question": "verified users in enterprise orgs with more than 5 files", "sql": "SELECT u.name, o.name as org_name, COUNT(f.id) as file_count FROM users u JOIN organizations o ON u.organization_id = o.id JOIN files f ON u.id = f.user_id WHERE u.is_verified = 1 AND o.plan = 'enterprise' GROUP BY u.id, u.name, o.name HAVING COUNT(f.id) > 5 LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 12: RANKING & TOP/BOTTOM QUERIES
    # ==========================================================================
    {"question": "top 5 uploaders", "sql": "SELECT u.name, COUNT(f.id) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name ORDER BY file_count DESC LIMIT 5"},
    {"question": "top 10 largest files", "sql": "SELECT f.filename, ROUND(f.size/1048576,2) as size_mb FROM files f ORDER BY f.size DESC LIMIT 10"},
    {"question": "bottom 5 organizations by users", "sql": "SELECT o.name, COUNT(u.id) as user_count FROM organizations o LEFT JOIN users u ON o.id = u.organization_id GROUP BY o.id, o.name ORDER BY user_count ASC LIMIT 5"},
    {"question": "top 3 organizations by storage", "sql": "SELECT o.name, ROUND(SUM(f.size)/1048576, 2) as total_mb FROM organizations o LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name ORDER BY total_mb DESC LIMIT 3"},
    {"question": "users ranked by storage usage", "sql": "SELECT u.name, ROUND(SUM(f.size)/1048576, 2) as total_mb, RANK() OVER (ORDER BY SUM(f.size) DESC) as rank FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name LIMIT 50"},
    {"question": "files bigger than average", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb FROM files f WHERE f.size > (SELECT AVG(size) FROM files) LIMIT 50"},
    {"question": "files smaller than average", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb FROM files f WHERE f.size < (SELECT AVG(size) FROM files) LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 13: COMPARISON & ANALYTICS
    # ==========================================================================
    {"question": "compare storage usage between orgs", "sql": "SELECT o.name, ROUND(SUM(f.size)/1048576, 2) as total_mb, COUNT(f.id) as file_count FROM organizations o LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name ORDER BY total_mb DESC LIMIT 50"},
    {"question": "users vs files ratio", "sql": "SELECT (SELECT COUNT(*) FROM users) as total_users, (SELECT COUNT(*) FROM files) as total_files, ROUND((SELECT COUNT(*) FROM files) * 1.0 / (SELECT COUNT(*) FROM users), 2) as files_per_user LIMIT 50"},
    {"question": "monthly signup trend", "sql": "SELECT DATE_FORMAT(u.created_at, '%Y-%m') as month, COUNT(*) as signups FROM users u GROUP BY DATE_FORMAT(u.created_at, '%Y-%m') ORDER BY month LIMIT 50"},
    {"question": "monthly upload trend", "sql": "SELECT DATE_FORMAT(f.virus_scan_date, '%Y-%m') as month, COUNT(*) as uploads FROM files f GROUP BY DATE_FORMAT(f.virus_scan_date, '%Y-%m') ORDER BY month LIMIT 50"},
    {"question": "daily uploads this week", "sql": "SELECT DATE(f.virus_scan_date) as date, COUNT(*) as uploads FROM files f WHERE f.virus_scan_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY DATE(f.virus_scan_date) ORDER BY date LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 14: SECURITY & AUDIT QUERIES
    # ==========================================================================
    {"question": "failed login attempts", "sql": "SELECT u.name, u.email, u.failed_login_attempts FROM users u WHERE u.failed_login_attempts > 0 LIMIT 50"},
    {"question": "users with many failed logins", "sql": "SELECT u.name, u.email, u.failed_login_attempts FROM users u WHERE CAST(u.failed_login_attempts AS UNSIGNED) >= 3 LIMIT 50"},
    {"question": "users with oauth login", "sql": "SELECT u.name, u.email, u.oauth_provider FROM users u WHERE u.oauth_provider IS NOT NULL LIMIT 50"},
    {"question": "google oauth users", "sql": "SELECT u.name, u.email FROM users u WHERE u.oauth_provider = 'google' LIMIT 50"},
    {"question": "password changed recently", "sql": "SELECT u.name, u.email, u.password_changed_at FROM users u WHERE u.password_changed_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY) LIMIT 50"},
    {"question": "users who never changed password", "sql": "SELECT u.name, u.email FROM users u WHERE u.password_changed_at IS NULL LIMIT 50"},
    {"question": "login activity by ip", "sql": "SELECT u.last_login_ip, COUNT(*) as user_count FROM users u WHERE u.last_login_ip IS NOT NULL GROUP BY u.last_login_ip LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 15: FOLDER QUERIES
    # ==========================================================================
    {"question": "folders with files", "sql": "SELECT fo.name, COUNT(f.id) as file_count FROM folders fo LEFT JOIN files f ON fo.id = f.folder_id GROUP BY fo.id, fo.name HAVING COUNT(f.id) > 0 LIMIT 50"},
    {"question": "empty folders", "sql": "SELECT fo.name, fo.path FROM folders fo LEFT JOIN files f ON fo.id = f.folder_id WHERE f.id IS NULL LIMIT 50"},
    {"question": "folders with no files", "sql": "SELECT fo.name, fo.path FROM folders fo LEFT JOIN files f ON fo.id = f.folder_id WHERE f.id IS NULL LIMIT 50"},
    {"question": "files per folder", "sql": "SELECT fo.name, COUNT(f.id) as file_count FROM folders fo LEFT JOIN files f ON fo.id = f.folder_id GROUP BY fo.id, fo.name LIMIT 50"},
    {"question": "subfolders", "sql": "SELECT child.name as folder, parent.name as parent_folder FROM folders child JOIN folders parent ON child.parent_id = parent.id LIMIT 50"},
    {"question": "root folders", "sql": "SELECT fo.name FROM folders fo WHERE fo.parent_id IS NULL LIMIT 50"},
    {"question": "folder storage usage", "sql": "SELECT fo.name, ROUND(SUM(f.size)/1048576, 2) as total_mb FROM folders fo LEFT JOIN files f ON fo.id = f.folder_id GROUP BY fo.id, fo.name ORDER BY total_mb DESC LIMIT 50"},
    
    # ==========================================================================
    # CATEGORY 16: EDGE CASES & NEGATION
    # ==========================================================================
    {"question": "users except super admins", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.role != 'super_admin' LIMIT 50"},
    {"question": "all files except pdfs", "sql": "SELECT f.filename, f.content_type FROM files f WHERE f.content_type NOT LIKE '%pdf%' LIMIT 50"},
    {"question": "organizations not active", "sql": "SELECT o.name FROM organizations o WHERE o.is_active = 0 OR o.is_active IS NULL LIMIT 50"},
    {"question": "users without organization", "sql": "SELECT u.name, u.email FROM users u WHERE u.organization_id IS NULL LIMIT 50"},
    {"question": "files not in any folder", "sql": "SELECT f.filename FROM files f WHERE f.folder_id IS NULL LIMIT 50"},
    {"question": "users with email but no name", "sql": "SELECT u.email FROM users u WHERE (u.name IS NULL OR u.name = '') AND u.email IS NOT NULL LIMIT 50"},
]

# Validation examples (to test accuracy)
VALIDATION_EXAMPLES = [
    # ========== DIVERSE VALIDATION SET (20 examples) ==========
    # Should test different patterns than training
    {"question": "show all admins", "sql": "SELECT u.name, u.email, u.role FROM users u WHERE u.role IN ('super_admin', 'org_admin') LIMIT 50"},
    {"question": "recent uploads", "sql": "SELECT f.filename, u.name as uploader, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id ORDER BY f.virus_scan_date DESC LIMIT 50"},
    {"question": "storage used by each user", "sql": "SELECT u.name, ROUND(SUM(f.size)/1048576, 2) as total_mb FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name ORDER BY total_mb DESC LIMIT 50"},
    {"question": "all managers in the system", "sql": "SELECT u.name, u.email, o.name as org_name FROM users u LEFT JOIN organizations o ON u.organization_id = o.id WHERE u.role = 'manager' LIMIT 50"},
    {"question": "count files per organization", "sql": "SELECT o.name, COUNT(f.id) as file_count FROM organizations o LEFT JOIN files f ON o.id = f.organization_id GROUP BY o.id, o.name LIMIT 50"},
    {"question": "who has the largest file", "sql": "SELECT u.name, f.filename, ROUND(f.size/1048576,2) as size_mb FROM files f JOIN users u ON f.user_id = u.id ORDER BY f.size DESC LIMIT 1"},
    {"question": "users registered in January 2025", "sql": "SELECT u.name, u.email, u.created_at FROM users u WHERE MONTH(u.created_at) = 1 AND YEAR(u.created_at) = 2025 LIMIT 50"},
    {"question": "files by content type breakdown", "sql": "SELECT f.content_type, COUNT(*) as count, ROUND(SUM(f.size)/1048576, 2) as total_mb FROM files f GROUP BY f.content_type LIMIT 50"},
    {"question": "which users have never been verified", "sql": "SELECT u.name, u.email FROM users u WHERE u.is_verified = 0 OR u.is_verified IS NULL LIMIT 50"},
    {"question": "organizations sorted by storage usage", "sql": "SELECT o.name, ROUND(o.storage_used_bytes/1048576, 2) as used_mb FROM organizations o ORDER BY o.storage_used_bytes DESC LIMIT 50"},
    {"question": "users with their file counts", "sql": "SELECT u.name, u.email, COUNT(f.id) as file_count FROM users u LEFT JOIN files f ON u.id = f.user_id GROUP BY u.id, u.name, u.email LIMIT 50"},
    {"question": "newest organizations", "sql": "SELECT o.name, o.created_at FROM organizations o ORDER BY o.created_at DESC LIMIT 50"},
    {"question": "approved users count per role", "sql": "SELECT u.role, COUNT(*) as count FROM users u WHERE u.status = 'approved' GROUP BY u.role LIMIT 50"},
    {"question": "average files per user", "sql": "SELECT ROUND(COUNT(f.id) * 1.0 / COUNT(DISTINCT f.user_id), 2) as avg_files FROM files f LIMIT 50"},
    {"question": "users and their approvers", "sql": "SELECT u.name, approver.name as approved_by FROM users u LEFT JOIN users approver ON u.approved_by = approver.id LIMIT 50"},
    {"question": "text files only", "sql": "SELECT f.filename, ROUND(f.size/1024,2) as size_kb FROM files f WHERE f.content_type LIKE '%text%' LIMIT 50"},
    {"question": "organizations with verified status", "sql": "SELECT o.name, o.is_verified, o.is_active FROM organizations o LIMIT 50"},
    {"question": "files without folders", "sql": "SELECT f.filename, u.name as uploader FROM files f JOIN users u ON f.user_id = u.id WHERE f.folder_id IS NULL LIMIT 50"},
    {"question": "users sorted by last login", "sql": "SELECT u.name, u.email, u.last_login_at FROM users u ORDER BY u.last_login_at DESC LIMIT 50"},
    {"question": "organization plans distribution", "sql": "SELECT o.plan, COUNT(*) as count FROM organizations o GROUP BY o.plan LIMIT 50"},
]


# =============================================================================
# DATABASE SCHEMA (Comprehensive for DSPy context)
# =============================================================================

DATABASE_SCHEMA = """
TABLE: users (alias: u)
COLUMNS: 
  - id (INT, PK)
  - name (VARCHAR) 
  - email (VARCHAR, unique)
  - password_hash (VARCHAR)
  - role (ENUM: 'super_admin', 'org_admin', 'manager', 'user')
  - organization_id (INT, FK to organizations.id, nullable)
  - is_active (BOOLEAN)
  - is_verified (BOOLEAN)
  - status (ENUM: 'approved', 'pending', 'rejected')
  - approved_by (INT, FK to users.id, nullable - who approved this user)
  - approved_at (DATETIME, nullable)
  - created_at (DATETIME)
  - updated_at (DATETIME)
  - last_login_at (DATETIME, nullable)
  - last_login_ip (VARCHAR, nullable)
  - failed_login_attempts (INT)
  - locked_until (DATETIME, nullable)
  - password_changed_at (DATETIME, nullable)
  - oauth_provider (VARCHAR, nullable - 'google', 'github', etc.)
  - oauth_id (VARCHAR, nullable)
  - refresh_token (VARCHAR, nullable)

TABLE: files (alias: f)
COLUMNS:
  - id (INT, PK)
  - filename (VARCHAR)
  - path (VARCHAR)
  - content_type (VARCHAR - MIME type like 'application/pdf', 'image/png', 'text/plain')
  - size (BIGINT - size in BYTES)
  - user_id (INT, FK to users.id - the uploader)
  - organization_id (INT, FK to organizations.id)
  - folder_id (INT, FK to folders.id, nullable)
  - virus_scan_status (ENUM: 'pending', 'clean', 'infected')
  - virus_scan_date (DATETIME - effectively the upload date)
  - is_quarantined (BOOLEAN)
  - quarantine_reason (VARCHAR, nullable)
  - created_at (DATETIME)
  - updated_at (DATETIME)

TABLE: organizations (alias: o)
COLUMNS:
  - id (INT, PK)
  - name (VARCHAR)
  - slug (VARCHAR, unique)
  - description (TEXT, nullable)
  - email (VARCHAR)
  - phone (VARCHAR, nullable)
  - address (VARCHAR, nullable)
  - plan (ENUM: 'free', 'basic', 'pro', 'enterprise')
  - is_active (BOOLEAN)
  - is_verified (BOOLEAN)
  - storage_quota_bytes (BIGINT)
  - storage_used_bytes (BIGINT)
  - max_users (INT)
  - max_files (INT)
  - created_at (DATETIME)
  - updated_at (DATETIME)

TABLE: folders (alias: fo)
COLUMNS:
  - id (INT, PK)
  - name (VARCHAR)
  - parent_id (INT, FK to folders.id, nullable - NULL for root folders)
  - organization_id (INT, FK to organizations.id)
  - created_by (INT, FK to users.id)
  - path (VARCHAR - full path like '/documents/reports')
  - created_at (DATETIME)
  - updated_at (DATETIME)

KEY RELATIONSHIPS:
- users.organization_id -> organizations.id (user belongs to org)
- users.approved_by -> users.id (self-join for approval tracking)
- files.user_id -> users.id (file uploader)
- files.organization_id -> organizations.id (file belongs to org)
- files.folder_id -> folders.id (file in folder)
- folders.parent_id -> folders.id (folder hierarchy)
- folders.created_by -> users.id (folder creator)

SIZE CONVERSIONS:
- Bytes to KB: size / 1024
- Bytes to MB: size / 1048576
- Bytes to GB: size / 1073741824

COMMON PATTERNS:
- Get uploader name: JOIN users u ON f.user_id = u.id
- Get org name: JOIN organizations o ON u.organization_id = o.id
- Get approver name: LEFT JOIN users approver ON u.approved_by = approver.id
- Users with no files: LEFT JOIN files f ON u.id = f.user_id WHERE f.id IS NULL
- Date filtering: WHERE DATE(created_at) = CURDATE() / DATE_SUB(CURDATE(), INTERVAL 7 DAY)
- Who approved user: LEFT JOIN users approver ON u.approved_by = approver.id
"""


# =============================================================================
# DSPy SIGNATURES AND MODULES
# =============================================================================

if DSPY_AVAILABLE:
    
    class TextToSQL(dspy.Signature):
        """Convert a natural language question to a MySQL SELECT query."""
        
        schema = dspy.InputField(desc="Database schema with tables and columns")
        question = dspy.InputField(desc="Natural language question about the data")
        sql = dspy.OutputField(desc="MySQL SELECT query to answer the question. Must start with SELECT and end with LIMIT 50.")
    
    
    class SQLGenerator(dspy.Module):
        """DSPy module for generating SQL from natural language."""
        
        def __init__(self):
            super().__init__()
            self.generate_sql = dspy.ChainOfThought(TextToSQL)
        
        def forward(self, question: str, schema: str = DATABASE_SCHEMA) -> str:
            result = self.generate_sql(schema=schema, question=question)
            sql = result.sql.strip()
            
            # Ensure it starts with SELECT
            if not sql.upper().startswith('SELECT'):
                sql = f"SELECT {sql}"
            
            # Ensure it ends with LIMIT
            if 'LIMIT' not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT 50"
            
            return sql


# =============================================================================
# DSPy OPTIMIZER CLASS
# =============================================================================

class DSPyTextToSQL:
    """
    DSPy-optimized Text-to-SQL generator.
    
    Uses DSPy's BootstrapFewShot to automatically find optimal prompts.
    """
    
    def __init__(
        self,
        model_name: str = "ollama_chat/gemma2:2b",
        ollama_base_url: str = "http://host.docker.internal:11434",
        cache_dir: str = None
    ):
        if not DSPY_AVAILABLE:
            raise ImportError("DSPy not installed. Run: pip install dspy-ai")
        
        self.model_name = model_name
        self.ollama_base_url = ollama_base_url
        self.cache_dir = cache_dir or "/tmp/dspy_cache"
        self.is_optimized = False
        self.sql_generator = None
        
        # Initialize DSPy with Ollama
        self._init_dspy()
        
        # Load or create optimized model
        self._load_or_optimize()
    
    def _init_dspy(self):
        """Initialize DSPy with Ollama backend."""
        try:
            # Configure DSPy to use Ollama
            lm = dspy.LM(
                model=self.model_name,
                api_base=self.ollama_base_url,
                api_key="",  # Ollama doesn't need key
                temperature=0.0,  # Deterministic for SQL
            )
            dspy.configure(lm=lm)
            logger.info(f"DSPy initialized with {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize DSPy: {e}")
            raise
    
    def _load_or_optimize(self):
        """Load cached optimized model or run optimization."""
        cache_path = Path(self.cache_dir) / "optimized_sql_generator.json"
        
        if cache_path.exists():
            try:
                self.sql_generator = SQLGenerator()
                self.sql_generator.load(str(cache_path))
                self.is_optimized = True
                logger.info("Loaded optimized DSPy model from cache")
                return
            except Exception as e:
                logger.warning(f"Failed to load cached model: {e}")
        
        # Create unoptimized model (will optimize on first use or manually)
        self.sql_generator = SQLGenerator()
        logger.info("Created new DSPy SQL generator (not yet optimized)")
    
    def optimize(self, num_threads: int = 4) -> Dict[str, Any]:
        """
        Run DSPy optimization to find optimal prompts.
        
        This analyzes the training examples and discovers the best prompt patterns.
        """
        logger.info("Starting DSPy optimization...")
        
        # Prepare training data
        trainset = [
            dspy.Example(
                question=ex["question"],
                schema=DATABASE_SCHEMA,
                sql=ex["sql"]
            ).with_inputs("question", "schema")
            for ex in TRAINING_EXAMPLES
        ]
        
        # Prepare validation data
        valset = [
            dspy.Example(
                question=ex["question"],
                schema=DATABASE_SCHEMA,
                sql=ex["sql"]
            ).with_inputs("question", "schema")
            for ex in VALIDATION_EXAMPLES
        ]
        
        # Define metric (exact match for now, could use semantic similarity)
        def sql_match_metric(example, prediction, trace=None):
            # Normalize both SQLs
            # prediction can be either a Prediction object or dict-like
            if hasattr(prediction, 'sql'):
                pred_sql = prediction.sql
            elif isinstance(prediction, dict):
                pred_sql = prediction.get('sql', '')
            else:
                pred_sql = str(prediction)
                
            pred_sql = pred_sql.strip().upper().replace(';', '')
            gold_sql = example.sql.strip().upper().replace(';', '')
            
            # Check if key elements match
            score = 0.0
            
            # Table names present
            tables = ['USERS', 'FILES', 'ORGANIZATIONS', 'FOLDERS']
            for table in tables:
                if table in gold_sql and table in pred_sql:
                    score += 0.1
            
            # JOIN present if needed
            if 'JOIN' in gold_sql:
                if 'JOIN' in pred_sql:
                    score += 0.2
            
            # WHERE clause
            if 'WHERE' in gold_sql:
                if 'WHERE' in pred_sql:
                    score += 0.2
            
            # GROUP BY
            if 'GROUP BY' in gold_sql:
                if 'GROUP BY' in pred_sql:
                    score += 0.2
            
            # HAVING
            if 'HAVING' in gold_sql:
                if 'HAVING' in pred_sql:
                    score += 0.2
            
            # Exact match bonus
            if pred_sql == gold_sql:
                score = 1.0
            
            return score
        
        # Run optimization
        optimizer = BootstrapFewShot(
            metric=sql_match_metric,
            max_bootstrapped_demos=4,
            max_labeled_demos=8,
            max_rounds=1,
        )
        
        try:
            self.sql_generator = optimizer.compile(
                SQLGenerator(),
                trainset=trainset,
            )
            self.is_optimized = True
            
            # Save optimized model
            cache_path = Path(self.cache_dir) / "optimized_sql_generator.json"
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.sql_generator.save(str(cache_path))
            
            # Evaluate on validation set
            correct = 0
            for ex in valset:
                try:
                    result = self.sql_generator(question=ex.question, schema=ex.schema)
                    # result is a Prediction object
                    pred_sql = result.sql if hasattr(result, 'sql') else str(result)
                    if sql_match_metric(ex, dspy.Prediction(sql=pred_sql)) > 0.5:
                        correct += 1
                except Exception as e:
                    logger.warning(f"Validation error: {e}")
                    pass
            
            accuracy = correct / len(valset) if valset else 0
            
            logger.info(f"DSPy optimization complete. Validation accuracy: {accuracy:.1%}")
            
            return {
                "success": True,
                "is_optimized": True,
                "validation_accuracy": accuracy,
                "training_examples": len(trainset),
                "validation_examples": len(valset)
            }
            
        except Exception as e:
            logger.error(f"DSPy optimization failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_sql(self, question: str) -> Tuple[str, Dict[str, Any]]:
        """
        Generate SQL for a natural language question.
        
        Returns:
            Tuple of (sql_query, metadata)
        """
        try:
            sql = self.sql_generator(question=question, schema=DATABASE_SCHEMA)
            
            # Clean up SQL
            sql = sql.strip()
            if not sql.upper().startswith('SELECT'):
                sql = f"SELECT {sql}"
            if 'LIMIT' not in sql.upper():
                sql = f"{sql.rstrip(';')} LIMIT 50"
            
            return sql, {
                "success": True,
                "is_optimized": self.is_optimized,
                "model": self.model_name
            }
            
        except Exception as e:
            logger.error(f"DSPy SQL generation failed: {e}")
            return None, {
                "success": False,
                "error": str(e)
            }
    
    def add_training_example(self, question: str, sql: str):
        """Add a new training example for future optimization."""
        TRAINING_EXAMPLES.append({
            "question": question,
            "sql": sql
        })
        logger.info(f"Added training example: {question[:50]}...")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_dspy_instance: Optional[DSPyTextToSQL] = None


def get_dspy_sql_generator(
    model_name: str = None,
    ollama_base_url: str = None
) -> Optional[DSPyTextToSQL]:
    """Get or create DSPy SQL generator singleton."""
    global _dspy_instance
    
    if not DSPY_AVAILABLE:
        logger.warning("DSPy not available")
        return None
    
    if _dspy_instance is None:
        try:
            _dspy_instance = DSPyTextToSQL(
                model_name=model_name or "ollama_chat/gemma2:2b",
                ollama_base_url=ollama_base_url or "http://host.docker.internal:11434"
            )
        except Exception as e:
            logger.error(f"Failed to create DSPy instance: {e}")
            return None
    
    return _dspy_instance


# =============================================================================
# CLI for manual optimization
# =============================================================================

if __name__ == "__main__":
    import sys
    
    if not DSPY_AVAILABLE:
        print("ERROR: DSPy not installed. Run: pip install dspy-ai")
        sys.exit(1)
    
    print("DSPy Text-to-SQL Optimizer")
    print("=" * 50)
    
    # Create instance
    generator = DSPyTextToSQL()
    
    if len(sys.argv) > 1 and sys.argv[1] == "optimize":
        print("\nRunning optimization...")
        result = generator.optimize()
        print(f"\nResult: {json.dumps(result, indent=2)}")
    else:
        print("\nTesting SQL generation...")
        test_questions = [
            "how many users are there",
            "who approved user20@gmail.com",
            "files uploaded by Super Admin",
        ]
        
        for q in test_questions:
            sql, meta = generator.generate_sql(q)
            print(f"\nQ: {q}")
            print(f"SQL: {sql}")
            print(f"Meta: {meta}")
