"""
engine/ — Pipeline core package

Exports:
    Orchestrator: Pipeline central
    PipelineResult: Output contract (estable para UI)
"""
from engine.orchestrator import Orchestrator
from engine.models import PipelineResult

__all__ = ["Orchestrator", "PipelineResult"]
