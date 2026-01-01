from __future__ import annotations

from typing import Optional

def evaluate_severity(datos_mb: float | None, validos_dias: int | None, thresholds: dict) -> Optional[str]:
    """
    thresholds = {
      "critical": {"days": 1, "data_mb": 300},
      "high": {"days": 3, "data_mb": 1024},
      "medium": {"days": 7, "data_mb": 2048},
    }
    """
    def band(name: str):
        b = thresholds.get(name) or {}
        return int(b.get("days", 0) or 0), int(b.get("data_mb", 0) or 0)

    c_days, c_mb = band("critical")
    h_days, h_mb = band("high")
    m_days, m_mb = band("medium")

    # CRÍTICO
    if (
        (validos_dias is not None and c_days > 0 and validos_dias <= c_days) or
        (datos_mb is not None and c_mb > 0 and datos_mb < c_mb)
    ):
        return "CRÍTICO"

    # ALTA
    if (
        (validos_dias is not None and h_days > 0 and validos_dias <= h_days) or
        (datos_mb is not None and h_mb > 0 and datos_mb < h_mb)
    ):
        return "ALTA"

    # MEDIA
    if (
        (validos_dias is not None and m_days > 0 and validos_dias <= m_days) or
        (datos_mb is not None and m_mb > 0 and datos_mb < m_mb)
    ):
        return "MEDIA"

    return None
