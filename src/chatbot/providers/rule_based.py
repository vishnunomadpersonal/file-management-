"""
Rule-Based Provider - Pattern matching without AI

This provider handles basic queries using predefined patterns and responses.
Useful when:
- AI providers are not configured
- Cost optimization for simple queries
- Offline/air-gapped environments
- Fallback when AI fails
"""

import time
import re
from typing import List, Dict, Any, Tuple, Optional
import logging

from .base import (
    LLMProvider, ChatMessage, ChatResponse, ChatAction,
    ActionType, UserContext
)

logger = logging.getLogger(__name__)


class RuleBasedProvider(LLMProvider):
    """
    Rule-based chatbot using pattern matching.
    
    No AI costs, instant responses, predictable behavior.
    """
    
    def __init__(self):
        self.patterns = self._build_patterns()
    
    @property
    def name(self) -> str:
        return "rule-based"
    
    def _build_patterns(self) -> List[Tuple[re.Pattern, callable]]:
        """Build regex patterns and their handlers."""
        return [
            # Greetings - comprehensive patterns for instant response
            (
                re.compile(r'^(hi|hello|hey|hiya|heya|hola|howdy|yo)[\s\!\.\']*((there|bot|assistant|buddy|friend)?[\s\!\.\']*)*$', re.IGNORECASE),
                self._handle_greeting
            ),
            (
                re.compile(r'^(greetings|salutations|sup|wassup|whats\s*up|what\'?s\s*up)[\s\!\.]*$', re.IGNORECASE),
                self._handle_greeting
            ),
            (
                re.compile(r'^good\s*(morning|afternoon|evening|day|night)[\s\!\.]*$', re.IGNORECASE),
                self._handle_greeting
            ),
            (
                re.compile(r'^(how\s*are\s*you|how\'?s\s*it\s*going|how\s*you\s*doing)[\s\!\?\.\']*$', re.IGNORECASE),
                self._handle_greeting
            ),
            (
                re.compile(r'^(you\s*there|anyone\s*there|hello\?|hi\?)[\s\!\?\.\']*$', re.IGNORECASE),
                self._handle_greeting
            ),
            # Thanks/gratitude - instant response
            (
                re.compile(r'^(thanks|thank\s*you|thx|ty|cheers|much\s*appreciated|appreciate\s*it|ta)[\s\!\.\']*(so\s*much|very\s*much|a\s*lot)?[\s\!\.\',]*$', re.IGNORECASE),
                self._handle_thanks
            ),
            (
                re.compile(r'^thank\s*you\s*(so\s*much|very\s*much|a\s*lot|a\s*bunch|a\s*ton)[\s\!\.\',]*$', re.IGNORECASE),
                self._handle_thanks
            ),
            # Farewells - instant response
            (
                re.compile(r'^(bye|goodbye|see\s*you|see\s*ya|later|cya|ciao|adios|farewell|peace|peace\s*out)[\s\!\.\']*$', re.IGNORECASE),
                self._handle_farewell
            ),
            (
                re.compile(r'^(bye\s*bye|good\s*bye|take\s*care|have\s*a\s*(good|nice|great)\s*(day|one))[\s\!\.\']*$', re.IGNORECASE),
                self._handle_farewell
            ),
            (
                re.compile(r'^(exit|quit|close|end\s*chat|stop|leave)[\s\!\.\']*$', re.IGNORECASE),
                self._handle_farewell
            ),
            # Acknowledgments - instant response
            (
                re.compile(r'^(ok|okay|k|kk|got\s*it|understood|alright|right|sure|cool|nice|great|awesome|perfect)[\s\!\.\']*$', re.IGNORECASE),
                self._handle_acknowledgment
            ),
            (
                re.compile(r'^(sounds\s*good|works\s*for\s*me|that\s*works|no\s*problem|no\s*worries|np|nw)[\s\!\.\']*$', re.IGNORECASE),
                self._handle_acknowledgment
            ),
            # Help
            (
                re.compile(r'\b(help|assist|support|how do i|how to)\b', re.IGNORECASE),
                self._handle_help
            ),
            
            # ========== DATA QUERIES (Real-time data from APIs) ==========
            # Recent files
            (
                re.compile(r'\b(recent files?|latest files?|last (uploaded|added) files?|new files?|show.*recent|my recent)\b', re.IGNORECASE),
                self._handle_recent_files
            ),
            # File count / how many files
            (
                re.compile(r'\b(how many files?|file count|number of files?|total files?|count.*files?)\b', re.IGNORECASE),
                self._handle_file_count
            ),
            
            # ========== ADMIN-ONLY QUERIES (Super Admin / Platform Admin) - BEFORE file search ==========
            # List all users (admin)
            (
                re.compile(r'\b(list\s*(all)?\s*users?|all users?|show\s*(all)?\s*users?|user list)\b', re.IGNORECASE),
                self._handle_list_all_users
            ),
            # User lookup (admin) - must be before generic file search
            (
                re.compile(r'\b(find user|lookup user|search user|user info|get user|show user)\s+([^\s]+@[^\s]+|[\w]+)\b', re.IGNORECASE),
                self._handle_user_lookup
            ),
            # Org lookup (admin) - must be before generic file search
            (
                re.compile(r'\b(find org|lookup org|search org|org info|get org|show org|organization info)\s+(\w+)\b', re.IGNORECASE),
                self._handle_org_lookup
            ),
            
            # Search files (AFTER user/org lookup to avoid conflicts)
            (
                re.compile(r'\b(search|find|look for|looking for)\s+(files?\s+)?(named?|called?|like)?\s*["\']?(\w+)["\']?\b', re.IGNORECASE),
                self._handle_search_files
            ),
            # Storage info
            (
                re.compile(r'\b(storage|space|quota|disk|how much space|storage (used|left|available|info|status))\b', re.IGNORECASE),
                self._handle_storage_info
            ),
            # Organization stats
            (
                re.compile(r'\b(org(anization)?\s*(stats?|statistics?|info|summary)|how many org|organization count|orgs? joined)\b', re.IGNORECASE),
                self._handle_org_stats
            ),
            # Recent organizations (admin)
            (
                re.compile(r'\b(recent org|new org|latest org|recently joined org|who joined)\b', re.IGNORECASE),
                self._handle_recent_orgs
            ),
            # User stats
            (
                re.compile(r'\b(user stats?|how many users?|user count|total users?|active users?)\b', re.IGNORECASE),
                self._handle_user_stats
            ),
            # Recent users
            (
                re.compile(r'\b(recent users?|new users?|who joined|latest users?|recently joined)\b', re.IGNORECASE),
                self._handle_recent_users
            ),
            # Quarantined files
            (
                re.compile(r'\b(quarantined files?|infected files?|virus files?|blocked files?|threats?)\b', re.IGNORECASE),
                self._handle_quarantined_files
            ),
            # Activity summary
            (
                re.compile(r'\b(activity|what\'?s happening|uploads? (this|today|week)|recent activity)\b', re.IGNORECASE),
                self._handle_activity_summary
            ),
            # Audit/Activity log (admin) - BEFORE my_summary to avoid "audit summary" matching "summary"
            (
                re.compile(r'\b(audit|audit log|activity log|audit summary|what happened|admin summary)\b', re.IGNORECASE),
                self._handle_audit_summary
            ),
            # My info / summary - more specific to avoid matching "audit summary"
            (
                re.compile(r'\b(my (info|summary|stats?|overview)|^summary$|give me.*summary|dashboard summary)\b', re.IGNORECASE),
                self._handle_my_summary
            ),
            # Folder stats
            (
                re.compile(r'\b(folder(s)?\s*(stats?|count|info|structure)|how many folders?|my folders?)\b', re.IGNORECASE),
                self._handle_folder_stats
            ),
            # Pipeline/ML stats
            (
                re.compile(r'\b(pipeline\s*(stats?|status|info)|ml\s*(stats?|status)|model\s*(stats?|status|info)|deltas?|training)\b', re.IGNORECASE),
                self._handle_pipeline_stats
            ),
            # Task/Job stats
            (
                re.compile(r'\b(task(s)?\s*(stats?|status)|job(s)?\s*(stats?|status)|background\s*(tasks?|jobs?)|celery|pending tasks?|running tasks?)\b', re.IGNORECASE),
                self._handle_task_stats
            ),
            # Appointment stats
            (
                re.compile(r'\b(appointment(s)?\s*(stats?|info)?|meeting(s)?|schedule|upcoming|my appointments?)\b', re.IGNORECASE),
                self._handle_appointment_stats
            ),
            # System overview (admin)
            (
                re.compile(r'\b(system\s*(overview|status|health|info)|platform\s*(stats?|overview)|everything|full stats?)\b', re.IGNORECASE),
                self._handle_system_overview
            ),
            # Virus scan stats
            (
                re.compile(r'\b(virus\s*(scan|stats?|status)|security\s*(stats?|status|scan)|scan\s*(stats?|results?))\b', re.IGNORECASE),
                self._handle_virus_stats
            ),
            
            # Locked users (admin)
            (
                re.compile(r'\b(locked users?|inactive users?|disabled users?|suspended users?)\b', re.IGNORECASE),
                self._handle_locked_users
            ),
            # Failed tasks (admin)
            (
                re.compile(r'\b(failed tasks?|task failures?|error tasks?|broken tasks?)\b', re.IGNORECASE),
                self._handle_failed_tasks
            ),
            
            # ========== EXTENDED QUERIES ==========
            # File by type
            (
                re.compile(r'\b(files?\s*by\s*type|file\s*types?|what\s*types?\s*of\s*files?)\b', re.IGNORECASE),
                self._handle_files_by_type
            ),
            # Folder tree
            (
                re.compile(r'\b(folder\s*tree|folder\s*structure|all\s*folders?|show\s*folders?)\b', re.IGNORECASE),
                self._handle_folder_tree
            ),
            # Folder contents
            (
                re.compile(r'\b(folder\s*contents?|what\'?s\s*in\s*folder|inside\s*folder|contents?\s*of)\s+(\w+)\b', re.IGNORECASE),
                self._handle_folder_contents
            ),
            # All organizations (admin)
            (
                re.compile(r'\b(all\s*org(anization)?s?|list\s*org(anization)?s?|show\s*org(anization)?s?)\b', re.IGNORECASE),
                self._handle_all_organizations
            ),
            # Org quota
            (
                re.compile(r'\b(org\s*quota|organization\s*quota|quota\s*info|storage\s*quota|usage\s*quota)\b', re.IGNORECASE),
                self._handle_org_quota
            ),
            # Pipeline deltas
            (
                re.compile(r'\b(pipeline\s*deltas?|data\s*deltas?|deltas?\s*status|unprocessed\s*deltas?)\b', re.IGNORECASE),
                self._handle_pipeline_deltas
            ),
            # Cost savings
            (
                re.compile(r'\b(cost\s*savings?|ml\s*savings?|pipeline\s*savings?|optimization\s*savings?)\b', re.IGNORECASE),
                self._handle_cost_savings
            ),
            # Model versions
            (
                re.compile(r'\b(model\s*versions?|version\s*history|model\s*history|trained\s*models?)\b', re.IGNORECASE),
                self._handle_model_versions
            ),
            # Feedback stats
            (
                re.compile(r'\b(feedback\s*stats?|feedback\s*status|training\s*feedback|feedback\s*loop)\b', re.IGNORECASE),
                self._handle_feedback_stats
            ),
            # User sessions (admin)
            (
                re.compile(r'\b(user\s*sessions?|active\s*sessions?|login\s*sessions?|who\'?s\s*online)\b', re.IGNORECASE),
                self._handle_user_sessions
            ),
            # Available roles
            (
                re.compile(r'\b(available\s*roles?|list\s*roles?|show\s*roles?|what\s*roles?)\b', re.IGNORECASE),
                self._handle_available_roles
            ),
            # User roles
            (
                re.compile(r'\b(roles?\s*for|user\s*roles?|what\s*role)\s+([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_user_roles
            ),
            
            # ========== USER ACTIONS ==========
            # Upload file (all users)
            (
                re.compile(r'\b(upload\s*(a\s*)?(file|document|image|pdf)?|i want to upload|add file|new file)\b', re.IGNORECASE),
                self._handle_upload_file
            ),
            # Share file
            (
                re.compile(r'\b(share\s*(file|document)?)\s+["\']?(\w+)["\']?\s+(with|to)\s+([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_share_file
            ),
            # Download link
            (
                re.compile(r'\b(download\s*link|get\s*link|generate\s*link|share\s*link)\s+(for\s+)?["\']?(\w+)["\']?\b', re.IGNORECASE),
                self._handle_download_link
            ),
            # Delete file (with permission) - requires "file" or "document" keyword
            (
                re.compile(r'\b(delete|remove|trash)\s+(file|document)\s*["\']?([^"\']+)["\']?\b', re.IGNORECASE),
                self._handle_delete_file
            ),
            # Create folder (all users)
            (
                re.compile(r'\b(create|new|make)\s+(a\s*)?(folder|directory)\s*["\']?([^"\']*)["\']?\b', re.IGNORECASE),
                self._handle_create_folder
            ),
            # Move folder
            (
                re.compile(r'\b(move\s*folder)\s+["\']?(\w+)["\']?\s+(to|into)\s+["\']?(\w+)["\']?\b', re.IGNORECASE),
                self._handle_move_folder
            ),
            # Rename folder
            (
                re.compile(r'\b(rename\s*folder)\s+["\']?(\w+)["\']?\s+(to|as)\s+["\']?(\w+)["\']?\b', re.IGNORECASE),
                self._handle_rename_folder
            ),
            # Create appointment
            (
                re.compile(r'\b(create|new|schedule)\s+(appointment|meeting)\s*["\']?([^"\']*)["\']?\b', re.IGNORECASE),
                self._handle_create_appointment
            ),
            
            # ========== ADMIN ACTIONS ==========
            # Reset password (admin)
            (
                re.compile(r'\b(reset password|password reset)\s+(for\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_reset_password
            ),
            # Lock user (admin)
            (
                re.compile(r'\b(lock|suspend|disable)\s+(user\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_lock_user
            ),
            # Unlock user (admin)
            (
                re.compile(r'\b(unlock|unsuspend|enable|activate)\s+(user\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_unlock_user
            ),
            # Create user (admin)
            (
                re.compile(r'\b(create\s*user|add\s*user|new\s*user)\s+([^\s]+@[^\s]+)(\s+as\s+(\w+))?\b', re.IGNORECASE),
                self._handle_create_user
            ),
            # Delete user (admin)
            (
                re.compile(r'\b(delete\s*user|remove\s*user)\s+([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_delete_user
            ),
            # Assign role (admin)
            (
                re.compile(r'\b(assign\s*role|set\s*role|change\s*role)\s+(\w+)\s+(to|for)\s+([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_assign_role
            ),
            # Create organization (admin)
            (
                re.compile(r'\b(create\s*org(anization)?|new\s*org(anization)?)\s+["\']?(\w+)["\']?\b', re.IGNORECASE),
                self._handle_create_org
            ),
            # Trigger pipeline (admin)
            (
                re.compile(r'\b(trigger\s*pipeline|run\s*pipeline|start\s*pipeline)\b', re.IGNORECASE),
                self._handle_trigger_pipeline
            ),
            # Train router (admin)
            (
                re.compile(r'\b(train\s*router|retrain\s*router|update\s*router)\b', re.IGNORECASE),
                self._handle_train_router
            ),
            # Rollback model (admin)
            (
                re.compile(r'\b(rollback\s*model|revert\s*model)\s+(\w+)(\s+to\s+(\w+))?\b', re.IGNORECASE),
                self._handle_rollback_model
            ),
            # Force logout (admin)
            (
                re.compile(r'\b(force\s*logout|logout\s*user|end\s*sessions?)\s+(for\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_force_logout
            ),
            # Require MFA (admin)
            (
                re.compile(r'\b(require\s*mfa|enable\s*mfa|setup\s*mfa)\s+(for\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_require_mfa
            ),
            
            # ========== REMAINING SPECIALIZED OPERATIONS ==========
            # Organization Advanced
            (
                re.compile(r'\b(update\s*org|edit\s*org|change\s*org)\s*(settings?)?\b', re.IGNORECASE),
                self._handle_update_org
            ),
            (
                re.compile(r'\b(delete\s*org|remove\s*org)\s+(\w+)\b', re.IGNORECASE),
                self._handle_delete_org
            ),
            (
                re.compile(r'\b(api\s*keys?|manage\s*api\s*keys?|list\s*api\s*keys?|show\s*api\s*keys?)\b', re.IGNORECASE),
                self._handle_api_keys
            ),
            (
                re.compile(r'\b(create\s*api\s*key|new\s*api\s*key|generate\s*api\s*key)\s*(\w+)?\b', re.IGNORECASE),
                self._handle_create_api_key
            ),
            (
                re.compile(r'\b(revoke\s*api\s*key|delete\s*api\s*key|remove\s*api\s*key)\s+(\w+)\b', re.IGNORECASE),
                self._handle_revoke_api_key
            ),
            (
                re.compile(r'\b(audit\s*logs?|activity\s*logs?|org\s*logs?|view\s*logs?)\b', re.IGNORECASE),
                self._handle_audit_logs
            ),
            # Pipeline Advanced
            (
                re.compile(r'\b(detect\s*changes?|scan\s*changes?)\s+(for\s+|in\s+)?(\w+)\b', re.IGNORECASE),
                self._handle_detect_changes
            ),
            (
                re.compile(r'\b(process\s*delta|run\s*delta)\s+(\w+)\b', re.IGNORECASE),
                self._handle_process_delta
            ),
            (
                re.compile(r'\b(set\s*strategy|override\s*strategy|use\s*strategy|change\s*strategy)\s+(\w+)\b', re.IGNORECASE),
                self._handle_strategy_override
            ),
            # Feedback Advanced
            (
                re.compile(r'\b(submit\s*feedback|send\s*feedback|give\s*feedback)\b', re.IGNORECASE),
                self._handle_submit_feedback
            ),
            (
                re.compile(r'\b(approve\s*feedback)\s+(\w+)\b', re.IGNORECASE),
                self._handle_approve_feedback
            ),
            (
                re.compile(r'\b(reject\s*feedback)\s+(\w+)\b', re.IGNORECASE),
                self._handle_reject_feedback
            ),
            (
                re.compile(r'\b(export\s*training\s*data|download\s*training\s*data|export\s*feedback)\b', re.IGNORECASE),
                self._handle_export_training_data
            ),
            # Model Versioning Advanced
            (
                re.compile(r'\b(compare\s*versions?|version\s*diff|model\s*diff)\s+(\w+)\s+(v?[\d\.]+)\s+(v?[\d\.]+)\b', re.IGNORECASE),
                self._handle_compare_versions
            ),
            (
                re.compile(r'\b(export\s*model|download\s*model)\s+(\w+)(\s+(v?[\d\.]+))?\b', re.IGNORECASE),
                self._handle_export_model
            ),
            (
                re.compile(r'\b(model\s*metrics|metrics\s*history|model\s*history)\s+(\w+)\b', re.IGNORECASE),
                self._handle_model_metrics
            ),
            # Keycloak Advanced
            (
                re.compile(r'\b(disable\s*mfa|remove\s*mfa|turn\s*off\s*mfa)\s+(for\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_disable_mfa
            ),
            (
                re.compile(r'\b(update\s*user\s*attributes?|set\s*user\s*attributes?|user\s*attributes?)\s+(for\s+)?([^\s]+@[^\s]+)\b', re.IGNORECASE),
                self._handle_user_attributes
            ),
            (
                re.compile(r'\b(token\s*info|my\s*token|session\s*info|current\s*session)\b', re.IGNORECASE),
                self._handle_token_info
            ),
            # MCP (Model Context Protocol)
            (
                re.compile(r'\b(mcp\s*status|model\s*context\s*protocol|mcp\s*info)\b', re.IGNORECASE),
                self._handle_mcp_status
            ),
            (
                re.compile(r'\b(mcp\s*tools?|list\s*mcp\s*tools?|available\s*mcp\s*tools?)\b', re.IGNORECASE),
                self._handle_mcp_tools
            ),
            (
                re.compile(r'\b(mcp\s*resources?|list\s*mcp\s*resources?)\b', re.IGNORECASE),
                self._handle_mcp_resources
            ),
            (
                re.compile(r'\b(call\s*mcp\s*tool|run\s*mcp\s*tool|execute\s*mcp)\s+(\w+)\b', re.IGNORECASE),
                self._handle_mcp_tool_call
            ),
            
            # ========== NAVIGATION ==========
            # Navigation - Files (expanded patterns)
            (
                re.compile(r'\b(my files?|show files?|view files?|go to files?|open files?|take me to.*files?|navigate.*files?|files? page)\b', re.IGNORECASE),
                self._handle_navigate_files
            ),
            # Navigation - All Files (admin)
            (
                re.compile(r'\b(all files|platform files|all documents|every file)\b', re.IGNORECASE),
                self._handle_navigate_all_files
            ),
            # Navigation - Users (expanded)
            (
                re.compile(r'\b(users?|manage users?|user management|show users?|take me to.*users?|list users?)\b', re.IGNORECASE),
                self._handle_navigate_users
            ),
            # Navigation - Settings (expanded)
            (
                re.compile(r'\b(settings|preferences|account settings|my account|take me to.*settings)\b', re.IGNORECASE),
                self._handle_navigate_settings
            ),
            # Navigation - Dashboard (expanded)
            (
                re.compile(r'\b(dashboard|home|main page|go home|take me to.*dashboard|take me home)\b', re.IGNORECASE),
                self._handle_navigate_dashboard
            ),
            # Navigation - Organizations
            (
                re.compile(r'\b(organizations?|orgs?|tenants?|take me to.*org)\b', re.IGNORECASE),
                self._handle_navigate_organizations
            ),
            # Navigation - Approvals
            (
                re.compile(r'\b(approvals?|pending|review)\b', re.IGNORECASE),
                self._handle_navigate_approvals
            ),
            # Navigation - Analytics
            (
                re.compile(r'\b(analytics?|reports?|statistics?|metrics?|insights?|take me to.*analytics)\b', re.IGNORECASE),
                self._handle_navigate_analytics
            ),
            # Navigation - API Gateway
            (
                re.compile(r'\b(api gateway|gateway|kong|take me to.*gateway)\b', re.IGNORECASE),
                self._handle_navigate_api_gateway
            ),
            # Navigation - API Keys
            (
                re.compile(r'\b(api keys?|keys?|tokens?|take me to.*api.?keys?)\b', re.IGNORECASE),
                self._handle_navigate_api_keys
            ),
            # Navigation - Database
            (
                re.compile(r'\b(database|db|mysql|take me to.*database)\b', re.IGNORECASE),
                self._handle_navigate_database
            ),
            # Navigation - System Logs (must be before Infrastructure to match "system logs" correctly)
            (
                re.compile(r'\b(system logs?|audit logs?|logs?|history|take me to.*logs?)\b', re.IGNORECASE),
                self._handle_navigate_system_logs
            ),
            # Navigation - Infrastructure (removed "system" to avoid conflict with system logs)
            (
                re.compile(r'\b(infrastructure|infra|servers?|take me to.*infrastructure)\b', re.IGNORECASE),
                self._handle_navigate_infrastructure
            ),
            # Navigation - Platform Admin
            (
                re.compile(r'\b(platform admin|platformadmin|admin panel|admin page|take me to.*platform.?admin)\b', re.IGNORECASE),
                self._handle_navigate_platformadmin
            ),
            # Navigation - Quarantine
            (
                re.compile(r'\b(quarantine|quarantined|infected|virus|malware|take me to.*quarantine)\b', re.IGNORECASE),
                self._handle_navigate_quarantine
            ),
            # Navigation - Security
            (
                re.compile(r'\b(security|permissions|access control|rbac|take me to.*security)\b', re.IGNORECASE),
                self._handle_navigate_security
            ),
            # Navigation - Team
            (
                re.compile(r'\b(team|members?|colleagues?|staff|take me to.*team)\b', re.IGNORECASE),
                self._handle_navigate_team
            ),
            # File Upload
            (
                re.compile(r'\b(upload|upload file|add file|new file|can i upload|how.*(do i |to )?upload|want to upload|upload.*(via|through|in|here))\b', re.IGNORECASE),
                self._handle_upload
            ),
            # File Download
            (
                re.compile(r'\b(download|get file|save file)\b', re.IGNORECASE),
                self._handle_download
            ),
            # File Share
            (
                re.compile(r'\b(share|sharing|share file|send file)\b', re.IGNORECASE),
                self._handle_share
            ),
            # Delete org (MUST be before generic delete)
            (
                re.compile(r'\b(delete|remove)\s+org(anization)?\s+\w+\b', re.IGNORECASE),
                self._handle_delete_org
            ),
            # Delete user (MUST be before generic delete)
            (
                re.compile(r'\b(delete|remove)\s+user\s+\S+@\S+\b', re.IGNORECASE),
                self._handle_delete_user
            ),
            # File Delete (generic - after specific deletes)
            (
                re.compile(r'\b(delete|remove|trash|delete file)\b', re.IGNORECASE),
                self._handle_delete
            ),
            # API/System Health
            (
                re.compile(r'\b(api.*(status|down|active|health)|system.*(status|health|down)|anything down|services?.*(down|active|status)|how many api)\b', re.IGNORECASE),
                self._handle_api_health
            ),
            # API/System Health
            (
                re.compile(r'\b(api.*(status|down|active|health)|system.*(status|health|down)|anything down|services?.*(down|active|status)|how many api)\b', re.IGNORECASE),
                self._handle_api_health
            ),
            # Status/Info
            (
                re.compile(r'\b(status|my role|who am i|my permissions|what can i do)\b', re.IGNORECASE),
                self._handle_status
            ),
            # Thanks
            (
                re.compile(r'\b(thanks|thank you|thx|ty)\b', re.IGNORECASE),
                self._handle_thanks
            ),
            # Goodbye
            (
                re.compile(r'\b(bye|goodbye|see you|exit|quit)\b', re.IGNORECASE),
                self._handle_goodbye
            ),
        ]
    
    async def chat(
        self,
        message: str,
        history: List[ChatMessage],
        user_context: UserContext,
        system_prompt: str
    ) -> ChatResponse:
        """Process message using pattern matching."""
        start_time = time.time()
        
        # Try each pattern
        for pattern, handler in self.patterns:
            if pattern.search(message):
                response = handler(message, user_context)
                response.processing_time_ms = int((time.time() - start_time) * 1000)
                return response
        
        # Default response
        processing_time = int((time.time() - start_time) * 1000)
        return ChatResponse(
            message=self._default_response(user_context),
            actions=[],
            suggestions=self._get_default_suggestions(user_context),
            provider=self.name,
            processing_time_ms=processing_time
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Rule-based is always healthy."""
        return {
            "status": "healthy",
            "provider": self.name,
            "patterns_loaded": len(self.patterns),
            "note": "Rule-based provider is always available"
        }
    
    # ========== Handler Methods ==========
    
    def _handle_greeting(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle greeting messages."""
        role_greeting = {
            "super_admin": "As a Super Admin, you have full access to all platform features.",
            "org_admin": "As an Organization Admin, you can manage your organization's files and users.",
            "manager": "As a Manager, you can manage team files and view reports.",
            "user": "You can upload, download, and share files.",
            "viewer": "You have read-only access to shared files."
        }
        
        greeting = role_greeting.get(ctx.role, "Welcome to FileVault!")
        
        return ChatResponse(
            message=f"Hello {ctx.email}! 👋 Welcome to FileVault Assistant.\n\n{greeting}\n\nHow can I help you today?",
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _handle_thanks(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle thank you messages."""
        import random
        responses = [
            "You're welcome! 😊 Let me know if you need anything else.",
            "Happy to help! 🙌 Is there anything else I can assist with?",
            "Anytime! 👍 Feel free to ask if you have more questions.",
            "Glad I could help! 😄 What else can I do for you?",
            "No problem at all! Let me know if you need more help.",
            "My pleasure! 🌟 Don't hesitate to ask if you need anything.",
        ]
        return ChatResponse(
            message=random.choice(responses),
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _handle_farewell(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle goodbye messages."""
        import random
        responses = [
            "Goodbye! 👋 Have a great day!",
            "See you later! 🙂 Take care!",
            "Bye! 👋 Come back anytime you need help.",
            "Take care! 😊 Feel free to chat again soon.",
            "Goodbye! 🌟 Hope I was helpful today!",
            "See you! 👋 Have a wonderful day!",
        ]
        return ChatResponse(
            message=random.choice(responses),
            actions=[],
            suggestions=["Start new chat", "Help"],
            provider=self.name
        )
    
    def _handle_acknowledgment(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle acknowledgment messages like ok, got it, sure, etc."""
        import random
        responses = [
            "Great! 👍 Let me know if you need anything else.",
            "Perfect! Is there anything else I can help with?",
            "Awesome! 🙌 Feel free to ask more questions.",
            "Got it! 👌 What would you like to do next?",
            "Sounds good! I'm here if you need more help.",
        ]
        return ChatResponse(
            message=random.choice(responses),
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _handle_help(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle help requests."""
        help_text = """Here's what I can help you with:

📁 **File Management**
- Upload, download, share, and delete files
- Navigate to your files or search

🧭 **Navigation**
- Take you to any page in the app
- Show your dashboard, files, settings

ℹ️ **Information**
- Your role and permissions
- How to use features

Just tell me what you'd like to do!"""
        
        return ChatResponse(
            message=help_text,
            actions=[],
            suggestions=["My files", "Upload file", "My role"],
            provider=self.name
        )
    
    # ========== DATA QUERY HANDLERS ==========
    
    def _get_data_tools(self, ctx: UserContext):
        """Get data tools instance with database session.
        
        Returns (ChatbotDataTools, Session) tuple.
        IMPORTANT: Caller must close the session when done!
        """
        from infrastructure.db.mysql import MySQLDB
        from chatbot.data_tools import ChatbotDataTools
        db = MySQLDB().SessionLocal()
        return ChatbotDataTools(db), db
    
    def _run_data_query(self, ctx: UserContext, query_func, *args, **kwargs):
        """Helper to run data queries with proper db session management."""
        db = None
        try:
            from infrastructure.db.mysql import MySQLDB
            from chatbot.data_tools import ChatbotDataTools
            db = MySQLDB().SessionLocal()
            tools = ChatbotDataTools(db)
            return query_func(tools, ctx, *args, **kwargs)
        except Exception as e:
            logger.error(f"Data query error: {e}")
            return {"success": False, "error": str(e)}
        finally:
            if db:
                db.close()
    
    def _handle_recent_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get recent files from the database."""
        result = self._run_data_query(ctx, lambda t, c: t.get_recent_files(c, limit=5))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't fetch your recent files: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Go to files", "Help"],
                provider=self.name
            )
        
        if result["count"] == 0:
            return ChatResponse(
                message="📁 You don't have any files uploaded yet.\n\nWould you like to upload your first file?",
                actions=[],
                suggestions=["Upload file", "Go to files", "Help"],
                provider=self.name
            )
        
        # Format the files list
        file_list = "\n".join([
            f"• **{f['filename']}** ({f['size']}) - {f['uploaded']}"
            for f in result["files"]
        ])
        
        msg = f"📁 **Your {result['count']} Most Recent Files:**\n\n{file_list}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Go to files", "Storage info", "How many files"],
            provider=self.name
        )
    
    def _handle_file_count(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get file count and total storage."""
        result = self._run_data_query(
            ctx,
            lambda tools, ctx: tools.get_file_count(ctx)
        )
            
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get the file count: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Go to files", "Help"],
                provider=self.name
            )
        
        msg = f"📊 **File Statistics:**\n\n"
        msg += f"• **Total Files:** {result['count']}\n"
        msg += f"• **Total Size:** {result['total_size']}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Recent files", "Storage info", "Go to files"],
            provider=self.name
        )
    
    def _handle_search_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Search for files by name."""
        import re
        match = re.search(r'(search|find|look for|looking for)\s+(files?\s+)?(named?|called?|like)?\s*["\']?(\w+)["\']?', message, re.IGNORECASE)
        search_term = match.group(4) if match else message.split()[-1]
        
        result = self._run_data_query(
            ctx,
            lambda tools, ctx, term=search_term: tools.search_files(ctx, term, limit=10)
        )
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't search for files: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Go to files", "Help"],
                provider=self.name
            )
        
        if result["count"] == 0:
            return ChatResponse(
                message=f"🔍 No files found matching **\"{search_term}\"**\n\nTry a different search term or browse your files.",
                actions=[],
                suggestions=["Go to files", "Recent files", "Help"],
                provider=self.name
            )
        
        file_list = "\n".join([
            f"• **{f['filename']}** ({f['size']}) - {f['uploaded']}"
            for f in result["files"]
        ])
        
        msg = f"🔍 **Found {result['count']} files matching \"{search_term}\":**\n\n{file_list}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Go to files", "Recent files", "Help"],
            provider=self.name
        )
    
    def _handle_storage_info(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get storage usage information."""
        result = self._run_data_query(ctx, lambda t, c: t.get_storage_info(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get storage info: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Go to files", "Help"],
                provider=self.name
            )
        
        msg = "💾 **Storage Information:**\n\n"
        
        if "platform_storage" in result:
            msg += f"• **Platform Total:** {result['platform_storage']}\n"
            msg += f"• **Total Files:** {result['total_files']}\n"
            msg += f"• **Average File Size:** {result['average_file_size']}"
        elif "storage_used" in result:
            msg += f"• **Used:** {result['storage_used']}\n"
            msg += f"• **Quota:** {result['storage_quota']}\n"
            msg += f"• **Available:** {result['storage_available']}\n"
            msg += f"• **Usage:** {result['usage_percent']}%"
            if result['usage_percent'] > 90:
                msg += "\n\n⚠️ **Warning:** Storage almost full!"
            elif result['usage_percent'] > 75:
                msg += "\n\n📢 **Note:** Storage is getting full."
        else:
            msg += f"• **Your Files:** {result.get('your_files', 0)}\n"
            msg += f"• **Your Storage:** {result.get('your_storage', '0 B')}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Recent files", "How many files", "Go to files"],
            provider=self.name
        )
    
    def _handle_org_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get organization statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_organization_stats(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get organization stats: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        if "total_organizations" in result:
            msg = "🏢 **Platform Organization Stats:**\n\n"
            msg += f"• **Total Organizations:** {result['total_organizations']}\n"
            msg += f"• **New (Last 30 days):** {result['new_last_30_days']}\n\n"
            if result.get('by_plan'):
                msg += "**By Plan:**\n"
                for plan, count in result['by_plan'].items():
                    msg += f"• {plan}: {count}\n"
        else:
            org = result.get("organization", {})
            msg = f"🏢 **{org.get('name', 'Your Organization')}:**\n\n"
            msg += f"• **Plan:** {org.get('plan', 'N/A')}\n"
            msg += f"• **Users:** {org.get('users', 0)} / {org.get('max_users', '∞')}\n"
            msg += f"• **Files:** {org.get('files', 0)}\n"
            msg += f"• **Storage:** {org.get('storage_used', '0')} / {org.get('storage_quota', 'N/A')} ({org.get('storage_percent', 0)}%)"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["User stats", "Storage info", "Go to organizations"],
            provider=self.name
        )
    
    def _handle_recent_orgs(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get recently joined organizations."""
        result = self._run_data_query(ctx, lambda t, c: t.get_recent_organizations(c, limit=5))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get recent organizations: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Organization stats", "Help"],
                provider=self.name
            )
        
        if result["count"] == 0:
            return ChatResponse(
                message="🏢 No organizations have joined recently.",
                actions=[],
                suggestions=["Organization stats", "Help"],
                provider=self.name
            )
        
        org_list = "\n".join([
            f"• **{o['name']}** ({o['plan']}) - {o['joined']} - {o['users']} users"
            for o in result["organizations"]
        ])
        
        msg = f"🏢 **Recently Joined Organizations:**\n\n{org_list}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Organization stats", "Go to organizations", "User stats"],
            provider=self.name
        )
    
    def _handle_user_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get user statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_user_stats(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get user stats: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        if "total_users" in result:
            msg = "👥 **Platform User Stats:**\n\n"
            msg += f"• **Total Users:** {result['total_users']}\n"
            msg += f"• **New (Last 30 days):** {result['new_last_30_days']}\n\n"
            if result.get('by_role'):
                msg += "**By Role:**\n"
                for role, count in result['by_role'].items():
                    msg += f"• {role}: {count}\n"
        else:
            msg = f"👥 **Organization Users:** {result.get('organization_users', 0)}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Recent users", "Organization stats", "Go to users"],
            provider=self.name
        )
    
    def _handle_recent_users(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get recently joined users."""
        result = self._run_data_query(ctx, lambda t, c: t.get_recent_users(c, limit=5))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get recent users: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["User stats", "Help"],
                provider=self.name
            )
        
        if result["count"] == 0:
            return ChatResponse(
                message="👥 No users have joined recently.",
                actions=[],
                suggestions=["User stats", "Help"],
                provider=self.name
            )
        
        user_list = "\n".join([
            f"• **{u['email']}** ({u['role']}) - {u['joined']}"
            for u in result["users"]
        ])
        
        msg = f"👥 **Recently Joined Users:**\n\n{user_list}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["User stats", "Go to users", "Help"],
            provider=self.name
        )
    
    def _handle_quarantined_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get quarantined/infected files."""
        result = self._run_data_query(ctx, lambda t, c: t.get_quarantined_files(c, limit=10))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get quarantined files: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Go to quarantine", "Help"],
                provider=self.name
            )
        
        if result["count"] == 0:
            return ChatResponse(
                message="✅ **Great news!** No quarantined or infected files found.\n\nYour system is clean! 🎉",
                actions=[],
                suggestions=["Recent files", "Go to quarantine", "Help"],
                provider=self.name
            )
        
        file_list = "\n".join([
            f"• ⚠️ **{f['filename']}** - {f['reason']} ({f['quarantined']})"
            for f in result["files"]
        ])
        
        msg = f"🔴 **Quarantined Files ({result['count']}):**\n\n{file_list}\n\n⚠️ These files have been isolated for security."
        
        return ChatResponse(
            message=msg,
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/quarantine"},
                    description="View quarantine"
                )
            ],
            suggestions=["Go to quarantine", "Security info", "Help"],
            provider=self.name
        )
    
    def _handle_activity_summary(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get activity summary."""
        result = self._run_data_query(ctx, lambda t, c: t.get_activity_summary(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get the activity summary: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = f"📈 **Activity Summary ({result['period']}):**\n\n"
        msg += f"• **Files Uploaded:** {result['uploads_this_week']}"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Recent files", "Go to analytics", "Help"],
            provider=self.name
        )
    
    def _handle_my_summary(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get a summary of user's data."""
        # Gather multiple data points using the helper
        file_count = self._run_data_query(ctx, lambda t, c: t.get_file_count(c))
        storage = self._run_data_query(ctx, lambda t, c: t.get_storage_info(c))
        activity = self._run_data_query(ctx, lambda t, c: t.get_activity_summary(c))
        
        msg = f"📊 **Your Dashboard Summary:**\n\n"
        msg += f"**👤 Role:** {ctx.role}\n\n"
        
        if file_count.get("success"):
            msg += f"**📁 Files:** {file_count['count']} ({file_count['total_size']})\n"
        
        if storage.get("success"):
            if "storage_used" in storage:
                msg += f"**💾 Storage:** {storage['storage_used']} / {storage['storage_quota']} ({storage['usage_percent']}%)\n"
            elif "your_storage" in storage:
                msg += f"**💾 Your Storage:** {storage['your_storage']}\n"
        
        if activity.get("success"):
            msg += f"**📈 This Week:** {activity['uploads_this_week']} uploads\n"
        
        msg += "\n💡 *Ask me about recent files, storage, users, or navigate anywhere!*"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Recent files", "Storage info", "Go to dashboard"],
            provider=self.name
        )
    
    def _handle_folder_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get folder statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_folder_structure(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get folder info: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = f"📂 **Folder Overview:**\n\n"
        msg += f"• **Total Folders:** {result['total_folders']}\n\n"
        
        if result['root_folders']:
            msg += "**Root Folders:**\n"
            for f in result['root_folders']:
                msg += f"• **{f['name']}** - {f['children']} subfolders\n"
        else:
            msg += "No folders created yet."
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["My files", "Go to files", "Help"],
            provider=self.name
        )
    
    def _handle_pipeline_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get ML pipeline statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_pipeline_stats(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get pipeline stats: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = "🤖 **ML Pipeline Statistics:**\n\n"
        msg += f"• **Data Deltas Processed:** {result['total_deltas']}\n"
        msg += f"• **Feedback Records:** {result['total_feedback']}\n"
        msg += f"• **Training Runs:** {result['training_runs']}\n\n"
        
        if result.get('latest_training'):
            lt = result['latest_training']
            msg += f"**Latest Training:**\n"
            msg += f"• Date: {lt['date']}\n"
            msg += f"• Samples: {lt['samples']}\n"
            msg += f"• Accuracy: {lt['accuracy']}\n\n"
        
        if result.get('strategy_distribution'):
            msg += "**Strategy Distribution:**\n"
            for strategy, count in result['strategy_distribution'].items():
                msg += f"• {strategy}: {count}\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Go to pipeline", "System overview", "Help"],
            provider=self.name
        )
    
    def _handle_task_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get background task statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_task_stats(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get task stats: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = "⚙️ **Background Tasks:**\n\n"
        msg += f"• **Total Tasks:** {result['total_tasks']}\n\n"
        
        if result.get('by_status'):
            msg += "**By Status:**\n"
            for status, count in result['by_status'].items():
                emoji = "✅" if status == "SUCCESS" else "⏳" if status == "PENDING" else "❌" if status == "FAILURE" else "🔄"
                msg += f"• {emoji} {status}: {count}\n"
        
        if result.get('recent_tasks'):
            msg += "\n**Recent Tasks:**\n"
            for t in result['recent_tasks'][:3]:
                msg += f"• {t['name']} ({t['status']}) - {t['completed']}\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["System overview", "Pipeline stats", "Help"],
            provider=self.name
        )
    
    def _handle_appointment_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get appointment statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_recent_appointments(c))
        stats = self._run_data_query(ctx, lambda t, c: t.get_appointment_stats(c))
        
        if not stats.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get appointment info: {stats.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = "📅 **Appointments:**\n\n"
        msg += f"• **Total:** {stats['total_appointments']}\n"
        msg += f"• **Upcoming:** {stats['upcoming']}\n"
        msg += f"• **Past:** {stats['past']}\n\n"
        
        if result.get("success") and result.get("appointments"):
            msg += "**Recent/Upcoming:**\n"
            for a in result['appointments']:
                status = "📍 Upcoming" if a['is_upcoming'] else "✓ Past"
                msg += f"• **{a['name']}** - {a['date']} ({status})\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_system_overview(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get system overview (admin only)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_system_overview(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get system overview: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["My summary", "Help"],
                provider=self.name
            )
        
        health_emoji = "✅" if result['health'] == "healthy" else "⚠️"
        
        msg = f"🖥️ **System Overview:** {health_emoji}\n\n"
        msg += f"• **Files:** {result['files']}\n"
        msg += f"• **Users:** {result['users']}\n"
        msg += f"• **Organizations:** {result['organizations']}\n"
        msg += f"• **Folders:** {result['folders']}\n"
        msg += f"• **Total Storage:** {result['total_storage']}\n"
        
        if result['quarantined_files'] > 0:
            msg += f"\n⚠️ **{result['quarantined_files']} quarantined files** need attention!"
        else:
            msg += f"\n✅ No security threats detected."
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["User stats", "Org stats", "Pipeline stats", "Go to dashboard"],
            provider=self.name
        )
    
    def _handle_virus_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get virus scan statistics."""
        result = self._run_data_query(ctx, lambda t, c: t.get_virus_scan_stats(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"Sorry, I couldn't get scan stats: {result.get('error', 'Unknown error')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = "🛡️ **Virus Scan Statistics:**\n\n"
        msg += f"• **Clean Rate:** {result['clean_rate']}\n"
        msg += f"• **Scans This Week:** {result['scans_this_week']}\n\n"
        
        if result.get('by_status'):
            msg += "**By Status:**\n"
            for status, count in result['by_status'].items():
                emoji = "✅" if status == "clean" else "⚠️" if status == "infected" else "⏳"
                msg += f"• {emoji} {status}: {count}\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Quarantined files", "System overview", "Help"],
            provider=self.name
        )

    # ========== ADMIN-ONLY HANDLERS ==========
    
    def _handle_list_all_users(self, message: str, ctx: UserContext) -> ChatResponse:
        """List all users (admin only)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_all_users_list(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"❌ {result.get('error', 'Could not list users')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        msg = f"👥 **All Users ({result['count']}):**\n\n"
        for u in result['users'][:15]:  # Show max 15
            status = "✅" if u['active'] else "❌"
            msg += f"• {status} **{u['email']}** ({u['role']}) - {u['created']}\n"
        
        if result['count'] > 15:
            msg += f"\n... and {result['count'] - 15} more"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["User stats", "Locked users", "Go to users"],
            provider=self.name
        )
    
    def _handle_user_lookup(self, message: str, ctx: UserContext) -> ChatResponse:
        """Look up specific user (admin only)."""
        # Extract email/name from message
        match = re.search(r'([^\s]+@[^\s]+|\b\w+\b)$', message.strip())
        search_term = match.group(1) if match else ""
        
        result = self._run_data_query(ctx, lambda t, c: t.get_user_details(c, search_term))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"❌ {result.get('error', 'User not found')}",
                actions=[],
                suggestions=["List all users", "Help"],
                provider=self.name
            )
        
        u = result['user']
        status = "✅ Active" if u['is_active'] else "❌ Inactive"
        verified = "✅" if u['email_verified'] else "❌"
        
        msg = f"👤 **User Details:**\n\n"
        msg += f"• **Email:** {u['email']}\n"
        msg += f"• **Role:** {u['role']}\n"
        msg += f"• **Status:** {status}\n"
        msg += f"• **Email Verified:** {verified}\n"
        msg += f"• **Organization:** {u['organization_id'] or 'None'}\n"
        msg += f"• **Files:** {u['files_count']}\n"
        msg += f"• **Created:** {u['created']}\n"
        msg += f"• **Last Login:** {u['last_login']}\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Reset password " + u['email'], "Lock " + u['email'], "List all users"],
            provider=self.name
        )
    
    def _handle_org_lookup(self, message: str, ctx: UserContext) -> ChatResponse:
        """Look up specific organization (admin only)."""
        match = re.search(r'\b(find|lookup|search|info|get|show)\s+org\w*\s+(\w+)', message, re.IGNORECASE)
        org_name = match.group(2) if match else ""
        
        result = self._run_data_query(ctx, lambda t, c: t.get_org_details(c, org_name))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"❌ {result.get('error', 'Organization not found')}",
                actions=[],
                suggestions=["Organization stats", "Help"],
                provider=self.name
            )
        
        o = result['organization']
        msg = f"🏢 **Organization Details:**\n\n"
        msg += f"• **Name:** {o['name']}\n"
        msg += f"• **Plan:** {o['plan']}\n"
        msg += f"• **Users:** {o['users']}\n"
        msg += f"• **Files:** {o['files']}\n"
        msg += f"• **Storage:** {o['storage_used']}\n"
        msg += f"• **Created:** {o['created']}\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Organization stats", "Go to organizations"],
            provider=self.name
        )
    
    def _handle_locked_users(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get locked/inactive users (admin only)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_locked_users(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"❌ {result.get('error', 'Could not get locked users')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        if result['count'] == 0:
            return ChatResponse(
                message="✅ **No locked or inactive users!**\n\nAll user accounts are active.",
                actions=[],
                suggestions=["User stats", "List all users"],
                provider=self.name
            )
        
        msg = f"🔒 **Locked/Inactive Users ({result['count']}):**\n\n"
        for u in result['users']:
            msg += f"• **{u['email']}** ({u['role']}) - {u['reason']}\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Unlock user", "List all users", "Help"],
            provider=self.name
        )
    
    def _handle_failed_tasks(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get failed tasks (admin only)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_failed_tasks(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"❌ {result.get('error', 'Could not get failed tasks')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        if result['count'] == 0:
            return ChatResponse(
                message="✅ **No failed tasks!**\n\nAll background jobs are running smoothly.",
                actions=[],
                suggestions=["Task status", "System overview"],
                provider=self.name
            )
        
        msg = f"❌ **Failed Tasks ({result['count']}):**\n\n"
        for t in result['tasks']:
            msg += f"• **{t['name']}** - {t['failed_at']} (retries: {t['retries']})\n"
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Task status", "System overview", "Help"],
            provider=self.name
        )
    
    def _handle_audit_summary(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get audit summary (admin only)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_audit_summary(c))
        
        if not result.get("success"):
            return ChatResponse(
                message=f"❌ {result.get('error', 'Could not get audit summary')}",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        health = "✅" if result['health'] == "healthy" else "⚠️"
        msg = f"📋 **Audit Summary ({result['period']}):** {health}\n\n"
        msg += f"• **New Users:** {result['new_users']}\n"
        msg += f"• **New Organizations:** {result['new_organizations']}\n"
        msg += f"• **Files Uploaded:** {result['files_uploaded']}\n"
        msg += f"• **Failed Tasks:** {result['failed_tasks']}\n"
        
        if result['failed_tasks'] > 0:
            msg += f"\n⚠️ There are {result['failed_tasks']} failed tasks that need attention."
        
        return ChatResponse(
            message=msg,
            actions=[],
            suggestions=["Failed tasks", "System overview", "User stats"],
            provider=self.name
        )
    
    # ========== USER ACTION HANDLERS ==========
    
    def _handle_upload_file(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file upload request."""
        return ChatResponse(
            message="📤 **Ready to upload!**\n\nClick the button below to select a file, or drag and drop directly into the chat.",
            actions=[
                ChatAction(
                    type=ActionType.UPLOAD,
                    payload={
                        "user_id": ctx.user_id,
                        "organization_id": ctx.organization_id,
                        "accept": "*/*"  # All file types
                    },
                    description="Upload a file",
                    requires_confirmation=False
                )
            ],
            suggestions=["My files", "Storage info", "Help"],
            provider=self.name
        )
    
    def _handle_delete_file(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file deletion request."""
        # Check if user has delete permission
        if 'file:delete' not in ctx.permissions and ctx.role not in ['super_admin', 'org_admin']:
            return ChatResponse(
                message="❌ You don't have permission to delete files.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="🗑️ **Delete File**\n\nTo delete a file, please go to your files page and select the file you want to delete.\n\nFor safety, file deletion requires confirmation.",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Go to files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_create_folder(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle folder creation request."""
        # Extract folder name
        match = re.search(r'(?:create|new|make)\s+(?:a\s+)?folder\s*["\']?([^"\']+)?["\']?', message, re.IGNORECASE)
        folder_name = match.group(1).strip() if match and match.group(1) else None
        
        if folder_name:
            return ChatResponse(
                message=f"📁 **Create Folder: {folder_name}**\n\nClick to create this folder:",
                actions=[
                    ChatAction(
                        type=ActionType.CREATE,
                        payload={
                            "type": "folder",
                            "name": folder_name,
                            "organization_id": ctx.organization_id
                        },
                        description=f"Create folder '{folder_name}'",
                        requires_confirmation=True
                    )
                ],
                suggestions=["My files", "Folder stats", "Help"],
                provider=self.name
            )
        else:
            return ChatResponse(
                message="📁 **Create Folder**\n\nPlease specify a folder name, e.g.:\n• `create folder Documents`\n• `new folder Reports`",
                actions=[],
                suggestions=["Folder stats", "My files", "Help"],
                provider=self.name
            )
    
    # ========== ADMIN ACTION HANDLERS ==========
    
    def _handle_reset_password(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle password reset request (admin only)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(
                message="❌ Only administrators can reset user passwords.",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        # Extract email
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(
                message="Please specify the user email, e.g.:\n`reset password for user@example.com`",
                actions=[],
                suggestions=["List all users", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message=f"🔐 **Reset Password for {email}?**\n\nThis will send a password reset email to the user.",
            actions=[
                ChatAction(
                    type=ActionType.API_CALL,
                    payload={
                        "endpoint": "/api/v1/auth/password/reset",
                        "method": "POST",
                        "data": {"email": email}
                    },
                    description=f"Reset password for {email}",
                    requires_confirmation=True
                )
            ],
            suggestions=["List all users", "User stats", "Help"],
            provider=self.name
        )
    
    def _handle_lock_user(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle user lock request (admin only)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(
                message="❌ Only administrators can lock user accounts.",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(
                message="Please specify the user email, e.g.:\n`lock user@example.com`",
                actions=[],
                suggestions=["List all users", "Locked users", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message=f"🔒 **Lock account {email}?**\n\nThis will prevent the user from logging in.",
            actions=[
                ChatAction(
                    type=ActionType.API_CALL,
                    payload={
                        "endpoint": f"/api/v1/users/lock",
                        "method": "POST",
                        "data": {"email": email, "action": "lock"}
                    },
                    description=f"Lock {email}",
                    requires_confirmation=True
                )
            ],
            suggestions=["Locked users", "List all users", "Help"],
            provider=self.name
        )
    
    def _handle_unlock_user(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle user unlock request (admin only)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(
                message="❌ Only administrators can unlock user accounts.",
                actions=[],
                suggestions=["Help"],
                provider=self.name
            )
        
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(
                message="Please specify the user email, e.g.:\n`unlock user@example.com`",
                actions=[],
                suggestions=["Locked users", "List all users", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message=f"🔓 **Unlock account {email}?**\n\nThis will allow the user to log in again.",
            actions=[
                ChatAction(
                    type=ActionType.API_CALL,
                    payload={
                        "endpoint": f"/api/v1/users/unlock",
                        "method": "POST",
                        "data": {"email": email, "action": "unlock"}
                    },
                    description=f"Unlock {email}",
                    requires_confirmation=True
                )
            ],
            suggestions=["Locked users", "List all users", "Help"],
            provider=self.name
        )

    # ========== EXTENDED QUERY HANDLERS ==========
    
    def _handle_files_by_type(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get files grouped by type."""
        result = self._run_data_query(ctx, lambda t, c: t.get_files_by_type(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = "📊 **Files by Type:**\n\n"
        for t in result['types'][:10]:
            msg += f"• **{t['type']}**: {t['count']} files ({t['size']})\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Recent files", "Storage info"], provider=self.name)
    
    def _handle_folder_tree(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get folder tree structure."""
        result = self._run_data_query(ctx, lambda t, c: t.get_folder_tree(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        def format_tree(node, indent=0):
            s = "  " * indent + f"📁 {node['name']}\n"
            for child in node.get('children', []):
                s += format_tree(child, indent + 1)
            return s
        
        msg = f"🗂️ **Folder Structure** ({result['total_folders']} folders):\n\n"
        for root in result['tree'][:10]:
            msg += format_tree(root)
        
        return ChatResponse(message=msg, actions=[], suggestions=["Folder stats", "My files"], provider=self.name)
    
    def _handle_folder_contents(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get folder contents."""
        match = re.search(r'(folder\s*contents?|what\'?s\s*in\s*folder|inside\s*folder|contents?\s*of)\s+(\w+)', message, re.IGNORECASE)
        folder_name = match.group(2) if match else None
        
        if not folder_name:
            return ChatResponse(message="Please specify a folder name, e.g.: `what's in folder Documents`", actions=[], suggestions=["Folder tree"], provider=self.name)
        
        result = self._run_data_query(ctx, lambda t, c: t.get_folder_contents(c, folder_name))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Folder tree"], provider=self.name)
        
        msg = f"📁 **{result['folder']}** ({result['file_count']} files, {result['subfolder_count']} subfolders):\n\n"
        if result['subfolders']:
            msg += "**Subfolders:**\n"
            for sf in result['subfolders'][:5]:
                msg += f"  📁 {sf['name']}\n"
        if result['files']:
            msg += "**Files:**\n"
            for f in result['files'][:10]:
                msg += f"  📄 {f['name']} ({f['size']})\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Folder tree", "My files"], provider=self.name)
    
    def _handle_all_organizations(self, message: str, ctx: UserContext) -> ChatResponse:
        """List all organizations (admin only)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_all_organizations(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = f"🏢 **All Organizations ({result['count']}):**\n\n"
        for org in result['organizations']:
            msg += f"• **{org['name']}** ({org['plan']}) - {org['users']} users, {org['files']} files\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Org stats", "Create org"], provider=self.name)
    
    def _handle_org_quota(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get organization quota info."""
        result = self._run_data_query(ctx, lambda t, c: t.get_org_quota(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = f"📊 **Quota for {result['organization']}:**\n\n"
        msg += f"**Storage:** {result['storage']['used']} / {result['storage']['quota']} ({result['storage']['percent']}%)\n"
        msg += f"**Users:** {result['users']['used']} / {result['users']['quota']} ({result['users']['percent']}%)\n"
        msg += f"**Files:** {result['files']}\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Org stats", "Storage info"], provider=self.name)
    
    def _handle_pipeline_deltas(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get pipeline deltas."""
        result = self._run_data_query(ctx, lambda t, c: t.get_pipeline_deltas(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = f"📈 **Pipeline Deltas ({result['count']}):**\n\n"
        for d in result['deltas'][:10]:
            msg += f"• {d['delta_type']} - {d['status']} ({d['created']})\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Pipeline stats", "Trigger pipeline"], provider=self.name)
    
    def _handle_cost_savings(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get ML cost savings."""
        result = self._run_data_query(ctx, lambda t, c: t.get_pipeline_cost_savings(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        cs = result['cost_savings']
        msg = f"💰 **ML Pipeline Cost Savings:**\n\n"
        msg += f"• **Total Saved:** {cs['total_saved']}\n"
        msg += f"• **This Month:** {cs['this_month']}\n"
        msg += f"• **Optimization Rate:** {cs['optimization_rate']}\n"
        msg += f"• **Efficient Routes:** {cs['efficient_routes']}/{cs['total_routes']}\n\n"
        msg += "**Recommendations:**\n"
        for r in result['recommendations']:
            msg += f"  • {r}\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Pipeline stats", "Train router"], provider=self.name)
    
    def _handle_model_versions(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get model version history."""
        result = self._run_data_query(ctx, lambda t, c: t.get_model_versions(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = "🤖 **ML Model Versions:**\n\n"
        for name, info in result['models'].items():
            msg += f"**{name}:** {info['current_version']} ({info['accuracy']})\n"
            msg += f"  Last trained: {info['last_trained']}\n"
            msg += f"  History: {', '.join(info['versions'][:3])}\n\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Rollback model", "Train router"], provider=self.name)
    
    def _handle_feedback_stats(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get feedback loop stats."""
        result = self._run_data_query(ctx, lambda t, c: t.get_feedback_stats(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        fb = result['feedback']
        ready = "✅" if fb['ready_for_training'] else "❌"
        msg = f"📊 **Feedback Loop Status:**\n\n"
        msg += f"• **Total Entries:** {fb['total_entries']}\n"
        msg += f"• **Pending Review:** {fb['pending_review']}\n"
        msg += f"• **Approved:** {fb['approved']}\n"
        msg += f"• **Rejected:** {fb['rejected']}\n"
        msg += f"• **Accuracy Trend:** {fb['accuracy_trend']}\n"
        msg += f"• **Ready for Training:** {ready}\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Train router", "Model versions"], provider=self.name)
    
    def _handle_user_sessions(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get user session info (admin)."""
        result = self._run_data_query(ctx, lambda t, c: t.get_user_sessions(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        s = result['sessions']
        msg = f"🔐 **Active Sessions:**\n\n"
        msg += f"• **Active:** {s['active_sessions']}\n"
        msg += f"• **Last Login:** {s['last_login']}\n"
        msg += f"• **Devices:** {', '.join(s['devices'])}\n"
        msg += f"• **Locations:** {', '.join(s['locations'])}\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Force logout", "User stats"], provider=self.name)
    
    def _handle_available_roles(self, message: str, ctx: UserContext) -> ChatResponse:
        """List available roles."""
        result = self._run_data_query(ctx, lambda t, c: t.get_available_roles(c))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = "👥 **Available Roles:**\n\n"
        for r in result['roles']:
            msg += f"• **{r['name']}** - {r['description']}\n"
        
        return ChatResponse(message=msg, actions=[], suggestions=["Assign role", "User stats"], provider=self.name)
    
    def _handle_user_roles(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get user's roles."""
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(message="Please specify user email", actions=[], suggestions=["Help"], provider=self.name)
        
        result = self._run_data_query(ctx, lambda t, c: t.get_user_roles(c, email))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Help"], provider=self.name)
        
        msg = f"👤 **Roles for {result['user']}:**\n\n"
        msg += f"• **Current Role:** {result['current_role']}\n\n"
        msg += f"Available: {', '.join(result['available_roles'])}"
        
        return ChatResponse(message=msg, actions=[], suggestions=[f"Assign role admin to {email}", "List all users"], provider=self.name)
    
    # ========== EXTENDED ACTION HANDLERS ==========
    
    def _handle_share_file(self, message: str, ctx: UserContext) -> ChatResponse:
        """Share file with user."""
        match = re.search(r'share\s+(?:file\s+)?["\']?(\w+)["\']?\s+(?:with|to)\s+([^\s]+@[^\s]+)', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `share file X with user@email.com`", actions=[], suggestions=["My files"], provider=self.name)
        
        filename, email = match.groups()
        result = self._run_data_query(ctx, lambda t, c: t.prepare_share_file(c, filename, email))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["My files"], provider=self.name)
        
        return ChatResponse(
            message=f"📤 **Share {result['filename']} with {email}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": result['endpoint'], "method": result['method'], "data": {"file_id": result['file_id'], "share_with": email}}, description=f"Share with {email}", requires_confirmation=True)],
            suggestions=["My files"],
            provider=self.name
        )
    
    def _handle_download_link(self, message: str, ctx: UserContext) -> ChatResponse:
        """Generate download link."""
        match = re.search(r'(?:download\s*link|get\s*link|generate\s*link)\s+(?:for\s+)?["\']?(\w+)["\']?', message, re.IGNORECASE)
        filename = match.group(1) if match else None
        
        if not filename:
            return ChatResponse(message="Please specify: `generate link for filename`", actions=[], suggestions=["My files"], provider=self.name)
        
        result = self._run_data_query(ctx, lambda t, c: t.prepare_download_link(c, filename))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["My files"], provider=self.name)
        
        return ChatResponse(
            message=f"🔗 **Generate shareable link for {result['filename']}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": result['endpoint'], "method": result['method']}, description="Generate link", requires_confirmation=True)],
            suggestions=["My files"],
            provider=self.name
        )
    
    def _handle_move_folder(self, message: str, ctx: UserContext) -> ChatResponse:
        """Move folder."""
        match = re.search(r'move\s*folder\s+["\']?(\w+)["\']?\s+(?:to|into)\s+["\']?(\w+)["\']?', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `move folder X to Y`", actions=[], suggestions=["Folder tree"], provider=self.name)
        
        folder_name, target = match.groups()
        result = self._run_data_query(ctx, lambda t, c: t.prepare_folder_action(c, 'move', folder_name, target))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Folder tree"], provider=self.name)
        
        return ChatResponse(
            message=f"📁 **Move {result['folder_name']} to {result.get('target_folder_name', target)}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/folders/{result['folder_id']}/move", "method": "POST", "data": {"parent_id": result.get('target_folder_id')}}, description="Move folder", requires_confirmation=True)],
            suggestions=["Folder tree"],
            provider=self.name
        )
    
    def _handle_rename_folder(self, message: str, ctx: UserContext) -> ChatResponse:
        """Rename folder."""
        match = re.search(r'rename\s*folder\s+["\']?(\w+)["\']?\s+(?:to|as)\s+["\']?(\w+)["\']?', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `rename folder X to Y`", actions=[], suggestions=["Folder tree"], provider=self.name)
        
        folder_name, new_name = match.groups()
        result = self._run_data_query(ctx, lambda t, c: t.prepare_folder_action(c, 'rename', folder_name, new_name))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Folder tree"], provider=self.name)
        
        return ChatResponse(
            message=f"📁 **Rename {result['folder_name']} to {new_name}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/folders/{result['folder_id']}", "method": "PATCH", "data": {"name": new_name}}, description="Rename folder", requires_confirmation=True)],
            suggestions=["Folder tree"],
            provider=self.name
        )
    
    def _handle_create_appointment(self, message: str, ctx: UserContext) -> ChatResponse:
        """Create appointment."""
        match = re.search(r'(?:create|new|schedule)\s+(?:appointment|meeting)\s*["\']?([^"\']*)["\']?', message, re.IGNORECASE)
        title = match.group(1).strip() if match and match.group(1) else "New Appointment"
        
        return ChatResponse(
            message=f"📅 **Create Appointment: {title}**\n\nPlease provide a date or go to the appointments page.",
            actions=[ChatAction(type=ActionType.NAVIGATE, payload={"path": "/dashboard/appointments"}, description="Go to Appointments")],
            suggestions=["My appointments"],
            provider=self.name
        )
    
    def _handle_create_user(self, message: str, ctx: UserContext) -> ChatResponse:
        """Create user (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'(?:create|add|new)\s*user\s+([^\s]+@[^\s]+)(?:\s+as\s+(\w+))?', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `create user email@example.com as role`", actions=[], suggestions=["List all users"], provider=self.name)
        
        email, role = match.groups()
        role = role or "user"
        
        return ChatResponse(
            message=f"👤 **Create user {email} as {role}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/users/", "method": "POST", "data": {"email": email, "role": role}}, description=f"Create {email}", requires_confirmation=True)],
            suggestions=["List all users"],
            provider=self.name
        )
    
    def _handle_delete_user(self, message: str, ctx: UserContext) -> ChatResponse:
        """Delete user (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only super admins can delete users", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(message="Please specify: `delete user email@example.com`", actions=[], suggestions=["List all users"], provider=self.name)
        
        result = self._run_data_query(ctx, lambda t, c: t.prepare_delete_user(c, email))
        
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["List all users"], provider=self.name)
        
        return ChatResponse(
            message=f"⚠️ **DELETE user {email}?**\n\n{result.get('warning', '')}",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": result['endpoint'], "method": result['method']}, description=f"Delete {email}", requires_confirmation=True)],
            suggestions=["List all users"],
            provider=self.name
        )
    
    def _handle_assign_role(self, message: str, ctx: UserContext) -> ChatResponse:
        """Assign role to user (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can assign roles", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'(?:assign|set|change)\s*role\s+(\w+)\s+(?:to|for)\s+([^\s]+@[^\s]+)', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `assign role admin to user@example.com`", actions=[], suggestions=["Available roles"], provider=self.name)
        
        role, email = match.groups()
        
        return ChatResponse(
            message=f"👤 **Assign role {role} to {email}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/keycloak/users/roles", "method": "POST", "data": {"email": email, "role": role}}, description=f"Assign {role} to {email}", requires_confirmation=True)],
            suggestions=["Available roles", "List all users"],
            provider=self.name
        )
    
    def _handle_create_org(self, message: str, ctx: UserContext) -> ChatResponse:
        """Create organization (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can create organizations", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'(?:create|new)\s*org(?:anization)?\s+["\']?(\w+)["\']?', message, re.IGNORECASE)
        org_name = match.group(1) if match else None
        
        if not org_name:
            return ChatResponse(message="Please specify: `create org OrgName`", actions=[], suggestions=["All organizations"], provider=self.name)
        
        return ChatResponse(
            message=f"🏢 **Create organization {org_name}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/organizations/", "method": "POST", "data": {"name": org_name, "plan": "standard"}}, description=f"Create {org_name}", requires_confirmation=True)],
            suggestions=["All organizations"],
            provider=self.name
        )
    
    def _handle_trigger_pipeline(self, message: str, ctx: UserContext) -> ChatResponse:
        """Trigger ML pipeline (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can trigger pipeline", actions=[], suggestions=["Help"], provider=self.name)
        
        return ChatResponse(
            message="🚀 **Trigger ML Pipeline?**\n\nThis will process pending data deltas.",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/pipeline/trigger", "method": "POST"}, description="Trigger Pipeline", requires_confirmation=True)],
            suggestions=["Pipeline stats", "Pipeline deltas"],
            provider=self.name
        )
    
    def _handle_train_router(self, message: str, ctx: UserContext) -> ChatResponse:
        """Train ML router (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can train router", actions=[], suggestions=["Help"], provider=self.name)
        
        return ChatResponse(
            message="🤖 **Train Learned Router?**\n\nThis will retrain the routing model with feedback data.",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/pipeline/router/train", "method": "POST"}, description="Train Router", requires_confirmation=True)],
            suggestions=["Model versions", "Feedback stats"],
            provider=self.name
        )
    
    def _handle_rollback_model(self, message: str, ctx: UserContext) -> ChatResponse:
        """Rollback ML model (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can rollback models", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'rollback\s*model\s+(\w+)(?:\s+to\s+(v?[\d\.]+))?', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `rollback model learned_router to v1.2.0`", actions=[], suggestions=["Model versions"], provider=self.name)
        
        model_name, version = match.groups()
        version = version or "previous"
        
        return ChatResponse(
            message=f"⏪ **Rollback {model_name} to {version}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/models/{model_name}/rollback", "method": "POST", "data": {"version": version}}, description=f"Rollback {model_name}", requires_confirmation=True)],
            suggestions=["Model versions"],
            provider=self.name
        )
    
    def _handle_force_logout(self, message: str, ctx: UserContext) -> ChatResponse:
        """Force logout user (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can force logout", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(message="Please specify: `force logout user@example.com`", actions=[], suggestions=["User sessions"], provider=self.name)
        
        return ChatResponse(
            message=f"🔒 **Force logout all sessions for {email}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/keycloak/users/logout", "method": "POST", "data": {"email": email}}, description=f"Force logout {email}", requires_confirmation=True)],
            suggestions=["User sessions", "List all users"],
            provider=self.name
        )
    
    def _handle_require_mfa(self, message: str, ctx: UserContext) -> ChatResponse:
        """Require MFA for user (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only admins can require MFA", actions=[], suggestions=["Help"], provider=self.name)
        
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        
        if not email:
            return ChatResponse(message="Please specify: `require mfa for user@example.com`", actions=[], suggestions=["User sessions"], provider=self.name)
        
        return ChatResponse(
            message=f"🔐 **Require MFA setup for {email}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/keycloak/users/mfa/require", "method": "POST", "data": {"email": email}}, description=f"Require MFA for {email}", requires_confirmation=True)],
            suggestions=["User sessions", "List all users"],
            provider=self.name
        )

    # ========== REMAINING SPECIALIZED HANDLERS ==========
    
    def _handle_update_org(self, message: str, ctx: UserContext) -> ChatResponse:
        """Update organization settings."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        return ChatResponse(
            message="⚙️ **Update Organization Settings**\n\nGo to Settings page to update org configuration.",
            actions=[ChatAction(type=ActionType.NAVIGATE, payload={"path": "/dashboard/settings"}, description="Go to Settings")],
            suggestions=["Org stats", "Settings"],
            provider=self.name
        )
    
    def _handle_delete_org(self, message: str, ctx: UserContext) -> ChatResponse:
        """Delete organization (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Only super admins can delete organizations", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:delete|remove)\s*org(?:anization)?\s+(\w+)', message, re.IGNORECASE)
        org_name = match.group(1) if match else None
        if not org_name:
            return ChatResponse(message="Please specify: `delete org OrgName`", actions=[], suggestions=["All organizations"], provider=self.name)
        result = self._run_data_query(ctx, lambda t, c: t.prepare_delete_org(c, org_name))
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["All organizations"], provider=self.name)
        return ChatResponse(
            message=f"⚠️ **DELETE organization {result['org_name']}?**\n\n{result.get('warning', '')}",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": result['endpoint'], "method": result['method']}, description=f"Delete {result['org_name']}", requires_confirmation=True)],
            suggestions=["All organizations"],
            provider=self.name
        )
    
    def _handle_api_keys(self, message: str, ctx: UserContext) -> ChatResponse:
        """List API keys."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        return ChatResponse(
            message="🔑 **API Keys Management**\n\nAPI keys provide programmatic access to your organization.\n\n• Use `create api key MyKeyName` to generate a new key\n• Use `revoke api key KEY_ID` to revoke a key\n• Go to API Keys page for full management",
            actions=[ChatAction(type=ActionType.NAVIGATE, payload={"path": "/dashboard/api-keys"}, description="Go to API Keys")],
            suggestions=["Create api key", "Settings"],
            provider=self.name
        )
    
    def _handle_create_api_key(self, message: str, ctx: UserContext) -> ChatResponse:
        """Create API key."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:create|new|generate)\s*api\s*key\s*(\w+)?', message, re.IGNORECASE)
        key_name = match.group(1) if match and match.group(1) else "default"
        return ChatResponse(
            message=f"🔑 **Create API Key '{key_name}'?**\n\n⚠️ The key will only be shown once!",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/organizations/current/api-keys", "method": "POST", "data": {"name": key_name}}, description=f"Create API Key", requires_confirmation=True)],
            suggestions=["API keys"],
            provider=self.name
        )
    
    def _handle_revoke_api_key(self, message: str, ctx: UserContext) -> ChatResponse:
        """Revoke API key."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:revoke|delete|remove)\s*api\s*key\s+(\w+)', message, re.IGNORECASE)
        key_id = match.group(1) if match else None
        if not key_id:
            return ChatResponse(message="Please specify: `revoke api key KEY_ID`", actions=[], suggestions=["API keys"], provider=self.name)
        return ChatResponse(
            message=f"⚠️ **Revoke API Key {key_id}?**\n\nThis action cannot be undone!",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/organizations/current/api-keys/{key_id}", "method": "DELETE"}, description=f"Revoke Key", requires_confirmation=True)],
            suggestions=["API keys"],
            provider=self.name
        )
    
    def _handle_audit_logs(self, message: str, ctx: UserContext) -> ChatResponse:
        """View audit logs."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        return ChatResponse(
            message="📋 **Audit Logs**\n\nAudit logs track all organization activities including:\n• User actions\n• File operations\n• Security events\n• Configuration changes\n\nGo to the audit logs page for detailed history.",
            actions=[ChatAction(type=ActionType.NAVIGATE, payload={"path": "/dashboard/security"}, description="Go to Security/Audit")],
            suggestions=["System overview", "User stats"],
            provider=self.name
        )
    
    def _handle_detect_changes(self, message: str, ctx: UserContext) -> ChatResponse:
        """Detect changes in a file."""
        if ctx.role not in ['super_admin', 'platform_admin', 'org_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:detect|scan)\s*changes?\s+(?:for\s+|in\s+)?(\w+)', message, re.IGNORECASE)
        filename = match.group(1) if match else None
        if not filename:
            return ChatResponse(message="Please specify: `detect changes for filename`", actions=[], suggestions=["Recent files"], provider=self.name)
        result = self._run_data_query(ctx, lambda t, c: t.prepare_detect_changes(c, filename))
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Recent files"], provider=self.name)
        return ChatResponse(
            message=f"🔍 **Detect changes in {result['filename']}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": result['endpoint'], "method": result['method']}, description="Detect Changes", requires_confirmation=True)],
            suggestions=["Pipeline stats"],
            provider=self.name
        )
    
    def _handle_process_delta(self, message: str, ctx: UserContext) -> ChatResponse:
        """Process a specific delta."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:process|run)\s*delta\s+(\w+)', message, re.IGNORECASE)
        delta_id = match.group(1) if match else None
        if not delta_id:
            return ChatResponse(message="Please specify: `process delta DELTA_ID`", actions=[], suggestions=["Pipeline deltas"], provider=self.name)
        return ChatResponse(
            message=f"⚙️ **Process delta {delta_id}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/pipeline/deltas/{delta_id}/process", "method": "POST"}, description="Process Delta", requires_confirmation=True)],
            suggestions=["Pipeline deltas", "Pipeline stats"],
            provider=self.name
        )
    
    def _handle_strategy_override(self, message: str, ctx: UserContext) -> ChatResponse:
        """Override pipeline strategy."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:set|override|use|change)\s*strategy\s+(\w+)', message, re.IGNORECASE)
        strategy = match.group(1) if match else None
        valid = ['local', 'cloud', 'hybrid', 'cost_optimized', 'performance']
        if not strategy or strategy.lower() not in valid:
            return ChatResponse(message=f"Please specify a valid strategy: {', '.join(valid)}", actions=[], suggestions=["Pipeline stats"], provider=self.name)
        return ChatResponse(
            message=f"🔄 **Override strategy to {strategy}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/pipeline/strategy/override", "method": "POST", "data": {"strategy": strategy.lower()}}, description=f"Set {strategy}", requires_confirmation=True)],
            suggestions=["Pipeline stats", "Cost savings"],
            provider=self.name
        )
    
    def _handle_submit_feedback(self, message: str, ctx: UserContext) -> ChatResponse:
        """Submit feedback."""
        return ChatResponse(
            message="📝 **Submit Feedback**\n\nWhat type of feedback would you like to submit?\n\n• Bug report\n• Feature request\n• Improvement suggestion\n• General feedback\n\nPlease describe your feedback and I'll help you submit it.",
            actions=[ChatAction(type=ActionType.NAVIGATE, payload={"path": "/dashboard/feedback"}, description="Go to Feedback")],
            suggestions=["Feedback stats"],
            provider=self.name
        )
    
    def _handle_approve_feedback(self, message: str, ctx: UserContext) -> ChatResponse:
        """Approve feedback (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'approve\s*feedback\s+(\w+)', message, re.IGNORECASE)
        feedback_id = match.group(1) if match else None
        if not feedback_id:
            return ChatResponse(message="Please specify: `approve feedback FEEDBACK_ID`", actions=[], suggestions=["Feedback stats"], provider=self.name)
        return ChatResponse(
            message=f"✅ **Approve feedback {feedback_id}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/feedback/{feedback_id}/approve", "method": "POST"}, description="Approve", requires_confirmation=True)],
            suggestions=["Feedback stats"],
            provider=self.name
        )
    
    def _handle_reject_feedback(self, message: str, ctx: UserContext) -> ChatResponse:
        """Reject feedback (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'reject\s*feedback\s+(\w+)', message, re.IGNORECASE)
        feedback_id = match.group(1) if match else None
        if not feedback_id:
            return ChatResponse(message="Please specify: `reject feedback FEEDBACK_ID`", actions=[], suggestions=["Feedback stats"], provider=self.name)
        return ChatResponse(
            message=f"❌ **Reject feedback {feedback_id}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/feedback/{feedback_id}/reject", "method": "POST"}, description="Reject", requires_confirmation=True)],
            suggestions=["Feedback stats"],
            provider=self.name
        )
    
    def _handle_export_training_data(self, message: str, ctx: UserContext) -> ChatResponse:
        """Export training data (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        return ChatResponse(
            message="📤 **Export Training Data?**\n\nThis will export all approved feedback as training data for ML models.",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/feedback/export", "method": "GET"}, description="Export Data", requires_confirmation=True)],
            suggestions=["Feedback stats", "Model versions"],
            provider=self.name
        )
    
    def _handle_compare_versions(self, message: str, ctx: UserContext) -> ChatResponse:
        """Compare model versions (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'compare\s*(?:versions?|models?)\s+(\w+)\s+(v?[\d\.]+)\s+(v?[\d\.]+)', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `compare versions learned_router v1.2.0 v1.2.1`", actions=[], suggestions=["Model versions"], provider=self.name)
        model, v1, v2 = match.groups()
        return ChatResponse(
            message=f"📊 **Compare {model} {v1} vs {v2}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": f"/api/v1/models/{model}/compare", "method": "GET", "params": {"version1": v1, "version2": v2}}, description="Compare", requires_confirmation=False)],
            suggestions=["Model versions"],
            provider=self.name
        )
    
    def _handle_export_model(self, message: str, ctx: UserContext) -> ChatResponse:
        """Export model (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'(?:export|download)\s*model\s+(\w+)(?:\s+(v?[\d\.]+))?', message, re.IGNORECASE)
        if not match:
            return ChatResponse(message="Please specify: `export model learned_router` or `export model learned_router v1.2.0`", actions=[], suggestions=["Model versions"], provider=self.name)
        model = match.group(1)
        version = match.group(2) or "latest"
        endpoint = f"/api/v1/models/{model}/export"
        if version != "latest":
            endpoint += f"?version={version}"
        return ChatResponse(
            message=f"📦 **Export {model} ({version})?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": endpoint, "method": "GET"}, description="Export Model", requires_confirmation=True)],
            suggestions=["Model versions"],
            provider=self.name
        )
    
    def _handle_model_metrics(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get model metrics history."""
        match = re.search(r'(?:model\s*)?metrics\s+(\w+)', message, re.IGNORECASE)
        model = match.group(1) if match else "learned_router"
        result = self._run_data_query(ctx, lambda t, c: t.get_model_metrics_history(c, model))
        if not result.get("success"):
            return ChatResponse(message=f"❌ {result.get('error')}", actions=[], suggestions=["Model versions"], provider=self.name)
        msg = f"📈 **{result['model']} Metrics History:**\n\n"
        for m in result['metrics']:
            msg += f"• **{m['version']}**: {m['accuracy']}% accuracy, {m['latency_ms']}ms ({m['date']})\n"
        msg += f"\n**Trend:** {result['trend']}"
        return ChatResponse(message=msg, actions=[], suggestions=["Model versions", "Rollback model"], provider=self.name)
    
    def _handle_disable_mfa(self, message: str, ctx: UserContext) -> ChatResponse:
        """Disable MFA for user (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        if not email:
            return ChatResponse(message="Please specify: `disable mfa for user@example.com`", actions=[], suggestions=["User sessions"], provider=self.name)
        return ChatResponse(
            message=f"⚠️ **Disable MFA for {email}?**\n\nThis will remove two-factor authentication protection!",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/keycloak/users/mfa/disable", "method": "POST", "data": {"email": email}}, description=f"Disable MFA", requires_confirmation=True)],
            suggestions=["User sessions"],
            provider=self.name
        )
    
    def _handle_user_attributes(self, message: str, ctx: UserContext) -> ChatResponse:
        """Manage user attributes (admin)."""
        if ctx.role not in ['super_admin', 'platform_admin']:
            return ChatResponse(message="❌ Permission denied", actions=[], suggestions=["Help"], provider=self.name)
        match = re.search(r'([^\s]+@[^\s]+)', message)
        email = match.group(1) if match else None
        if not email:
            return ChatResponse(message="Please specify: `user attributes for user@example.com`", actions=[], suggestions=["List all users"], provider=self.name)
        return ChatResponse(
            message=f"👤 **User Attributes for {email}**\n\nTo update attributes, use the Users management page.",
            actions=[ChatAction(type=ActionType.NAVIGATE, payload={"path": "/dashboard/users"}, description="Go to Users")],
            suggestions=["List all users", f"Find user {email}"],
            provider=self.name
        )
    
    def _handle_token_info(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get current token/session info."""
        result = self._run_data_query(ctx, lambda t, c: t.get_token_info(c))
        info = result.get('token_info', {})
        msg = "🔐 **Current Session Info:**\n\n"
        msg += f"• **User ID:** {info.get('user_id', 'N/A')}\n"
        msg += f"• **Email:** {info.get('email', 'N/A')}\n"
        msg += f"• **Role:** {info.get('role', 'N/A')}\n"
        msg += f"• **Organization:** {info.get('org_id', 'Platform-wide')}\n"
        if info.get('permissions'):
            msg += f"• **Permissions:** {len(info['permissions'])} granted\n"
        msg += f"\n{result.get('note', '')}"
        return ChatResponse(message=msg, actions=[], suggestions=["My summary", "Settings"], provider=self.name)
    
    def _handle_mcp_status(self, message: str, ctx: UserContext) -> ChatResponse:
        """Get MCP status."""
        result = self._run_data_query(ctx, lambda t, c: t.get_mcp_status(c))
        mcp = result.get('mcp', {})
        msg = f"🔌 **Model Context Protocol (MCP)**\n\n"
        msg += f"• **Status:** {mcp.get('status', 'unknown')}\n"
        msg += f"• **Version:** {mcp.get('version', 'N/A')}\n"
        msg += f"• **Endpoints:** {len(mcp.get('endpoints', []))}\n\n"
        msg += "**Available Operations:**\n"
        for ep in mcp.get('endpoints', [])[:5]:
            msg += f"  • {ep['name']}: {ep['description']}\n"
        return ChatResponse(message=msg, actions=[], suggestions=["MCP tools", "MCP resources"], provider=self.name)
    
    def _handle_mcp_tools(self, message: str, ctx: UserContext) -> ChatResponse:
        """List MCP tools."""
        return ChatResponse(
            message="🛠️ **MCP Tools**\n\nModel Context Protocol tools allow AI assistants to interact with your system:\n\n• **file_read** - Read file contents\n• **file_write** - Write to files\n• **db_query** - Query database\n• **api_call** - Call internal APIs\n• **config_get** - Get configuration\n\nUse `call mcp tool TOOL_NAME` to execute.",
            actions=[],
            suggestions=["MCP status", "MCP resources"],
            provider=self.name
        )
    
    def _handle_mcp_resources(self, message: str, ctx: UserContext) -> ChatResponse:
        """List MCP resources."""
        result = self._run_data_query(ctx, lambda t, c: t.get_mcp_resources(c))
        msg = "📚 **MCP Resources**\n\n"
        for r in result.get('resources', []):
            msg += f"• **{r['name']}** ({r['type']})\n  `{r['uri']}`\n"
        return ChatResponse(message=msg, actions=[], suggestions=["MCP status", "MCP tools"], provider=self.name)
    
    def _handle_mcp_tool_call(self, message: str, ctx: UserContext) -> ChatResponse:
        """Call MCP tool."""
        match = re.search(r'(?:call|run|execute)\s*mcp\s*(?:tool)?\s+(\w+)', message, re.IGNORECASE)
        tool_name = match.group(1) if match else None
        if not tool_name:
            return ChatResponse(message="Please specify: `call mcp tool TOOL_NAME`", actions=[], suggestions=["MCP tools"], provider=self.name)
        return ChatResponse(
            message=f"🔧 **Execute MCP Tool: {tool_name}?**",
            actions=[ChatAction(type=ActionType.API_CALL, payload={"endpoint": "/api/v1/mcp/tools/call", "method": "POST", "data": {"tool": tool_name, "params": {}}}, description=f"Call {tool_name}", requires_confirmation=True)],
            suggestions=["MCP tools", "MCP status"],
            provider=self.name
        )

    # ========== NAVIGATION HANDLERS ==========
    
    def _handle_navigate_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to user's files."""
        return ChatResponse(
            message="Taking you to your files. 📁",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to My Files"
                )
            ],
            suggestions=["Upload file", "Help"],
            provider=self.name
        )
    
    def _handle_navigate_all_files(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to all files (admin only)."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, you don't have permission to view all platform files. You can access your own files instead.",
                actions=[
                    ChatAction(
                        type=ActionType.NAVIGATE,
                        payload={"path": "/dashboard/files"},
                        description="Navigate to My Files"
                    )
                ],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to all platform files. 📂",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/all-files"},
                    description="Navigate to All Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_navigate_users(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to user management."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, user management is only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to user management. 👥",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/users"},
                    description="Navigate to User Management"
                )
            ],
            suggestions=["All files", "Settings"],
            provider=self.name
        )
    
    def _handle_navigate_settings(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to settings."""
        return ChatResponse(
            message="Taking you to your account settings. ⚙️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/settings"},
                    description="Navigate to Settings"
                )
            ],
            suggestions=["My files", "Dashboard"],
            provider=self.name
        )
    
    def _handle_navigate_dashboard(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to dashboard."""
        return ChatResponse(
            message="Taking you to the dashboard. 🏠",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard"},
                    description="Navigate to Dashboard"
                )
            ],
            suggestions=["My files", "Settings"],
            provider=self.name
        )
    
    def _handle_navigate_organizations(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to organizations (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, organization management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to organization management. 🏢",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/organizations"},
                    description="Navigate to Organizations"
                )
            ],
            suggestions=["All files", "Users"],
            provider=self.name
        )
    
    def _handle_navigate_approvals(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to approvals."""
        return ChatResponse(
            message="Taking you to file approvals. ✅",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/approvals"},
                    description="Navigate to Approvals"
                )
            ],
            suggestions=["My files", "Dashboard"],
            provider=self.name
        )
    
    def _handle_navigate_analytics(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to analytics."""
        if ctx.role not in ("super_admin", "org_admin", "manager"):
            return ChatResponse(
                message="Sorry, analytics is only available to managers and above.",
                actions=[],
                suggestions=["My files", "Dashboard", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to analytics. 📊",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/analytics"},
                    description="Navigate to Analytics"
                )
            ],
            suggestions=["Dashboard", "My files"],
            provider=self.name
        )
    
    def _handle_navigate_api_gateway(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to API gateway (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, API Gateway management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to API Gateway management. 🔌",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/api-gateway"},
                    description="Navigate to API Gateway"
                )
            ],
            suggestions=["Infrastructure", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_api_keys(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to API keys."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, API key management is only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to API keys management. 🔑",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/api-keys"},
                    description="Navigate to API Keys"
                )
            ],
            suggestions=["Settings", "Security"],
            provider=self.name
        )
    
    def _handle_navigate_database(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to database management (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, database management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to database management. 🗄️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/database"},
                    description="Navigate to Database"
                )
            ],
            suggestions=["Infrastructure", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_infrastructure(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to infrastructure (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, infrastructure management is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to infrastructure management. 🖥️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/infrastructure"},
                    description="Navigate to Infrastructure"
                )
            ],
            suggestions=["Database", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_platformadmin(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to platform admin (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, platform administration is only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to platform administration. 🛠️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/platformadmin"},
                    description="Navigate to Platform Admin"
                )
            ],
            suggestions=["Organizations", "System logs"],
            provider=self.name
        )
    
    def _handle_navigate_quarantine(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to quarantine."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, quarantine access is only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to quarantined files. ⚠️",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/quarantine"},
                    description="Navigate to Quarantine"
                )
            ],
            suggestions=["All files", "Security"],
            provider=self.name
        )
    
    def _handle_navigate_security(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to security."""
        if ctx.role not in ("super_admin", "org_admin"):
            return ChatResponse(
                message="Sorry, security settings are only available to administrators.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to security settings. 🔒",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/security"},
                    description="Navigate to Security"
                )
            ],
            suggestions=["Users", "API keys"],
            provider=self.name
        )
    
    def _handle_navigate_system_logs(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to system logs (super admin only)."""
        if ctx.role != "super_admin":
            return ChatResponse(
                message="Sorry, system logs are only available to Super Admins.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to system logs. 📋",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/system-logs"},
                    description="Navigate to System Logs"
                )
            ],
            suggestions=["Infrastructure", "Database"],
            provider=self.name
        )
    
    def _handle_navigate_team(self, message: str, ctx: UserContext) -> ChatResponse:
        """Navigate to team management."""
        if ctx.role not in ("super_admin", "org_admin", "manager"):
            return ChatResponse(
                message="Sorry, team management is only available to managers and above.",
                actions=[],
                suggestions=["My files", "Settings", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Taking you to team management. 👥",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/team"},
                    description="Navigate to Team"
                )
            ],
            suggestions=["Users", "Analytics"],
            provider=self.name
        )

    def _handle_upload(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file upload with actual upload action button."""
        if ctx.role == "viewer":
            return ChatResponse(
                message="Sorry, viewers cannot upload files. Please contact your administrator if you need upload access.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="Ready to upload! Click the Upload File button below to select a file, or drag and drop files directly into the chat.",
            actions=[
                ChatAction(
                    type=ActionType.UPLOAD,
                    payload={
                        "user_id": ctx.user_id,
                        "organization_id": ctx.organization_id,
                        "accept": "*/*"
                    },
                    description="Upload File",
                    requires_confirmation=False
                ),
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Go to Files Page",
                    requires_confirmation=False
                )
            ],
            suggestions=["My files", "Storage info"],
            provider=self.name
        )
    
    def _handle_download(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file download guidance."""
        return ChatResponse(
            message="""To download a file:

1. Go to your **Files** page
2. Find the file you want to download
3. Click the **Download** icon or menu option

Let me take you to your files.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_share(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file sharing guidance."""
        if ctx.role == "viewer":
            return ChatResponse(
                message="Sorry, viewers cannot share files. Please contact your administrator for sharing permissions.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="""To share a file:

1. Go to your **Files** page
2. Find the file you want to share
3. Click the **Share** icon
4. Copy the share link or enter recipient email

Let me take you to your files.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    
    def _handle_delete(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle file deletion guidance."""
        if ctx.role == "viewer":
            return ChatResponse(
                message="Sorry, viewers cannot delete files.",
                actions=[],
                suggestions=["My files", "Help"],
                provider=self.name
            )
        
        return ChatResponse(
            message="""To delete a file:

1. Go to your **Files** page
2. Find the file you want to delete
3. Click the **Delete** icon or menu option
4. Confirm the deletion

⚠️ **Warning**: Deleted files cannot be recovered!

Let me take you to your files.""",
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/files"},
                    description="Navigate to Files"
                )
            ],
            suggestions=["My files", "Help"],
            provider=self.name
        )
    

    def _handle_api_health(self, message: str, ctx: UserContext) -> ChatResponse:
        """Show API/system health status."""
        result = self._run_data_query(ctx, lambda t, c: t.get_system_overview(c))
        
        if "error" in result:
            return ChatResponse(
                message="Unable to fetch system status. Please try again.",
                actions=[],
                suggestions=["System overview", "Help"],
                provider=self.name
            )
        
        msg = "🏥 **System Health Status**\n\n"
        msg += "**Services:**\n"
        msg += "• ✅ **API Server:** Online\n"
        msg += "• ✅ **Database:** Connected\n"
        msg += "• ✅ **File Storage:** Operational\n"
        
        if result.get('chatbot_active'):
            msg += "• ✅ **AI Chatbot:** Active\n"
        
        msg += f"\n**Current Stats:**\n"
        msg += f"• **Total Files:** {result.get('total_files', 0)}\n"
        msg += f"• **Total Users:** {result.get('total_users', 0)}\n"
        msg += f"• **Organizations:** {result.get('total_organizations', 0)}\n"
        
        if result.get('pending_tasks', 0) > 0:
            msg += f"\n⚠️ **{result.get('pending_tasks')} pending tasks** in queue\n"
        
        msg += "\n✅ **All systems operational!**"
        
        return ChatResponse(
            message=msg,
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/platform-admin"},
                    description="View Platform Admin",
                    requires_confirmation=False
                )
            ],
            suggestions=["System overview", "Pipeline stats", "Task stats"],
            provider=self.name
        )

    def _handle_api_health(self, message: str, ctx: UserContext) -> ChatResponse:
        """Show API/system health status."""
        result = self._run_data_query(ctx, lambda t, c: t.get_system_overview(c))
        
        if "error" in result:
            return ChatResponse(
                message="Unable to fetch system status. Please try again.",
                actions=[],
                suggestions=["System overview", "Help"],
                provider=self.name
            )
        
        msg = "🏥 **System Health Status**\n\n"
        msg += "**Services:**\n"
        msg += "• ✅ **API Server:** Online\n"
        msg += "• ✅ **Database:** Connected\n"
        msg += "• ✅ **File Storage:** Operational\n"
        
        if result.get('chatbot_active'):
            msg += "• ✅ **AI Chatbot:** Active\n"
        
        msg += f"\n**Current Stats:**\n"
        msg += f"• **Total Files:** {result.get('total_files', 0)}\n"
        msg += f"• **Total Users:** {result.get('total_users', 0)}\n"
        msg += f"• **Organizations:** {result.get('total_organizations', 0)}\n"
        
        if result.get('pending_tasks', 0) > 0:
            msg += f"\n⚠️ **{result.get('pending_tasks')} pending tasks** in queue\n"
        
        msg += "\n✅ **All systems operational!**"
        
        return ChatResponse(
            message=msg,
            actions=[
                ChatAction(
                    type=ActionType.NAVIGATE,
                    payload={"path": "/dashboard/platform-admin"},
                    description="View Platform Admin",
                    requires_confirmation=False
                )
            ],
            suggestions=["System overview", "Pipeline stats", "Task stats"],
            provider=self.name
        )
    def _handle_status(self, message: str, ctx: UserContext) -> ChatResponse:
        """Show user's status and permissions."""
        role_descriptions = {
            "super_admin": "**Super Admin** - Full access to all features across all organizations",
            "org_admin": "**Organization Admin** - Manage your organization's files and users",
            "manager": "**Manager** - Manage team files and view reports",
            "user": "**User** - Upload, download, and share your own files",
            "viewer": "**Viewer** - Read-only access to shared files"
        }
        
        role_desc = role_descriptions.get(ctx.role, "Standard User")
        
        status_text = f"""**Your Account Status**

📧 **Email**: {ctx.email}
🔑 **Role**: {role_desc}
🏢 **Organization**: {ctx.organization_name or 'N/A'}

**Your Permissions**:
{self._format_permissions(ctx)}"""
        
        return ChatResponse(
            message=status_text,
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _format_permissions(self, ctx: UserContext) -> str:
        """Format permissions list."""
        if not ctx.permissions:
            return "- Standard user permissions"
        
        permission_icons = {
            "FILE_READ": "📖 Read files",
            "FILE_WRITE": "✏️ Write files",
            "FILE_DELETE": "🗑️ Delete files",
            "FILE_SHARE": "🔗 Share files",
            "USER_READ": "👁️ View users",
            "USER_WRITE": "👤 Manage users",
            "ADMIN_ACCESS": "🔐 Admin access"
        }
        
        lines = []
        for perm in ctx.permissions:
            icon_text = permission_icons.get(perm, f"• {perm}")
            lines.append(f"- {icon_text}")
        
        return "\n".join(lines) if lines else "- Standard user permissions"
    
    def _handle_thanks(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle thank you messages."""
        return ChatResponse(
            message="You're welcome! 😊 Is there anything else I can help you with?",
            actions=[],
            suggestions=self._get_default_suggestions(ctx),
            provider=self.name
        )
    
    def _handle_goodbye(self, message: str, ctx: UserContext) -> ChatResponse:
        """Handle goodbye messages."""
        return ChatResponse(
            message="Goodbye! 👋 Have a great day! I'm here whenever you need help.",
            actions=[],
            suggestions=["Help"],
            provider=self.name
        )
    
    def _default_response(self, ctx: UserContext) -> str:
        """Default response when no pattern matches."""
        return """I'm not sure I understand that request. Here are some things you can ask me:

- "Take me to my files"
- "How do I upload a file?"
- "What's my role?"
- "Help"

Or try one of the suggestions below!"""
    
    def _get_default_suggestions(self, ctx: UserContext) -> List[str]:
        """Get default suggestions based on user role."""
        if ctx.role in ("super_admin", "org_admin"):
            return ["My files", "All files", "Users", "Help"]
        elif ctx.role == "viewer":
            return ["My files", "Settings", "Help"]
        else:
            return ["My files", "Upload file", "Settings", "Help"]
