from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from .adapters import ConsoleAdattatoreNotifiche, MockAdattatorePagamenti
from .domain import Cliente, DisponibilitaPosti, Film, Posto, SalaCinema, Spettacolo, StatoPosto
from .persistence import load_db, save_db
from .repositories import InMemoryDB, SeedData
from .services import (
    AdattatorePagamentiService,
    GestoreAcquisto,
    ServizioBiglietti,
    ServizioListaAttesa,
    ServizioOrdini,
    ServizioPosti,
    ServizioSpettacoli,
)


@dataclass
class AppContext:
    db: InMemoryDB
    gestore: GestoreAcquisto
    servizio_spettacoli: ServizioSpettacoli
    servizio_posti: ServizioPosti
    servizio_ordini: ServizioOrdini
    servizio_lista_attesa: ServizioListaAttesa
    state_file: str

    def save(self) -> None:
        save_db(self.db, self.state_file)


def _seed_db() -> InMemoryDB:
    db = InMemoryDB()

    cliente1 = Cliente(id="c1", nome="Mario Rossi", email="mario.rossi@example.com")
    cliente2 = Cliente(id="c2", nome="Giulia Bianchi", email="giulia.bianchi@example.com")

    film1 = Film(id="f1", titolo="Interstellar", durata_min=169)
    film2 = Film(id="f2", titolo="Inception", durata_min=148)

    sala1 = SalaCinema(id="s1", nome="1", righe=4, colonne=5)

    posti = []
    pid = 1
    for r in range(1, sala1.righe + 1):
        for c in range(1, sala1.colonne + 1):
            posti.append(Posto(id=f"p{pid}", riga=r, colonna=c))
            pid += 1

    now = datetime.now()
    sp1 = Spettacolo(id="sp1", film_id=film1.id, sala_id=sala1.id, inizio=now + timedelta(hours=2), prezzo_eur=9.90)
    sp2 = Spettacolo(id="sp2", film_id=film2.id, sala_id=sala1.id, inizio=now + timedelta(hours=5), prezzo_eur=8.50)

    disponibilita = []
    for sp in (sp1, sp2):
        for p in posti:
            disponibilita.append(
                DisponibilitaPosti(
                    spettacolo_id=sp.id,
                    posto_id=p.id,
                    stato=StatoPosto.LIBERO,
                    hold_scadenza=None,
                )
            )

    for d in disponibilita:
        if d.spettacolo_id == "sp2":
            d.stato = StatoPosto.VENDUTO

    db.load_seed(
        SeedData(
            clienti=[cliente1, cliente2],
            films=[film1, film2],
            sale=[sala1],
            posti=posti,
            spettacoli=[sp1, sp2],
            disponibilita=disponibilita,
        )
    )
    return db


def build_app_context(state_file: str = ".cinema_state.json") -> AppContext:
    if os.path.exists(state_file):
        db = load_db(state_file)
    else:
        db = _seed_db()
        save_db(db, state_file)

    notifiche = ConsoleAdattatoreNotifiche()
    gateway_pagamenti = MockAdattatorePagamenti()

    servizio_spettacoli = ServizioSpettacoli(db=db)
    servizio_posti = ServizioPosti(db=db, hold_minutes=10)
    servizio_ordini = ServizioOrdini(db=db)
    servizio_biglietti = ServizioBiglietti(db=db)
    pagamenti_service = AdattatorePagamentiService(db=db, gateway=gateway_pagamenti)
    servizio_lista_attesa = ServizioListaAttesa(db=db, notifiche=notifiche, posti=servizio_posti)

    gestore = GestoreAcquisto(
        spettacoli=servizio_spettacoli,
        posti=servizio_posti,
        ordini=servizio_ordini,
        biglietti=servizio_biglietti,
        pagamenti=pagamenti_service,
        lista_attesa=servizio_lista_attesa,
        notifiche=notifiche,
    )

    return AppContext(
        db=db,
        gestore=gestore,
        servizio_spettacoli=servizio_spettacoli,
        servizio_posti=servizio_posti,
        servizio_ordini=servizio_ordini,
        servizio_lista_attesa=servizio_lista_attesa,
        state_file=state_file,
    )