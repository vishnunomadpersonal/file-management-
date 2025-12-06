"""
Model Versioning System - Track, Store, and Rollback ML Models.

Provides:
- Versioned model storage
- Automatic backup before updates
- Rollback capability
- Model comparison
- Audit trail for model changes
"""

import os
import json
import shutil
import hashlib
import pickle
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

MODEL_BASE_DIR = os.environ.get("MODEL_BASE_DIR", "/var/www/models")
MAX_VERSIONS_TO_KEEP = int(os.environ.get("MAX_MODEL_VERSIONS", "10"))


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ModelMetadata:
    """Metadata for a model version."""
    model_name: str
    version: int
    created_at: str
    training_strategy: str
    samples_used: int
    accuracy: Optional[float]
    precision: Optional[float]
    recall: Optional[float]
    f1_score: Optional[float]
    training_time_seconds: float
    model_hash: str
    model_size_bytes: int
    parent_version: Optional[int]
    delta_id: Optional[str]
    custom_metrics: Dict[str, Any]
    is_active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModelMetadata":
        return cls(**data)


@dataclass
class ModelVersion:
    """Represents a specific model version."""
    metadata: ModelMetadata
    model_path: str
    
    @property
    def version(self) -> int:
        return self.metadata.version
    
    @property
    def is_active(self) -> bool:
        return self.metadata.is_active


# ============================================================================
# MODEL VERSION MANAGER
# ============================================================================

