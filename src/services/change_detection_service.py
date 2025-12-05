"""
Change Detection Service - Detects and quantifies changes between file versions.

This service implements delta extraction algorithms that enable:
1. Efficient change detection without full file comparison
2. Statistical analysis of data distribution changes
3. Feature drift detection for ML models

Research relevance: Incremental View Maintenance (IVM), Delta Queries
"""

import hashlib
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import numpy as np
from io import StringIO

from services.base_service import BaseService
from entities.data_delta import DataDelta, DeltaType, ProcessingStrategy
from repositories.delta_repository import DeltaRepo

logger = logging.getLogger(__name__)


class ChangeDetectionService(BaseService[DeltaRepo]):
    """
    Service for detecting and analyzing changes in uploaded data files.
    
    Implements multiple change detection strategies:
    1. Hash-based: Fast detection if anything changed
    2. Row-level: Identify specific inserted/deleted/updated rows
    3. Statistical: Measure distribution changes
    4. Structural: Detect schema changes
    """
    
    def __init__(self, repo: DeltaRepo) -> None:
        super().__init__(repo=repo)
        self.min_change_threshold = 0.01  # 1% change minimum to trigger processing
        
    async def detect_changes(
        self, 
        file_id: str, 
        new_content: bytes, 
        old_content: Optional[bytes] = None,
        content_type: str = "text/csv"
    ) -> DataDelta:
        """
        Main entry point for change detection.
        
        Args:
            file_id: ID of the file being updated
            new_content: New file content as bytes
            old_content: Previous file content (None for new files)
            content_type: MIME type of the file
            
        Returns:
            DataDelta object with detected changes
        """
        start_time = datetime.utcnow()
        
        # Fast path: new file
        if old_content is None:
            return await self._create_initial_delta(file_id, new_content, content_type)
        
        # Hash-based quick check
        old_hash = self._compute_hash(old_content)
        new_hash = self._compute_hash(new_content)
        
        if old_hash == new_hash:
            logger.info(f"No changes detected for file {file_id}")
            return await self._create_no_change_delta(file_id)
        
        # Detailed change detection based on content type
        if content_type in ["text/csv", "application/csv"]:
            delta = await self._detect_tabular_changes(file_id, old_content, new_content)
        elif content_type == "application/json":
            delta = await self._detect_json_changes(file_id, old_content, new_content)
        else:
            delta = await self._detect_binary_changes(file_id, old_content, new_content)
        
        # Calculate detection time
        delta.detection_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        delta.delta_hash = new_hash
        
        # Save delta
        saved_delta = self.repo.create(delta)
        logger.info(f"Detected changes for file {file_id}: {delta.delta_type}, magnitude={delta.change_magnitude:.3f}")
        
        return saved_delta
    
    async def _detect_tabular_changes(
        self, 
        file_id: str, 
        old_content: bytes, 
        new_content: bytes
    ) -> DataDelta:
        """
        Detect changes in CSV/tabular data files.
        
        Implements:
        - Row-level diff (inserted, deleted, updated)
        - Column schema changes
        - Statistical distribution changes
        """
        try:
            import pandas as pd
            
            old_df = pd.read_csv(StringIO(old_content.decode('utf-8')))
            new_df = pd.read_csv(StringIO(new_content.decode('utf-8')))
            
            delta = DataDelta(file_id=file_id)
            
            # Row counts
            delta.rows_before = len(old_df)
            delta.rows_after = len(new_df)
            
            # Schema changes
            old_cols = set(old_df.columns)
            new_cols = set(new_df.columns)
            
            delta.columns_added = list(new_cols - old_cols)
            delta.columns_removed = list(old_cols - new_cols)
            
            if delta.columns_added or delta.columns_removed:
                delta.delta_type = DeltaType.SCHEMA.value
            
            # Row-level changes (using index or first column as key)
            common_cols = list(old_cols & new_cols)
            if common_cols:
                # Identify key column (first column or 'id' if exists)
                key_col = 'id' if 'id' in common_cols else common_cols[0]
                
                old_keys = set(old_df[key_col].astype(str))
                new_keys = set(new_df[key_col].astype(str))
                
                inserted_keys = new_keys - old_keys
                deleted_keys = old_keys - new_keys
                common_keys = old_keys & new_keys
                
                delta.rows_inserted = len(inserted_keys)
                delta.rows_deleted = len(deleted_keys)
                
                # Check for updates in common rows
                if common_keys:
                    old_common = old_df[old_df[key_col].astype(str).isin(common_keys)].set_index(key_col)
                    new_common = new_df[new_df[key_col].astype(str).isin(common_keys)].set_index(key_col)
                    
                    # Find modified columns
                    modified_cols = []
                    for col in common_cols:
                        if col != key_col:
                            try:
                                if not old_common[col].equals(new_common[col]):
                                    modified_cols.append(col)
                            except:
                                pass
                    
                    delta.columns_modified = modified_cols
                    delta.rows_updated = len([k for k in common_keys if any(
                        str(old_common.loc[k, c]) != str(new_common.loc[k, c]) 
                        for c in modified_cols if c in old_common.columns and c in new_common.columns
                    )]) if modified_cols else 0
            
            # Determine delta type
            if delta.rows_inserted > 0 and delta.rows_deleted == 0 and delta.rows_updated == 0:
                delta.delta_type = DeltaType.INSERT.value
            elif delta.rows_deleted > 0 and delta.rows_inserted == 0 and delta.rows_updated == 0:
                delta.delta_type = DeltaType.DELETE.value
            elif delta.rows_updated > 0 or (delta.rows_inserted > 0 and delta.rows_deleted > 0):
                delta.delta_type = DeltaType.UPDATE.value
            
            # Calculate statistical metrics
            delta.change_magnitude = self._calculate_change_magnitude(delta)
            delta.entropy_delta = await self._calculate_entropy_delta(old_df, new_df, common_cols)
            delta.feature_drift_score = await self._calculate_feature_drift(old_df, new_df, common_cols)
            
            # Create compact summary
            delta.delta_summary = {
                "total_changes": delta.rows_inserted + delta.rows_deleted + delta.rows_updated,
                "schema_changed": bool(delta.columns_added or delta.columns_removed),
                "key_column": key_col if common_cols else None,
                "sample_insertions": list(inserted_keys)[:5] if inserted_keys else [],
                "sample_deletions": list(deleted_keys)[:5] if deleted_keys else []
            }
            
            return delta
            
        except Exception as e:
            logger.error(f"Error detecting tabular changes: {e}")
            return await self._detect_binary_changes(file_id, old_content, new_content)
    
    async def _detect_json_changes(
        self, 
        file_id: str, 
        old_content: bytes, 
        new_content: bytes
    ) -> DataDelta:
        """Detect changes in JSON files using recursive diff."""
        try:
            old_data = json.loads(old_content.decode('utf-8'))
            new_data = json.loads(new_content.decode('utf-8'))
            
            delta = DataDelta(file_id=file_id)
            
            # Calculate JSON diff
            diff_result = self._json_diff(old_data, new_data)
            
            delta.rows_inserted = diff_result['additions']
            delta.rows_deleted = diff_result['deletions']
            delta.rows_updated = diff_result['modifications']
            delta.delta_type = DeltaType.UPDATE.value
            
            delta.change_magnitude = diff_result['change_ratio']
            delta.delta_summary = {
                "paths_added": diff_result['added_paths'][:10],
                "paths_removed": diff_result['removed_paths'][:10],
                "paths_modified": diff_result['modified_paths'][:10]
            }
            
            return delta
            
        except Exception as e:
            logger.error(f"Error detecting JSON changes: {e}")
            return await self._detect_binary_changes(file_id, old_content, new_content)
    
    async def _detect_binary_changes(
        self, 
        file_id: str, 
        old_content: bytes, 
        new_content: bytes
    ) -> DataDelta:
        """Fallback change detection for binary files."""
        delta = DataDelta(file_id=file_id)
        delta.delta_type = DeltaType.FULL.value
        delta.rows_before = len(old_content)
        delta.rows_after = len(new_content)
        
        # Size-based change magnitude
        size_diff = abs(len(new_content) - len(old_content))
        delta.change_magnitude = min(size_diff / max(len(old_content), 1), 1.0)
        
        delta.delta_summary = {
            "size_before": len(old_content),
            "size_after": len(new_content),
            "size_delta": len(new_content) - len(old_content)
        }
        
        return delta
    
    async def _create_initial_delta(
        self, 
        file_id: str, 
        content: bytes, 
        content_type: str
    ) -> DataDelta:
        """Create delta for initial file upload (no previous version)."""
        delta = DataDelta(file_id=file_id)
        delta.delta_type = DeltaType.INSERT.value
        delta.version_before = 0
        delta.version_after = 1
        delta.rows_before = 0
        delta.change_magnitude = 1.0  # Complete change
        delta.delta_hash = self._compute_hash(content)
        
        # Try to count rows for tabular data
        if content_type in ["text/csv", "application/csv"]:
            try:
                import pandas as pd
                df = pd.read_csv(StringIO(content.decode('utf-8')))
                delta.rows_after = len(df)
                delta.rows_inserted = len(df)
                delta.columns_added = list(df.columns)
            except:
                delta.rows_after = len(content)
                delta.rows_inserted = len(content)
        else:
            delta.rows_after = len(content)
            delta.rows_inserted = len(content)
        
        saved_delta = self.repo.create(delta)
        return saved_delta
    
    async def _create_no_change_delta(self, file_id: str) -> DataDelta:
        """Create delta indicating no changes detected."""
        delta = DataDelta(file_id=file_id)
        delta.delta_type = DeltaType.UPDATE.value
        delta.change_magnitude = 0.0
        delta.processing_strategy = ProcessingStrategy.SKIP.value
        delta.strategy_confidence = 1.0
        delta.is_processed = True
        delta.processed_at = datetime.utcnow()
        
        saved_delta = self.repo.create(delta)
        return saved_delta
    
    def _compute_hash(self, content: bytes) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content).hexdigest()
    
    def _calculate_change_magnitude(self, delta: DataDelta) -> float:
        """Calculate overall change magnitude (0-1 scale)."""
        total_rows = max(delta.rows_before, delta.rows_after, 1)
        changed_rows = delta.rows_inserted + delta.rows_deleted + delta.rows_updated
        
        row_change = changed_rows / total_rows
        
        # Schema changes add to magnitude
        schema_change = 0.0
        if delta.columns_added or delta.columns_removed:
            total_cols = max(
                len(delta.columns_added or []) + len(delta.columns_removed or []),
                1
            )
            schema_change = 0.3  # Schema changes are significant
        
        return min(row_change + schema_change, 1.0)
    
    async def _calculate_entropy_delta(
        self, 
        old_df, 
        new_df, 
        common_cols: List[str]
    ) -> float:
        """
        Calculate change in data entropy/distribution.
        Higher values indicate distribution shift.
        """
        try:
            entropy_diffs = []
            
            for col in common_cols[:10]:  # Limit to first 10 columns for performance
                try:
                    if old_df[col].dtype in ['int64', 'float64'] and new_df[col].dtype in ['int64', 'float64']:
                        old_normalized = (old_df[col] - old_df[col].mean()) / (old_df[col].std() + 1e-8)
                        new_normalized = (new_df[col] - new_df[col].mean()) / (new_df[col].std() + 1e-8)
                        
                        # Calculate histogram difference
                        old_hist, _ = np.histogram(old_normalized.dropna(), bins=20, density=True)
                        new_hist, _ = np.histogram(new_normalized.dropna(), bins=20, density=True)
                        
                        # KL divergence approximation
                        old_hist = old_hist + 1e-8
                        new_hist = new_hist + 1e-8
                        kl_div = np.sum(new_hist * np.log(new_hist / old_hist))
                        entropy_diffs.append(min(abs(kl_div), 10) / 10)  # Normalize to 0-1
                except:
                    pass
            
            return np.mean(entropy_diffs) if entropy_diffs else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating entropy delta: {e}")
            return 0.0
    
    async def _calculate_feature_drift(
        self, 
        old_df, 
        new_df, 
        common_cols: List[str]
    ) -> float:
        """
        Calculate feature drift score using Population Stability Index (PSI).
        Used to detect if ML features have shifted significantly.
        """
        try:
            psi_scores = []
            
            for col in common_cols[:10]:
                try:
                    if old_df[col].dtype in ['int64', 'float64']:
                        # Calculate PSI
                        psi = self._calculate_psi(old_df[col].dropna(), new_df[col].dropna())
                        psi_scores.append(psi)
                except:
                    pass
            
            return np.mean(psi_scores) if psi_scores else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating feature drift: {e}")
            return 0.0
    
    def _calculate_psi(self, expected, actual, buckets: int = 10) -> float:
        """Calculate Population Stability Index between two distributions."""
        try:
            # Create buckets based on expected distribution
            breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
            breakpoints = np.unique(breakpoints)
            
            expected_counts = np.histogram(expected, bins=breakpoints)[0]
            actual_counts = np.histogram(actual, bins=breakpoints)[0]
            
            # Avoid division by zero
            expected_percents = (expected_counts + 1) / (len(expected) + buckets)
            actual_percents = (actual_counts + 1) / (len(actual) + buckets)
            
            psi = np.sum((actual_percents - expected_percents) * np.log(actual_percents / expected_percents))
            
            return min(psi, 1.0)  # Cap at 1.0
            
        except:
            return 0.0
    
    def _json_diff(self, old_data: Any, new_data: Any, path: str = "") -> Dict[str, Any]:
        """Recursive JSON diff calculation."""
        result = {
            'additions': 0,
            'deletions': 0,
            'modifications': 0,
            'added_paths': [],
            'removed_paths': [],
            'modified_paths': [],
            'change_ratio': 0.0
        }
        
        if type(old_data) != type(new_data):
            result['modifications'] = 1
            result['modified_paths'].append(path or "root")
            result['change_ratio'] = 1.0
            return result
        
        if isinstance(old_data, dict):
            old_keys = set(old_data.keys())
            new_keys = set(new_data.keys())
            
            for key in new_keys - old_keys:
                result['additions'] += 1
                result['added_paths'].append(f"{path}.{key}" if path else key)
            
            for key in old_keys - new_keys:
                result['deletions'] += 1
                result['removed_paths'].append(f"{path}.{key}" if path else key)
            
            for key in old_keys & new_keys:
                sub_result = self._json_diff(
                    old_data[key], 
                    new_data[key], 
                    f"{path}.{key}" if path else key
                )
                result['additions'] += sub_result['additions']
                result['deletions'] += sub_result['deletions']
                result['modifications'] += sub_result['modifications']
                result['added_paths'].extend(sub_result['added_paths'])
                result['removed_paths'].extend(sub_result['removed_paths'])
                result['modified_paths'].extend(sub_result['modified_paths'])
        
        elif isinstance(old_data, list):
            len_diff = len(new_data) - len(old_data)
            if len_diff > 0:
                result['additions'] = len_diff
            elif len_diff < 0:
                result['deletions'] = -len_diff
            
            for i, (old_item, new_item) in enumerate(zip(old_data, new_data)):
                sub_result = self._json_diff(old_item, new_item, f"{path}[{i}]")
                result['modifications'] += sub_result['modifications']
                result['modified_paths'].extend(sub_result['modified_paths'])
        
        elif old_data != new_data:
            result['modifications'] = 1
            result['modified_paths'].append(path or "root")
        
        total_changes = result['additions'] + result['deletions'] + result['modifications']
        result['change_ratio'] = min(total_changes / max(total_changes + 10, 1), 1.0)
        
        return result
