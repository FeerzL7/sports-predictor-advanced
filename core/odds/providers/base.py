# core/odds/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any


class OddsProvider(ABC):
    """
    Contrato base para cualquier proveedor de odds.
    Un provider SOLO se encarga de devolver mercados
    en un formato estándar, a partir del análisis.
    """

    @abstractmethod
    def get_markets(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve los mercados disponibles para un evento.

        Formato esperado (ejemplo):
        {
            "total": {
                "line": 8.5,
                "odds_over": 1.95,
                "odds_under": 1.95
            }
        }
        """
        raise NotImplementedError