class ModelVersionManager:
    """
    Manages versioned storage of ML models.
    
    Features:
    - Automatic versioning on save
    - Keeps last N versions
    - Rollback to any previous version
    - Model comparison
    - Metadata tracking
    """
    
    def __init__(self, model_name: str, base_dir: str = MODEL_BASE_DIR):
        self.model_name = model_name
        self.base_dir = Path(base_dir) / model_name
        self.metadata_file = self.base_dir / "metadata.json"
        
        # Create directories if needed
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "versions").mkdir(exist_ok=True)
        
        # Load existing metadata
        self.versions: Dict[int, ModelMetadata] = {}
        self.current_version: Optional[int] = None
        self._load_metadata()
    
    def _load_metadata(self):
        """Load metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    data = json.load(f)
                    self.current_version = data.get('current_version')
                    for v_data in data.get('versions', []):
                        meta = ModelMetadata.from_dict(v_data)
                        self.versions[meta.version] = meta
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")
    
    def _save_metadata(self):
        """Save metadata to disk."""
        try:
            data = {
                'model_name': self.model_name,
                'current_version': self.current_version,
                'versions': [v.to_dict() for v in self.versions.values()]
            }
            with open(self.metadata_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
    
    def _get_version_path(self, version: int) -> Path:
        """Get the path for a specific version."""
        return self.base_dir / "versions" / f"v{version:04d}.pkl"
    
    def _compute_model_hash(self, model: Any) -> str:
        """Compute a hash of the model for integrity checking."""
        try:
            model_bytes = pickle.dumps(model)
            return hashlib.sha256(model_bytes).hexdigest()[:16]
        except:
            return "unknown"
    
    def _get_next_version(self) -> int:
        """Get the next version number."""
        if not self.versions:
            return 1
        return max(self.versions.keys()) + 1
    
    def save_version(
        self,
        model: Any,
        training_strategy: str,
        samples_used: int,
        accuracy: Optional[float] = None,
        precision: Optional[float] = None,
        recall: Optional[float] = None,
        f1_score: Optional[float] = None,
        training_time_seconds: float = 0,
        delta_id: Optional[str] = None,
        custom_metrics: Optional[Dict[str, Any]] = None,
        make_active: bool = True
    ) -> ModelMetadata:
        """
        Save a new version of the model.
        
        Args:
            model: The model object to save
            training_strategy: How the model was trained (full, incremental, partial)
            samples_used: Number of training samples
            accuracy: Model accuracy score
            precision: Model precision score
            recall: Model recall score
            f1_score: Model F1 score
            training_time_seconds: Time taken to train
            delta_id: ID of the delta that triggered training
            custom_metrics: Any additional metrics
            make_active: Whether to make this the active version
            
        Returns:
            ModelMetadata for the new version
        """
        version = self._get_next_version()
        version_path = self._get_version_path(version)
        
        # Serialize model
        model_bytes = pickle.dumps(model)
        model_hash = hashlib.sha256(model_bytes).hexdigest()[:16]
        
        # Create metadata
        metadata = ModelMetadata(
            model_name=self.model_name,
            version=version,
            created_at=datetime.utcnow().isoformat(),
            training_strategy=training_strategy,
            samples_used=samples_used,
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            training_time_seconds=training_time_seconds,
            model_hash=model_hash,
            model_size_bytes=len(model_bytes),
            parent_version=self.current_version,
            delta_id=delta_id,
            custom_metrics=custom_metrics or {},
            is_active=make_active
        )
        
        # Save model file
        with open(version_path, 'wb') as f:
            f.write(model_bytes)
        
        # Update metadata
        self.versions[version] = metadata
        
        if make_active:
            # Deactivate previous active version
            if self.current_version and self.current_version in self.versions:
                self.versions[self.current_version].is_active = False
            self.current_version = version
        
        self._save_metadata()
        
        # Cleanup old versions
        self._cleanup_old_versions()
        
        logger.info(f"Saved model version {version} for {self.model_name}")
        
        return metadata
    
    def load_version(self, version: Optional[int] = None) -> Optional[Any]:
        """
        Load a specific model version.
        
        Args:
            version: Version to load. If None, loads current active version.
            
        Returns:
            The model object, or None if not found.
        """
        if version is None:
            version = self.current_version
        
        if version is None:
            logger.warning(f"No version specified and no active version for {self.model_name}")
            return None
        
        version_path = self._get_version_path(version)
        
        if not version_path.exists():
            logger.error(f"Version file not found: {version_path}")
            return None
        
        try:
            with open(version_path, 'rb') as f:
                model = pickle.load(f)
            
            # Verify hash if we have metadata
            if version in self.versions:
                expected_hash = self.versions[version].model_hash
                actual_hash = self._compute_model_hash(model)
                if actual_hash != expected_hash and expected_hash != "unknown":
                    logger.warning(f"Model hash mismatch for version {version}")
            
            return model
        except Exception as e:
            logger.error(f"Failed to load version {version}: {e}")
            return None
    
    def rollback_to_version(self, version: int) -> bool:
        """
        Rollback to a specific version.
        
        Makes the specified version active.
        
        Args:
            version: Version to rollback to
            
        Returns:
            True if successful
        """
        if version not in self.versions:
            logger.error(f"Version {version} not found")
            return False
        
        version_path = self._get_version_path(version)
        if not version_path.exists():
            logger.error(f"Version file not found: {version_path}")
            return False
        
        # Deactivate current version
        if self.current_version and self.current_version in self.versions:
            self.versions[self.current_version].is_active = False
        
        # Activate target version
        self.versions[version].is_active = True
        self.current_version = version
        
        self._save_metadata()
        
        logger.info(f"Rolled back {self.model_name} to version {version}")
        
        return True
    
    def get_version_history(self) -> List[ModelMetadata]:
        """Get the version history, newest first."""
        return sorted(
            self.versions.values(),
            key=lambda m: m.version,
            reverse=True
        )
    
    def get_active_version(self) -> Optional[ModelMetadata]:
        """Get metadata for the currently active version."""
        if self.current_version and self.current_version in self.versions:
            return self.versions[self.current_version]
        return None
    
    def compare_versions(
        self, 
        version1: int, 
        version2: int
    ) -> Dict[str, Any]:
        """
        Compare two model versions.
        
        Returns a dict with differences in metrics.
        """
        if version1 not in self.versions or version2 not in self.versions:
            return {"error": "One or both versions not found"}
        
        m1 = self.versions[version1]
        m2 = self.versions[version2]
        
        def diff(v1, v2):
            if v1 is None or v2 is None:
                return None
            return v2 - v1
        
        return {
            "version1": version1,
            "version2": version2,
            "accuracy_diff": diff(m1.accuracy, m2.accuracy),
            "precision_diff": diff(m1.precision, m2.precision),
            "recall_diff": diff(m1.recall, m2.recall),
            "f1_diff": diff(m1.f1_score, m2.f1_score),
            "samples_diff": m2.samples_used - m1.samples_used,
            "training_time_diff": m2.training_time_seconds - m1.training_time_seconds,
            "size_diff_bytes": m2.model_size_bytes - m1.model_size_bytes,
            "strategy_v1": m1.training_strategy,
            "strategy_v2": m2.training_strategy,
        }
    
    def _cleanup_old_versions(self):
        """Remove old versions beyond MAX_VERSIONS_TO_KEEP."""
        if len(self.versions) <= MAX_VERSIONS_TO_KEEP:
            return
        
        # Sort by version number
        sorted_versions = sorted(self.versions.keys())
        
        # Keep the active version and most recent versions
        versions_to_remove = sorted_versions[:-MAX_VERSIONS_TO_KEEP]
        
        # Don't remove the active version
        if self.current_version in versions_to_remove:
            versions_to_remove.remove(self.current_version)
        
        for version in versions_to_remove:
            version_path = self._get_version_path(version)
            try:
                if version_path.exists():
                    version_path.unlink()
                del self.versions[version]
                logger.info(f"Cleaned up old version {version} of {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to cleanup version {version}: {e}")
        
        self._save_metadata()
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the model versioning."""
        active = self.get_active_version()
        return {
            "model_name": self.model_name,
            "total_versions": len(self.versions),
            "current_version": self.current_version,
            "active_version_info": active.to_dict() if active else None,
            "max_versions_kept": MAX_VERSIONS_TO_KEEP,
            "storage_path": str(self.base_dir),
            "versions": [
                {
                    "version": v.version,
                    "created_at": v.created_at,
                    "strategy": v.training_strategy,
                    "accuracy": v.accuracy,
                    "is_active": v.is_active
                }
                for v in self.get_version_history()
            ]
        }


# ============================================================================
# GLOBAL MANAGERS (lazy initialization)
# ============================================================================

_managers: Dict[str, ModelVersionManager] = {}


def get_model_manager(model_name: str) -> ModelVersionManager:
    """Get or create a model version manager for the given model name."""
    if model_name not in _managers:
        _managers[model_name] = ModelVersionManager(model_name)
    return _managers[model_name]


# Pre-defined managers for common models
def get_router_model_manager() -> ModelVersionManager:
    """Get the manager for the learned router model."""
    return get_model_manager("learned_router")


def get_incremental_model_manager() -> ModelVersionManager:
    """Get the manager for the incremental ML model."""
    return get_model_manager("incremental_model")


def get_cost_model_manager() -> ModelVersionManager:
    """Get the manager for the cost optimizer model."""
    return get_model_manager("cost_optimizer")
