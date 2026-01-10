from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from .adapters import GatewayNotifiche, GatewayPagamenti
from .domain import (
    Biglietto,
    EsitoPagamento,
    IscrizioneListaAttesa,
    OrdineAcquisto,
    Pagamento,
    StatoOrdine,
    StatoPosto,
)
from .repositories import ConflictError, InMemoryDB, NotFoundError


def _new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


@dataclass
class ServizioSpettacoli:
    db: InMemoryDB

    def lista_spettacoli(self) -> List[str]:
        return list(self.db.spettacoli.keys())

    def descrivi_spettacolo(self, spettacolo_id: str) -> str:
        sp = self.db.get_spettacolo(spettacolo_id)
        film = self.db.get_film(sp.film_id)
        sala = self.db.get_sala(sp.sala_id)
        return f"{sp.id} | {film.titolo} | Sala {sala.nome} | {sp.inizio:%Y-%m-%d %H:%M} | €{sp.prezzo_eur:.2f}"


@dataclass
class ServizioPosti:
    db: InMemoryDB
    hold_minutes: int = 10

    def posti_liberi(self, spettacolo_id: str) -> List[str]:
        self._scadenze_hold(spettacolo_id)
        posti = []
        for d in self.db.list_disponibilita_spettacolo(spettacolo_id):
            if d.stato == StatoPosto.LIBERO:
                p = self.db.get_posto(d.posto_id)
                posti.append(p.etichetta())
        return sorted(posti)

    def verifica_disponibilita(self, spettacolo_id: str) -> bool:
        return len(self.posti_liberi(spettacolo_id)) > 0

    def blocca_posto(self, spettacolo_id: str, posto_id: str) -> None:
        self._scadenze_hold(spettacolo_id)
        d = self.db.get_disponibilita(spettacolo_id, posto_id)
        if d.stato != StatoPosto.LIBERO:
            raise ConflictError(f"Posto non disponibile (stato={d.stato}).")
        scad = datetime.utcnow() + timedelta(minutes=self.hold_minutes)
        self.db.set_stato_posto(spettacolo_id, posto_id, StatoPosto.BLOCCATO, hold_scadenza=scad)

    def vendi_posto(self, spettacolo_id: str, posto_id: str) -> None:
        d = self.db.get_disponibilita(spettacolo_id, posto_id)
        if d.stato not in (StatoPosto.BLOCCATO, StatoPosto.LIBERO):
            raise ConflictError(f"Impossibile vendere: stato={d.stato}")
        self.db.set_stato_posto(spettacolo_id, posto_id, StatoPosto.VENDUTO, hold_scadenza=None)

    def libera_posto_admin(self, spettacolo_id: str, posto_id: str) -> None:
        self.db.set_stato_posto(spettacolo_id, posto_id, StatoPosto.LIBERO, hold_scadenza=None)

    def _scadenze_hold(self, spettacolo_id: str) -> None:
        now = datetime.utcnow()
        for d in self.db.list_disponibilita_spettacolo(spettacolo_id):
            if d.stato == StatoPosto.BLOCCATO and d.hold_scadenza and d.hold_scadenza <= now:
                self.db.set_stato_posto(spettacolo_id, d.posto_id, StatoPosto.LIBERO, hold_scadenza=None)


@dataclass
class ServizioOrdini:
    db: InMemoryDB

    def crea_ordine(self, cliente_id: str, spettacolo_id: str, posto_id: str, totale_eur: float) -> OrdineAcquisto:
        ordine = OrdineAcquisto(
            id=_new_id("ord"),
            cliente_id=cliente_id,
            spettacolo_id=spettacolo_id,
            posto_id=posto_id,
            totale_eur=totale_eur,
            stato=StatoOrdine.IN_PAGAMENTO,
            creato_il=datetime.utcnow(),
        )
        self.db.save_ordine(ordine)
        return ordine

    def aggiorna_stato(self, ordine_id: str, stato: StatoOrdine) -> OrdineAcquisto:
        ordine = self.db.get_ordine(ordine_id)
        ordine.stato = stato
        self.db.save_ordine(ordine)
        return ordine


@dataclass
class ServizioBiglietti:
    db: InMemoryDB

    def emetti_biglietto(self, ordine_id: str) -> Biglietto:
        existing = self.db.get_biglietto_by_ordine(ordine_id)
        if existing:
            return existing
        b = Biglietto(
            id=_new_id("tkt"),
            ordine_id=ordine_id,
            qr_code=secrets.token_urlsafe(16),
            emesso_il=datetime.utcnow(),
        )
        self.db.save_biglietto(b)
        return b


