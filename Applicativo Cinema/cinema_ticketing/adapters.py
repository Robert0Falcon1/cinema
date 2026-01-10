from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .domain import Biglietto


class GatewayPagamenti(Protocol):
    def avvia_checkout(self, ordine_id: str, importo_eur: float) -> str:
        ...


class GatewayNotifiche(Protocol):
    def invia_biglietto(self, email: str, biglietto: Biglietto) -> None:
        ...

    def invia_notifica_disponibilita(self, email: str, spettacolo_id: str) -> None:
        ...


@dataclass
class MockAdattatorePagamenti(GatewayPagamenti):
    provider_name: str = "MockPay"

    def avvia_checkout(self, ordine_id: str, importo_eur: float) -> str:
        ts = int(datetime.utcnow().timestamp())
        return f"{self.provider_name}-CHK-{ordine_id}-{ts}"


@dataclass
class ConsoleAdattatoreNotifiche(GatewayNotifiche):
    def invia_biglietto(self, email: str, biglietto: Biglietto) -> None:
        print("\n=== NOTIFICA (biglietto) ===")
        print(f"A: {email}")
        print(f"Ticket ID: {biglietto.id}")
        print(f"QR: {biglietto.qr_code}")
        print(f"Emesso il: {biglietto.emesso_il.isoformat()}")
        print("============================\n")

    def invia_notifica_disponibilita(self, email: str, spettacolo_id: str) -> None:
        print("\n=== NOTIFICA (lista d'attesa) ===")
        print(f"A: {email}")
        print(f"Si è liberato un posto per lo spettacolo: {spettacolo_id}")
        print("Accedi e prova ad acquistare.")
        print("=================================\n")