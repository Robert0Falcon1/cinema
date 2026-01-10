# Applicativo Cinema — Ticketing CLI (Python)

Questo progetto è una demo da linea di comando per simulare il flusso di **acquisto biglietti cinema** con:
- elenco spettacoli
- visualizzazione posti liberi
- acquisto con **blocco posto** + **ordine** + **pagamento simulato**
- webhook di esito pagamento (AUTORIZZATO / RIFIUTATO / ANNULLATO)


## Come provare l'applicativo da linea di comando
```bash
python3 main.py list-shows
python3 main.py buy --cliente c1 --spettacolo sp1 --posto A1
python3 main.py webhook --pagamento pay_XXXXXXXXXXXX --esito AUTORIZZATO
```

## Reset
```bash
rm -f .cinema_state.json
```

