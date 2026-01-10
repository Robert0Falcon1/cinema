from __future__ import annotations

import argparse

from cinema_ticketing.app import build_app_context
from cinema_ticketing.domain import EsitoPagamento
from cinema_ticketing.repositories import ConflictError, NotFoundError


def cmd_list_shows(ctx) -> int:
    print("Spettacoli disponibili:\n")
    for sid in ctx.servizio_spettacoli.lista_spettacoli():
        print(" -", ctx.servizio_spettacoli.descrivi_spettacolo(sid))
    return 0


def cmd_show_seats(ctx, spettacolo_id: str) -> int:
    liberi = ctx.servizio_posti.posti_liberi(spettacolo_id)
    print(f"Posti liberi per {spettacolo_id}:")
    if not liberi:
        print(" - (nessuno)")
        return 0
    print(" - " + ", ".join(liberi))
    return 0


def cmd_buy(ctx, cliente_id: str, spettacolo_id: str, posto: str) -> int:
    try:
        ordine, pagamento = ctx.gestore.avvia_acquisto(cliente_id, spettacolo_id, posto)
    except (NotFoundError, ConflictError) as e:
        print(f"ERRORE: {e}")
        try:
            if not ctx.servizio_posti.verifica_disponibilita(spettacolo_id):
                print("\nSembra che non ci siano posti disponibili.")
                print("Puoi iscriverti alla lista d'attesa con:")
                print(f"  python3 main.py waitlist-join --cliente {cliente_id} --spettacolo {spettacolo_id}")
        except Exception:
            pass
        return 1

    print("\nOrdine creato e posto bloccato:")
    print(f" - ordine_id:   {ordine.id}")
    print(f" - totale:      €{ordine.totale_eur:.2f}")

    print("\nPagamento avviato (simulato):")
    print(f" - pagamento_id: {pagamento.id}")
    print(f" - provider:     {pagamento.provider}")
    print(f" - checkout_ref: {pagamento.transaction_ref}")

    print("\nPer simulare il webhook del provider pagamento:")
    print(f"  python3 main.py webhook --pagamento {pagamento.id} --esito AUTORIZZATO")
    print("oppure:")
    print(f"  python3 main.py webhook --pagamento {pagamento.id} --esito RIFIUTATO")

    ctx.save()
    return 0


def cmd_webhook(ctx, pagamento_id: str, esito: str) -> int:
    try:
        esito_enum = EsitoPagamento[esito.upper()]
    except KeyError:
        print("ERRORE: esito non valido. Usa: AUTORIZZATO, RIFIUTATO, ANNULLATO")
        return 1

    try:
        ticket = ctx.gestore.webhook_esito_pagamento(pagamento_id, esito_enum)
    except (NotFoundError, ConflictError) as e:
        print(f"ERRORE: {e}")
        return 1

    if ticket:
        print("Webhook OK: pagamento autorizzato, biglietto emesso e notificato.")
        print(f" - ticket_id: {ticket.id}")
    else:
        print("Webhook OK: pagamento NON autorizzato, ordine annullato e posto liberato.")

    ctx.save()
    return 0


def cmd_waitlist_join(ctx, cliente_id: str, spettacolo_id: str) -> int:
    try:
        iscr = ctx.servizio_lista_attesa.iscrivi(cliente_id, spettacolo_id)
    except NotFoundError as e:
        print(f"ERRORE: {e}")
        return 1
    print("Iscrizione lista d'attesa creata:")
    print(f" - waitlist_id: {iscr.id}")
    print(f" - spettacolo:  {iscr.spettacolo_id}")

    ctx.save()
    return 0


def cmd_waitlist_process(ctx) -> int:
    inviate = ctx.servizio_lista_attesa.processa_notifiche()
    print(f"Processo lista d'attesa completato. Notifiche inviate: {inviate}")

    ctx.save()
    return 0


def cmd_waitlist_list(ctx, spettacolo_id: str | None) -> int:
    if spettacolo_id:
        items = ctx.db.list_waitlist_by_spettacolo(spettacolo_id)
    else:
        items = list(ctx.db.waitlist.values())

    if not items:
        print("(nessuna iscrizione)")
        return 0

    for w in sorted(items, key=lambda x: x.creata_il):
        c = ctx.db.clienti.get(w.cliente_id)
        email = c.email if c else "?"
        print(f"- {w.id} | spettacolo={w.spettacolo_id} | cliente={w.cliente_id}({email}) | notificato={w.notificato}")
    return 0


