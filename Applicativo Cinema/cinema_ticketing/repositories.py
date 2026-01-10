from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .domain import (
    Biglietto,
    Cliente,
    DisponibilitaPosti,
    Film,
    IscrizioneListaAttesa,
    OrdineAcquisto,
    Pagamento,
    Posto,
    SalaCinema,
    Spettacolo,
    StatoPosto,
)


class NotFoundError(RuntimeError):
    pass


class ConflictError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedData:
    clienti: List[Cliente]
    films: List[Film]
    sale: List[SalaCinema]
    posti: List[Posto]
    spettacoli: List[Spettacolo]
    disponibilita: List[DisponibilitaPosti]


class InMemoryDB:
    def __init__(self) -> None:
        self.clienti: Dict[str, Cliente] = {}
        self.films: Dict[str, Film] = {}
        self.sale: Dict[str, SalaCinema] = {}
        self.posti: Dict[str, Posto] = {}
        self.spettacoli: Dict[str, Spettacolo] = {}

        self.disponibilita: Dict[Tuple[str, str], DisponibilitaPosti] = {}

        self.ordini: Dict[str, OrdineAcquisto] = {}
        self.pagamenti: Dict[str, Pagamento] = {}
        self.biglietti: Dict[str, Biglietto] = {}
        self.waitlist: Dict[str, IscrizioneListaAttesa] = {}

    def load_seed(self, seed: SeedData) -> None:
        for c in seed.clienti:
            self.clienti[c.id] = c
        for f in seed.films:
            self.films[f.id] = f
        for s in seed.sale:
            self.sale[s.id] = s
        for p in seed.posti:
            self.posti[p.id] = p
        for sp in seed.spettacoli:
            self.spettacoli[sp.id] = sp
        for d in seed.disponibilita:
            self.disponibilita[(d.spettacolo_id, d.posto_id)] = d

    def get_spettacolo(self, spettacolo_id: str) -> Spettacolo:
        sp = self.spettacoli.get(spettacolo_id)
        if not sp:
            raise NotFoundError(f"Spettacolo non trovato: {spettacolo_id}")
        return sp

    def get_film(self, film_id: str) -> Film:
        f = self.films.get(film_id)
        if not f:
            raise NotFoundError(f"Film non trovato: {film_id}")
        return f

    def get_sala(self, sala_id: str) -> SalaCinema:
        s = self.sale.get(sala_id)
        if not s:
            raise NotFoundError(f"Sala non trovata: {sala_id}")
        return s

    def get_posto(self, posto_id: str) -> Posto:
        p = self.posti.get(posto_id)
        if not p:
            raise NotFoundError(f"Posto non trovato: {posto_id}")
        return p

    def find_posto_by_etichetta(self, sala_id: str, etichetta: str) -> Posto:
        sala = self.get_sala(sala_id)
        et = etichetta.strip().upper()
        if len(et) < 2:
            raise NotFoundError(f"Etichetta posto non valida: {etichetta}")

        row_char = et[0]
        try:
            col = int(et[1:])
        except ValueError as e:
            raise NotFoundError(f"Etichetta posto non valida: {etichetta}") from e

        riga = (ord(row_char) - ord("A")) + 1
        if riga < 1 or riga > sala.righe or col < 1 or col > sala.colonne:
            raise NotFoundError(f"Posto fuori sala: {etichetta}")

        for p in self.posti.values():
            if p.riga == riga and p.colonna == col:
                return p
        raise NotFoundError(f"Posto non trovato: {etichetta}")

    def get_disponibilita(self, spettacolo_id: str, posto_id: str) -> DisponibilitaPosti:
        d = self.disponibilita.get((spettacolo_id, posto_id))
        if not d:
            raise NotFoundError(f"Disponibilità non trovata: spettacolo={spettacolo_id}, posto={posto_id}")
        return d

    def list_disponibilita_spettacolo(self, spettacolo_id: str) -> List[DisponibilitaPosti]:
        return [d for (sp_id, _), d in self.disponibilita.items() if sp_id == spettacolo_id]

    def set_stato_posto(
        self,
        spettacolo_id: str,
        posto_id: str,
        stato: StatoPosto,
        hold_scadenza: Optional[datetime] = None,
    ) -> None:
        d = self.get_disponibilita(spettacolo_id, posto_id)
        d.stato = stato
        d.hold_scadenza = hold_scadenza

    def save_ordine(self, ordine: OrdineAcquisto) -> None:
        self.ordini[ordine.id] = ordine

    def get_ordine(self, ordine_id: str) -> OrdineAcquisto:
        o = self.ordini.get(ordine_id)
        if not o:
            raise NotFoundError(f"Ordine non trovato: {ordine_id}")
        return o

    def save_pagamento(self, pagamento: Pagamento) -> None:
        self.pagamenti[pagamento.id] = pagamento

    def get_pagamento(self, pagamento_id: str) -> Pagamento:
        p = self.pagamenti.get(pagamento_id)
        if not p:
            raise NotFoundError(f"Pagamento non trovato: {pagamento_id}")
        return p

    def save_biglietto(self, biglietto: Biglietto) -> None:
        self.biglietti[biglietto.id] = biglietto

    def get_biglietto_by_ordine(self, ordine_id: str) -> Optional[Biglietto]:
        for b in self.biglietti.values():
            if b.ordine_id == ordine_id:
                return b
        return None

    def add_waitlist(self, iscr: IscrizioneListaAttesa) -> None:
        self.waitlist[iscr.id] = iscr

    def list_waitlist_by_spettacolo(self, spettacolo_id: str) -> List[IscrizioneListaAttesa]:
        return [w for w in self.waitlist.values() if w.spettacolo_id == spettacolo_id]

    def list_waitlist_pending(self) -> List[IscrizioneListaAttesa]:
        return [w for w in self.waitlist.values() if not w.notificato]