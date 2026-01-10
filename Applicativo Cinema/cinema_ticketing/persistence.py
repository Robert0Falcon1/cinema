from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

from .domain import (
    Biglietto,
    Cliente,
    DisponibilitaPosti,
    EsitoPagamento,
    Film,
    IscrizioneListaAttesa,
    OrdineAcquisto,
    Pagamento,
    Posto,
    SalaCinema,
    Spettacolo,
    StatoOrdine,
    StatoPosto,
)
from .repositories import InMemoryDB


def _dt_to_str(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _str_to_dt(s: Optional[str]) -> Optional[datetime]:
    return datetime.fromisoformat(s) if s else None


def save_db(db: InMemoryDB, path: str) -> None:
    payload: Dict[str, Any] = {
        "version": 1,
        "clienti": [{"id": c.id, "nome": c.nome, "email": c.email} for c in db.clienti.values()],
        "films": [{"id": f.id, "titolo": f.titolo, "durata_min": f.durata_min} for f in db.films.values()],
        "sale": [{"id": s.id, "nome": s.nome, "righe": s.righe, "colonne": s.colonne} for s in db.sale.values()],
        "posti": [{"id": p.id, "riga": p.riga, "colonna": p.colonna} for p in db.posti.values()],
        "spettacoli": [
            {
                "id": sp.id,
                "film_id": sp.film_id,
                "sala_id": sp.sala_id,
                "inizio": _dt_to_str(sp.inizio),
                "prezzo_eur": sp.prezzo_eur,
            }
            for sp in db.spettacoli.values()
        ],
        "disponibilita": [
            {
                "spettacolo_id": d.spettacolo_id,
                "posto_id": d.posto_id,
                "stato": d.stato.value,
                "hold_scadenza": _dt_to_str(d.hold_scadenza),
            }
            for d in db.disponibilita.values()
        ],
        "ordini": [
            {
                "id": o.id,
                "cliente_id": o.cliente_id,
                "spettacolo_id": o.spettacolo_id,
                "posto_id": o.posto_id,
                "totale_eur": o.totale_eur,
                "stato": o.stato.value,
                "creato_il": _dt_to_str(o.creato_il),
            }
            for o in db.ordini.values()
        ],
        "pagamenti": [
            {
                "id": p.id,
                "ordine_id": p.ordine_id,
                "provider": p.provider,
                "importo_eur": p.importo_eur,
                "esito": p.esito.value,
                "transaction_ref": p.transaction_ref,
                "ricevuto_il": _dt_to_str(p.ricevuto_il),
            }
            for p in db.pagamenti.values()
        ],
        "biglietti": [
            {
                "id": b.id,
                "ordine_id": b.ordine_id,
                "qr_code": b.qr_code,
                "emesso_il": _dt_to_str(b.emesso_il),
            }
            for b in db.biglietti.values()
        ],
        "waitlist": [
            {
                "id": w.id,
                "cliente_id": w.cliente_id,
                "spettacolo_id": w.spettacolo_id,
                "creata_il": _dt_to_str(w.creata_il),
                "notificato": w.notificato,
            }
            for w in db.waitlist.values()
        ],
    }

    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_db(path: str) -> InMemoryDB:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    db = InMemoryDB()

    for c in payload.get("clienti", []):
        obj = Cliente(id=c["id"], nome=c["nome"], email=c["email"])
        db.clienti[obj.id] = obj

    for f_ in payload.get("films", []):
        obj = Film(id=f_["id"], titolo=f_["titolo"], durata_min=int(f_["durata_min"]))
        db.films[obj.id] = obj

    for s in payload.get("sale", []):
        obj = SalaCinema(
            id=s["id"],
            nome=s["nome"],
            righe=int(s["righe"]),
            colonne=int(s["colonne"]),
        )
        db.sale[obj.id] = obj

    for p in payload.get("posti", []):
        obj = Posto(id=p["id"], riga=int(p["riga"]), colonna=int(p["colonna"]))
        db.posti[obj.id] = obj

    for sp in payload.get("spettacoli", []):
        obj = Spettacolo(
            id=sp["id"],
            film_id=sp["film_id"],
            sala_id=sp["sala_id"],
            inizio=_str_to_dt(sp["inizio"]) or datetime.now(),
            prezzo_eur=float(sp["prezzo_eur"]),
        )
        db.spettacoli[obj.id] = obj

    for d in payload.get("disponibilita", []):
        obj = DisponibilitaPosti(
            spettacolo_id=d["spettacolo_id"],
            posto_id=d["posto_id"],
            stato=StatoPosto(d["stato"]),
            hold_scadenza=_str_to_dt(d.get("hold_scadenza")),
        )
        db.disponibilita[(obj.spettacolo_id, obj.posto_id)] = obj

    for o in payload.get("ordini", []):
        obj = OrdineAcquisto(
            id=o["id"],
            cliente_id=o["cliente_id"],
            spettacolo_id=o["spettacolo_id"],
            posto_id=o["posto_id"],
            totale_eur=float(o["totale_eur"]),
            stato=StatoOrdine(o["stato"]),
            creato_il=_str_to_dt(o["creato_il"]) or datetime.utcnow(),
        )
        db.ordini[obj.id] = obj

    for p in payload.get("pagamenti", []):
        obj = Pagamento(
            id=p["id"],
            ordine_id=p["ordine_id"],
            provider=p["provider"],
            importo_eur=float(p["importo_eur"]),
            esito=EsitoPagamento(p["esito"]),
            transaction_ref=p.get("transaction_ref"),
            ricevuto_il=_str_to_dt(p.get("ricevuto_il")),
        )
        db.pagamenti[obj.id] = obj

    for b in payload.get("biglietti", []):
        obj = Biglietto(
            id=b["id"],
            ordine_id=b["ordine_id"],
            qr_code=b["qr_code"],
            emesso_il=_str_to_dt(b["emesso_il"]) or datetime.utcnow(),
        )
        db.biglietti[obj.id] = obj

    for w in payload.get("waitlist", []):
        obj = IscrizioneListaAttesa(
            id=w["id"],
            cliente_id=w["cliente_id"],
            spettacolo_id=w["spettacolo_id"],
            creata_il=_str_to_dt(w["creata_il"]) or datetime.utcnow(),
            notificato=bool(w["notificato"]),
        )
        db.waitlist[obj.id] = obj

    return db