"""
Engine output contracts - Stable JSON shapes for UI integration.

RESPONSABILIDAD:
Definir las estructuras de output del pipeline.
Estas estructuras son un CONTRATO PÚBLICO: cambiarlas
implica un breaking change para cualquier UI que consuma el sistema.

SEPARACIÓN INTENCIONAL DE orchestrator.py:
La lógica del pipeline (cómo se conectan las capas) vive en orchestrator.py.
Los contratos de output (qué forma tienen los resultados) viven aquí.
Esto permite que la UI importe solo engine.models sin traer el pipeline entero.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from core.models import Sport


@dataclass
class PipelineResult:
    """
    Output final del Orchestrator.

    Este es el contrato que cualquier UI futura consume.
    Cambiar esta estructura = breaking change.

    CAMPOS:
        run_id:         ID único del run (sport_league_date_HHMMSS)
        sport:          Deporte analizado
        league:         Liga analizada
        date:           Fecha del análisis
        timestamp:      Momento de ejecución
        approved_picks: Lista de picks listos para apostar (dicts JSON-ready)
        rejected_picks: Lista de picks rechazados + razón
        risk_status:    Estado del portfolio de riesgo
        pipeline_stats: Métricas de ejecución para monitoring
    """
    # Metadata del run
    run_id: str
    sport: Sport
    league: str
    date: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Picks aprobados (listos para apostar)
    approved_picks: List[Dict] = field(default_factory=list)

    # Picks rechazados por riesgo (con razón)
    rejected_picks: List[Dict] = field(default_factory=list)

    # Status del portfolio
    risk_status: Dict = field(default_factory=dict)

    # Métricas del pipeline (para monitoring/debugging)
    pipeline_stats: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """
        Serializa a Dict JSON-ready.

        GARANTÍA: El output de este método debe poder pasarse
        directamente a json.dumps() sin custom encoders.
        """
        return {
            "run_id": self.run_id,
            "sport": self.sport.value,
            "league": self.league,
            "date": self.date,
            "timestamp": self.timestamp.isoformat(),
            "approved_picks": self.approved_picks,
            "rejected_picks": self.rejected_picks,
            "risk_status": self.risk_status,
            "pipeline_stats": self.pipeline_stats
        }
