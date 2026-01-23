# Self-Healing AI System
# Uses CrewAI agents to detect, diagnose, and fix chatbot errors

from .agents import (
    SelfHealingSystem,
    MonitorAgent,
    DiagnosticAgent,
    FixAgent,
    ErrorType,
    FixType,
    ErrorReport,
    FixProposal,
)

from .advanced_healing import (
    AdvancedSelfHealingSystem,
    HealingConfig,
    LearnedPattern,
    FixResult,
    get_healer,
)

__all__ = [
    # Basic system
    'SelfHealingSystem',
    'MonitorAgent',
    'DiagnosticAgent',
    'FixAgent',
    'ErrorType',
    'FixType',
    'ErrorReport',
    'FixProposal',
    # Advanced system
    'AdvancedSelfHealingSystem',
    'HealingConfig',
    'LearnedPattern',
    'FixResult',
    'get_healer',
]
