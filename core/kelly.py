"""
Kelly Calculator - Stake sizing óptimo

RESPONSABILIDAD:
Calcular qué % del bankroll apostar en cada pick.

FÓRMULA KELLY:
f = (p * (b + 1) - 1) / b
donde:
- f = fracción del bankroll
- p = probabilidad real
- b = odds - 1

AJUSTES:
- Fracción conservadora (1/4 Kelly, 1/2 Kelly)
- Confidence del modelo
- Correlación con otras apuestas activas

NO DEPENDE DE:
- Deporte
- Mercado
- APIs
"""
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class KellyResult:
    """Resultado del cálculo de Kelly con metadata"""
    stake_pct: float              # % del bankroll (0-100)
    stake_amount: Optional[float]  # Cantidad absoluta (si bankroll conocido)
    kelly_full: float             # Kelly completo (antes de fracción)
    kelly_fraction_used: float    # Fracción aplicada (ej: 0.25)
    confidence_adjustment: float  # Multiplicador por confidence
    correlation_adjustment: float # Multiplicador por correlación
    final_adjustment: float       # Producto de todos los ajustes


class KellyCalculator:
    """
    Calculador de stake sizing con Kelly Criterion
    
    CONFIGURACIÓN CONSERVADORA (recomendada):
    - fraction=0.25 (1/4 Kelly)
    - max_stake=10% (nunca más del 10% del bankroll)
    - min_edge=0.02 (no apostar con edge < 2%)
    
    CONFIGURACIÓN AGRESIVA (solo si bankroll grande + alta confianza):
    - fraction=0.50 (1/2 Kelly)
    - max_stake=15%
    - min_edge=0.01
    """
    
    def __init__(
        self,
        fraction: float = 0.25,
        max_stake_pct: float = 10.0,
        min_edge: float = 0.02,
        bankroll: Optional[float] = None
    ):
        """
        Args:
            fraction: Fracción de Kelly a usar (0.1 - 1.0)
                     0.25 = Quarter Kelly (conservador, recomendado)
                     0.50 = Half Kelly (moderado)
                     1.00 = Full Kelly (agresivo, NO recomendado)
            
            max_stake_pct: Stake máximo permitido (% del bankroll)
                          Default 10% = nunca apostar más del 10%
            
            min_edge: Edge mínimo requerido para apostar
                     Default 2% = ignorar edges menores
            
            bankroll: Bankroll total (opcional, para calcular stake absoluto)
        """
        if not 0.1 <= fraction <= 1.0:
            raise ValueError("Fracción debe estar entre 0.1 y 1.0")
        
        if not 1.0 <= max_stake_pct <= 100.0:
            raise ValueError("max_stake_pct debe estar entre 1% y 100%")
        
        self.fraction = fraction
        self.max_stake_pct = max_stake_pct
        self.min_edge = min_edge
        self.bankroll = bankroll
    
    def calculate(
        self,
        probability: float,
        odds: float,
        confidence: float = 1.0,
        correlation: float = 0.0,
        edge: Optional[float] = None
    ) -> KellyResult:
        """
        Calcula stake óptimo con Kelly Criterion
        
        Args:
            probability: Probabilidad real (0-1)
            odds: Cuota decimal
            confidence: Confidence del modelo (0-1)
                       0.5 = baja confianza → reduce stake a la mitad
                       1.0 = máxima confianza → sin reducción
            
            correlation: Correlación con picks activos (0-1)
                        0.0 = independiente
                        0.5 = correlación media → reduce stake
                        0.8 = alta correlación → reduce mucho stake
            
            edge: Edge pre-calculado (opcional, se calcula si no se provee)
        
        Returns:
            KellyResult con stake y metadata
        
        Ejemplo:
            >>> calc = KellyCalculator(fraction=0.25, bankroll=10000)
            >>> result = calc.calculate(
            ...     probability=0.55,
            ...     odds=2.10,
            ...     confidence=0.85,
            ...     correlation=0.0
            ... )
            >>> result.stake_pct
            2.73  # 2.73% del bankroll
            >>> result.stake_amount
            273.0  # $273 si bankroll = $10,000
        """
        # 1. Calcular edge si no se provee
        if edge is None:
            implied_prob = 1 / odds
            edge = probability - implied_prob
        
        # 2. Verificar edge mínimo
        if edge < self.min_edge:
            return KellyResult(
                stake_pct=0.0,
                stake_amount=0.0 if self.bankroll else None,
                kelly_full=0.0,
                kelly_fraction_used=self.fraction,
                confidence_adjustment=confidence,
                correlation_adjustment=1.0 - correlation,
                final_adjustment=0.0
            )
        
        # 3. Kelly completo
        b = odds - 1
        kelly_full = (probability * (b + 1) - 1) / b
        kelly_full = max(0, kelly_full)  # No puede ser negativo
        
        # 4. Aplicar fracción conservadora
        kelly_fractional = kelly_full * self.fraction
        
        # 5. Ajustar por confidence
        kelly_adjusted = kelly_fractional * confidence
        
        # 6. Ajustar por correlación
        # Si correlation=0.5 → reduce stake en 50%
        correlation_multiplier = 1.0 - correlation
        kelly_final = kelly_adjusted * correlation_multiplier
        
        # 7. Convertir a porcentaje y aplicar cap
        stake_pct = min(kelly_final * 100, self.max_stake_pct)
        
        # 8. Calcular stake absoluto si bankroll conocido
        stake_amount = None
        if self.bankroll:
            stake_amount = round((stake_pct / 100) * self.bankroll, 2)
        
        return KellyResult(
            stake_pct=round(stake_pct, 2),
            stake_amount=stake_amount,
            kelly_full=round(kelly_full, 4),
            kelly_fraction_used=self.fraction,
            confidence_adjustment=confidence,
            correlation_adjustment=correlation_multiplier,
            final_adjustment=round(confidence * correlation_multiplier, 4)
        )
    
    def calculate_batch(
        self,
        picks: list,
        correlations: Optional[Dict] = None
    ) -> Dict[str, KellyResult]:
        """
        Calcula stakes para múltiples picks considerando correlaciones
        
        Args:
            picks: Lista de dicts con {"id", "probability", "odds", "confidence"}
            correlations: Dict de correlaciones entre picks
                         {"pick1_id-pick2_id": 0.7, ...}
        
        Returns:
            Dict con KellyResult por cada pick
        
        IMPORTANTE:
        Si dos picks están correlacionados, el segundo tendrá stake reducido
        
        Ejemplo:
            >>> picks = [
            ...     {"id": "game1_ml", "probability": 0.55, "odds": 2.10, "confidence": 0.9},
            ...     {"id": "game1_over", "probability": 0.58, "odds": 1.95, "confidence": 0.85}
            ... ]
            >>> correlations = {"game1_ml-game1_over": 0.4}
            >>> results = calc.calculate_batch(picks, correlations)
        """
        if correlations is None:
            correlations = {}
        
        results = {}
        processed_picks = []
        
        for pick in picks:
            pick_id = pick["id"]
            
            # Calcular correlación máxima con picks ya procesados
            max_correlation = 0.0
            for prev_pick_id in processed_picks:
                corr_key_1 = f"{prev_pick_id}-{pick_id}"
                corr_key_2 = f"{pick_id}-{prev_pick_id}"
                
                correlation = correlations.get(
                    corr_key_1,
                    correlations.get(corr_key_2, 0.0)
                )
                max_correlation = max(max_correlation, correlation)
            
            # Calcular Kelly con correlación
            result = self.calculate(
                probability=pick["probability"],
                odds=pick["odds"],
                confidence=pick.get("confidence", 1.0),
                correlation=max_correlation
            )
            
            results[pick_id] = result
            processed_picks.append(pick_id)
        
        return results
    
    def update_bankroll(self, new_bankroll: float) -> None:
        """Actualiza bankroll (después de wins/losses)"""
        if new_bankroll <= 0:
            raise ValueError("Bankroll debe ser > 0")
        self.bankroll = new_bankroll
    
    def get_recommended_fraction(
        self,
        risk_tolerance: str = "conservative"
    ) -> float:
        """
        Sugiere fracción de Kelly según tolerancia al riesgo
        
        Args:
            risk_tolerance: "conservative", "moderate", "aggressive"
        
        Returns:
            Fracción recomendada
        """
        recommendations = {
            "conservative": 0.25,   # 1/4 Kelly
            "moderate": 0.50,       # 1/2 Kelly
            "aggressive": 0.75      # 3/4 Kelly (NO full Kelly)
        }
        
        return recommendations.get(risk_tolerance, 0.25)