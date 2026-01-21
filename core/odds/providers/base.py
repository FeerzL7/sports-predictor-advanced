# core/odds/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any


class OddsProviderBase(ABC):
    """
    Contrato base para cualquier proveedor de odds.

    Un provider:
    - NO analiza partidos
    - NO decide picks
    - SOLO devuelve mercados en formato estándar
    """

    @abstractmethod
    def get_markets(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve los mercados disponibles para un evento
        a partir del analysis normalizado.

        Ejemplo:
        {
            "total": {
                "line": 8.5,
                "odds_over": 1.95,
                "odds_under": 1.95
            }
        }
        """
        pass
