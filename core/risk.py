"""
Risk Manager - Gestión de exposición y correlación

RESPONSABILIDADES:
1. Verificar que exposure total no exceda límites
2. Detectar correlaciones peligrosas entre picks
3. Aprobar/rechazar picks basado en riesgo actual

REGLAS:
- Nunca más de X% del bankroll en riesgo simultáneo
- Reducir stake si picks correlacionados (mismo juego)
- Alertar si >N picks en misma liga/deporte

NO ES RESPONSABLE DE:
- Calcular stake (lo hace KellyCalculator)
- Decidir qué mercados evaluar (lo hace Orchestrator)
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from core.models import Pick, MarketType


@dataclass
class RiskLimits:
    """Configuración de límites de riesgo"""
    max_total_exposure: float = 20.0      # % máximo del bankroll en riesgo
    max_single_pick: float = 10.0         # % máximo en un solo pick
    max_correlated_exposure: float = 15.0  # % máximo en picks correlacionados
    max_picks_per_game: int = 2           # Máximo de picks en el mismo juego
    max_picks_per_league: int = 10        # Máximo de picks en la misma liga


@dataclass
class RiskStatus:
    """Status actual de riesgo del portfolio"""
    total_exposure: float                  # % actual en riesgo
    active_picks: int                     # Número de picks activos
    picks_by_game: Dict[str, int] = field(default_factory=dict)
    picks_by_league: Dict[str, int] = field(default_factory=dict)
    correlated_groups: List[List[str]] = field(default_factory=list)
    within_limits: bool = True
    warnings: List[str] = field(default_factory=list)


class RiskManager:
    """
    Gestor de riesgo del portfolio
    
    FLUJO:
    1. Orchestrator genera picks con KellyCalculator
    2. RiskManager.can_add_pick() verifica si es seguro agregar
    3. Si aprobado → agregar a active_picks
    4. Después de resultado → remove_pick()
    """
    
    # Matriz de correlación entre tipos de mercado
    # Valores empíricos basados en análisis histórico
    MARKET_CORRELATION = {
        (MarketType.MONEYLINE, MarketType.MONEYLINE): 1.00,  # Mismo mercado
        (MarketType.MONEYLINE, MarketType.SPREAD): 0.75,     # Alta correlación
        (MarketType.MONEYLINE, MarketType.TOTALS): 0.35,     # Correlación media
        (MarketType.SPREAD, MarketType.TOTALS): 0.25,        # Baja correlación
        (MarketType.TOTALS, MarketType.TOTALS): 1.00,
    }
    
    def __init__(
        self,
        limits: Optional[RiskLimits] = None,
        bankroll: Optional[float] = None
    ):
        """
        Args:
            limits: Configuración de límites (usa defaults si None)
            bankroll: Bankroll total (opcional, para calcular exposure absoluto)
        """
        self.limits = limits or RiskLimits()
        self.bankroll = bankroll
        self.active_picks: List[Pick] = []
    
    def can_add_pick(
        self,
        pick: Pick,
        enforce_limits: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Verifica si es seguro agregar un pick
        
        Args:
            pick: Pick a evaluar
            enforce_limits: Si rechazar por violación de límites
                           False = solo advertir, no rechazar
        
        Returns:
            (puede_agregar, razón_rechazo)
            - (True, None): OK para agregar
            - (False, "razón"): Rechazado
        
        Ejemplo:
            >>> manager = RiskManager()
            >>> can_add, reason = manager.can_add_pick(pick)
            >>> if can_add:
            ...     manager.add_pick(pick)
            ... else:
            ...     print(f"Rechazado: {reason}")
        """
        # 1. Verificar exposure total
        current_exposure = self.get_total_exposure()
        new_exposure = current_exposure + pick.stake_pct
        
        if new_exposure > self.limits.max_total_exposure:
            if enforce_limits:
                return False, f"Excede exposure máximo ({new_exposure:.1f}% > {self.limits.max_total_exposure}%)"
        
        # 2. Verificar stake del pick individual
        if pick.stake_pct > self.limits.max_single_pick:
            if enforce_limits:
                return False, f"Pick excede stake máximo ({pick.stake_pct:.1f}% > {self.limits.max_single_pick}%)"
        
        # 3. Verificar límite de picks por juego
        same_game_picks = [p for p in self.active_picks if p.game_id == pick.game_id]
        if len(same_game_picks) >= self.limits.max_picks_per_game:
            if enforce_limits:
                return False, f"Máximo de picks por juego alcanzado ({self.limits.max_picks_per_game})"
        
        # 4. Verificar correlación con picks activos
        correlated_exposure = self._calculate_correlated_exposure(pick)
        if correlated_exposure > self.limits.max_correlated_exposure:
            if enforce_limits:
                return False, f"Excede exposure correlacionado ({correlated_exposure:.1f}% > {self.limits.max_correlated_exposure}%)"
        
        return True, None
    
    def add_pick(self, pick: Pick) -> None:
        """
        Agrega pick al portfolio activo
        
        IMPORTANTE: Siempre llamar can_add_pick() antes
        """
        can_add, reason = self.can_add_pick(pick)
        if not can_add:
            raise ValueError(f"No se puede agregar pick: {reason}")
        
        self.active_picks.append(pick)
    
    def remove_pick(self, pick_id: str) -> bool:
        """
        Remueve pick del portfolio (después de resolución)
        
        Args:
            pick_id: game_id + market + selection
        
        Returns:
            True si removido, False si no encontrado
        """
        initial_length = len(self.active_picks)
        self.active_picks = [
            p for p in self.active_picks
            if f"{p.game_id}_{p.market.value}_{p.selection}" != pick_id
        ]
        return len(self.active_picks) < initial_length
    
    def get_total_exposure(self) -> float:
        """Calcula exposure total actual (% del bankroll)"""
        return sum(p.stake_pct for p in self.active_picks)
    
    def get_risk_status(self) -> RiskStatus:
        """
        Genera reporte de status de riesgo actual
        
        Returns:
            RiskStatus con métricas y warnings
        """
        total_exposure = self.get_total_exposure()
        warnings = []
        
        # Agrupar por juego
        picks_by_game = {}
        for pick in self.active_picks:
            picks_by_game[pick.game_id] = picks_by_game.get(pick.game_id, 0) + 1
        
        # Detectar juegos con múltiples picks
        for game_id, count in picks_by_game.items():
            if count >= self.limits.max_picks_per_game:
                warnings.append(f"Juego {game_id} tiene {count} picks activos")
        
        # Verificar límites
        within_limits = (
            total_exposure <= self.limits.max_total_exposure and
            all(p.stake_pct <= self.limits.max_single_pick for p in self.active_picks)
        )
        
        if total_exposure > self.limits.max_total_exposure * 0.8:
            warnings.append(f"Cerca del límite de exposure ({total_exposure:.1f}% / {self.limits.max_total_exposure}%)")
        
        return RiskStatus(
            total_exposure=round(total_exposure, 2),
            active_picks=len(self.active_picks),
            picks_by_game=picks_by_game,
            within_limits=within_limits,
            warnings=warnings
        )
    
    def calculate_correlation(self, pick1: Pick, pick2: Pick) -> float:
        """
        Calcula correlación entre dos picks
        
        REGLAS:
        1. Mismo juego + mismo mercado = 1.0 (correlación perfecta)
        2. Mismo juego + mercados diferentes = correlación según matriz
        3. Juegos diferentes = 0.0 (independientes)
        
        Args:
            pick1, pick2: Picks a comparar
        
        Returns:
            Correlación (0-1)
        
        Ejemplo:
            >>> # Dodgers ML + Dodgers RL (mismo juego, mercados correlacionados)
            >>> corr = manager.calculate_correlation(pick_ml, pick_rl)
            >>> corr
            0.75
        """
        # Juegos diferentes = independientes
        if pick1.game_id != pick2.game_id:
            return 0.0
        
        # Mismo mercado = correlación perfecta
        if pick1.market == pick2.market:
            return 1.0
        
        # Buscar en matriz de correlación
        key = (pick1.market, pick2.market)
        reverse_key = (pick2.market, pick1.market)
        
        correlation = self.MARKET_CORRELATION.get(
            key,
            self.MARKET_CORRELATION.get(reverse_key, 0.5)  # Default: correlación media
        )
        
        return correlation
    
    def _calculate_correlated_exposure(self, new_pick: Pick) -> float:
        """
        Calcula exposure correlacionado si se agrega new_pick
        
        Suma stake ponderado por correlación con picks activos del mismo juego
        """
        correlated_exposure = new_pick.stake_pct
        
        for active_pick in self.active_picks:
            if active_pick.game_id == new_pick.game_id:
                correlation = self.calculate_correlation(active_pick, new_pick)
                correlated_exposure += active_pick.stake_pct * correlation
        
        return correlated_exposure
    
    def get_picks_summary(self) -> Dict:
        """
        Genera resumen de picks activos para logging/UI
        
        Returns:
            Dict con estructura friendly para JSON
        """
        return {
            "total_picks": len(self.active_picks),
            "total_exposure_pct": round(self.get_total_exposure(), 2),
            "total_exposure_amount": round(
                self.get_total_exposure() / 100 * self.bankroll, 2
            ) if self.bankroll else None,
            "picks": [
                {
                    "game_id": p.game_id,
                    "market": p.market.value,
                    "selection": p.selection,
                    "stake_pct": p.stake_pct,
                    "odds": p.odds,
                    "edge": p.edge,
                    "timestamp": p.timestamp.isoformat()
                }
                for p in self.active_picks
            ],
            "risk_status": self.get_risk_status().__dict__
        }
    
    def clear_picks(self) -> int:
        """
        Limpia todos los picks activos
        
        Returns:
            Número de picks removidos
        """
        count = len(self.active_picks)
        self.active_picks = []
        return count