@dataclass
class ServizioListaAttesa:
    db: InMemoryDB
    notifiche: GatewayNotifiche
    posti: ServizioPosti

    def iscrivi(self, cliente_id: str, spettacolo_id: str) -> IscrizioneListaAttesa:
        iscr = IscrizioneListaAttesa(
            id=_new_id("wl"),
            cliente_id=cliente_id,
            spettacolo_id=spettacolo_id,
            creata_il=datetime.utcnow(),
            notificato=False,
        )
        self.db.add_waitlist(iscr)
        return iscr

    def processa_notifiche(self) -> int:
        inviate = 0
        for w in self.db.list_waitlist_pending():
            if self.posti.verifica_disponibilita(w.spettacolo_id):
                cliente = self.db.clienti.get(w.cliente_id)
                if not cliente:
                    continue
                self.notifiche.invia_notifica_disponibilita(cliente.email, w.spettacolo_id)
                w.notificato = True
                inviate += 1
        return inviate


@dataclass
class AdattatorePagamentiService:
    db: InMemoryDB
    gateway: GatewayPagamenti

    def avvia_pagamento(self, ordine_id: str, importo_eur: float) -> Pagamento:
        tx = self.gateway.avvia_checkout(ordine_id, importo_eur)
        p = Pagamento(
            id=_new_id("pay"),
            ordine_id=ordine_id,
            provider=getattr(self.gateway, "provider_name", "Provider"),
            importo_eur=importo_eur,
            esito=EsitoPagamento.ANNULLATO,
            transaction_ref=tx,
            ricevuto_il=None,
        )
        self.db.save_pagamento(p)
        return p

    def registra_esito_webhook(self, pagamento_id: str, esito: EsitoPagamento) -> Pagamento:
        p = self.db.get_pagamento(pagamento_id)
        p.esito = esito
        p.ricevuto_il = datetime.utcnow()
        self.db.save_pagamento(p)
        return p


@dataclass
class GestoreAcquisto:
    spettacoli: ServizioSpettacoli
    posti: ServizioPosti
    ordini: ServizioOrdini
    biglietti: ServizioBiglietti
    pagamenti: AdattatorePagamentiService
    lista_attesa: ServizioListaAttesa
    notifiche: GatewayNotifiche

    @property
    def db(self) -> InMemoryDB:
        return self.spettacoli.db

    def avvia_acquisto(self, cliente_id: str, spettacolo_id: str, etichetta_posto: str):
        sp = self.db.get_spettacolo(spettacolo_id)
        sala = self.db.get_sala(sp.sala_id)
        posto = self.db.find_posto_by_etichetta(sala.id, etichetta_posto)

        d = self.db.get_disponibilita(spettacolo_id, posto.id)
        if d.stato != StatoPosto.LIBERO:
            raise ConflictError(f"Posto {etichetta_posto} non libero (stato={d.stato}).")

        self.posti.blocca_posto(spettacolo_id, posto.id)
        ordine = self.ordini.crea_ordine(cliente_id, spettacolo_id, posto.id, sp.prezzo_eur)
        pagamento = self.pagamenti.avvia_pagamento(ordine.id, ordine.totale_eur)
        return ordine, pagamento

    def webhook_esito_pagamento(self, pagamento_id: str, esito: EsitoPagamento) -> Optional[Biglietto]:
        p = self.pagamenti.registra_esito_webhook(pagamento_id, esito)
        ordine = self.db.get_ordine(p.ordine_id)

        if esito == EsitoPagamento.AUTORIZZATO:
            self.ordini.aggiorna_stato(ordine.id, StatoOrdine.PAGATO)
            self.posti.vendi_posto(ordine.spettacolo_id, ordine.posto_id)

            b = self.biglietti.emetti_biglietto(ordine.id)

            cliente = self.db.clienti.get(ordine.cliente_id)
            if not cliente:
                raise NotFoundError("Cliente ordine non trovato.")
            self.notifiche.invia_biglietto(cliente.email, b)
            return b

        self.ordini.aggiorna_stato(ordine.id, StatoOrdine.ANNULLATO)
        self.posti.libera_posto_admin(ordine.spettacolo_id, ordine.posto_id)
        return None