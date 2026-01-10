from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class Cliente:
    id: str
    nome: str
    email: str


@dataclass(frozen=True)
class Film:
    id: str
    titolo: str
    durata_min: int


@dataclass(frozen=True)
class SalaCinema:
    id: str
    nome: str
    righe: int
    colonne: int

    def posti_totali(self) -> int:
        return self.righe * self.colonne


@dataclass(frozen=True)
class Spettacolo:
    id: str
    film_id: str
    sala_id: str
    inizio: datetime
    prezzo_eur: float


@dataclass(frozen=True)
class Posto:
    id: str
    riga: int
    colonna: int

    def etichetta(self) -> str:
        return f"{chr(ord('A') + self.riga - 1)}{self.colonna}"


class StatoPosto(str, Enum):
    LIBERO = "LIBERO"
    BLOCCATO = "BLOCCATO"
    VENDUTO = "VENDUTO"


@dataclass
class DisponibilitaPosti:
    spettacolo_id: str
    posto_id: str
    stato: StatoPosto
    hold_scadenza: Optional[datetime] = None


class StatoOrdine(str, Enum):
    CREATO = "CREATO"
    IN_PAGAMENTO = "IN_PAGAMENTO"
    PAGATO = "PAGATO"
    ANNULLATO = "ANNULLATO"


@dataclass
class OrdineAcquisto:
    id: str
    cliente_id: str
    spettacolo_id: str
    posto_id: str
    totale_eur: float
    stato: StatoOrdine
    creato_il: datetime


class EsitoPagamento(str, Enum):
    AUTORIZZATO = "AUTORIZZATO"
    RIFIUTATO = "RIFIUTATO"
    ANNULLATO = "ANNULLATO"


@dataclass
class Pagamento:
    id: str
    ordine_id: str
    provider: str
    importo_eur: float
    esito: EsitoPagamento
    transaction_ref: Optional[str] = None
    ricevuto_il: Optional[datetime] = None


@dataclass
class Biglietto:
    id: str
    ordine_id: str
    qr_code: str
    emesso_il: datetime


@dataclass
class IscrizioneListaAttesa:
    id: str
    cliente_id: str
    spettacolo_id: str
    creata_il: datetime
    notificato: bool