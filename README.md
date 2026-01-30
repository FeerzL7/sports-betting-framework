# 🎯 Multi-Sport Betting Framework

Sistema profesional de análisis de apuestas deportivas con arquitectura extensible.

## 🏗️ Arquitectura

### Principios NO negociables:
1. **Core agnóstico**: No sabe qué es un gol, pitcher o touchdown
2. **Adapters por deporte**: Cada deporte implementa `SportAdapter`
3. **Mercados desacoplados**: Moneyline, Totals, Spread son módulos independientes
4. **Providers intercambiables**: Odds API se puede cambiar sin afectar lógica

### Estructura:
```
core/          → Lógica universal (probability, edge, kelly, risk)
sports/        → Adapters por deporte (soccer/, mlb/, nfl/)
markets/       → Evaluadores de mercado (moneyline.py, totals.py)
providers/     → Sources de odds (odds_api.py, fake_provider.py)
orchestrator.py → Pipeline completo
```

## 🚀 Roadmap

- [x] Commit 1: Contratos base
- [ ] Commit 2: Core modules
- [ ] Commit 3: Soccer adapter
- [ ] Commit 4: Markets
- [ ] Commit 5: Orchestrator + CLI

## 📝 Convenciones

**Commits**:
- `feat:` Nueva funcionalidad
- `refactor:` Cambio sin afectar comportamiento
- `fix:` Corrección de bug
- `docs:` Solo documentación

**Branches**:
- `main`: Código estable
- `dev`: Desarrollo activo
- `feature/*`: Features específicos

## ⚠️ Reglas críticas

1. **NUNCA** mezclar análisis deportivo con cálculo de edge
2. **NUNCA** hardcodear odds o proyecciones
3. **SIEMPRE** validar inputs (usar Optional, defaults seguros)
4. **SIEMPRE** loggear en vez de print