def cmd_orders_list(ctx) -> int:
    if not ctx.db.ordini:
        print("(nessun ordine)")
        return 0
    for o in sorted(ctx.db.ordini.values(), key=lambda x: x.creato_il):
        print(f"- {o.id} | cliente={o.cliente_id} | spettacolo={o.spettacolo_id} | posto={o.posto_id} | stato={o.stato} | €{o.totale_eur:.2f}")
    return 0


def cmd_admin_free_seat(ctx, spettacolo_id: str, posto: str) -> int:
    try:
        sp = ctx.db.get_spettacolo(spettacolo_id)
        sala = ctx.db.get_sala(sp.sala_id)
        p = ctx.db.find_posto_by_etichetta(sala.id, posto)
        ctx.servizio_posti.libera_posto_admin(spettacolo_id, p.id)
    except (NotFoundError, ConflictError) as e:
        print(f"ERRORE: {e}")
        return 1
    print(f"OK: posto {posto} liberato su spettacolo {spettacolo_id}.")

    ctx.save()
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cinema-ticketing-cli",
        description="CLI demo per flusso acquisto biglietti + lista d'attesa + webhook pagamenti (persistente su JSON).",
    )

    p.add_argument(
        "--state-file",
        default=".cinema_state.json",
        help="Percorso file stato (JSON) per mantenere ordini/pagamenti tra comandi (default: .cinema_state.json)",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list-shows", help="Elenca gli spettacoli")

    sp = sub.add_parser("show-seats", help="Mostra posti liberi per uno spettacolo")
    sp.add_argument("--spettacolo", required=True)

    b = sub.add_parser("buy", help="Avvia acquisto (blocca posto + ordine + avvio pagamento)")
    b.add_argument("--cliente", required=True, help="ID cliente (es: c1, c2)")
    b.add_argument("--spettacolo", required=True, help="ID spettacolo (es: sp1, sp2)")
    b.add_argument("--posto", required=True, help="Etichetta posto (es: A1, B3)")

    wh = sub.add_parser("webhook", help="Simula webhook esito pagamento")
    wh.add_argument("--pagamento", required=True, help="ID pagamento (pay_...)")
    wh.add_argument("--esito", required=True, help="AUTORIZZATO | RIFIUTATO | ANNULLATO")

    wj = sub.add_parser("waitlist-join", help="Iscrivi cliente alla lista d'attesa per uno spettacolo")
    wj.add_argument("--cliente", required=True)
    wj.add_argument("--spettacolo", required=True)

    sub.add_parser("waitlist-process", help="Processa lista d'attesa (simula timer)")

    wl = sub.add_parser("waitlist-list", help="Elenca iscrizioni lista d'attesa")
    wl.add_argument("--spettacolo", required=False)

    sub.add_parser("orders-list", help="Elenca ordini")

    af = sub.add_parser("admin-free-seat", help="Libera un posto per simulare cancellazioni e far scattare la waitlist")
    af.add_argument("--spettacolo", required=True)
    af.add_argument("--posto", required=True)

    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    ctx = build_app_context(state_file=args.state_file)

    if args.cmd == "list-shows":
        return cmd_list_shows(ctx)
    if args.cmd == "show-seats":
        return cmd_show_seats(ctx, args.spettacolo)
    if args.cmd == "buy":
        return cmd_buy(ctx, args.cliente, args.spettacolo, args.posto)
    if args.cmd == "webhook":
        return cmd_webhook(ctx, args.pagamento, args.esito)
    if args.cmd == "waitlist-join":
        return cmd_waitlist_join(ctx, args.cliente, args.spettacolo)
    if args.cmd == "waitlist-process":
        return cmd_waitlist_process(ctx)
    if args.cmd == "waitlist-list":
        return cmd_waitlist_list(ctx, args.spettacolo)
    if args.cmd == "orders-list":
        return cmd_orders_list(ctx)
    if args.cmd == "admin-free-seat":
        return cmd_admin_free_seat(ctx, args.spettacolo, args.posto)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())