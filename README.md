# Sistema di Ticketing Cinema

Applicazione Python da linea di comando per la gestione di acquisti di biglietti cinema, con gestione di disponibilità posti, ordini, pagamenti e lista d'attesa.

## 📋 Indice

- [Caratteristiche](#caratteristiche)
- [Requisiti](#requisiti)
- [Installazione](#installazione)
- [Architettura](#architettura)
- [Utilizzo](#utilizzo)
  - [Comandi disponibili](#comandi-disponibili)
  - [Esempi d'uso](#esempi-duso)
- [Persistenza dati](#persistenza-dati)
- [Troubleshooting](#troubleshooting)

---

## ✨ Caratteristiche

- **Consultazione spettacoli**: visualizza film, sale, orari e prezzi
- **Gestione posti**: verifica disponibilità e blocco temporaneo (10 minuti)
- **Flusso acquisto completo**: 
  - Selezione posto
  - Creazione ordine
  - Avvio pagamento (simulato)
  - Emissione biglietto (dopo esito positivo)
- **Webhook pagamenti**: simulazione callback dal provider pagamento
- **Lista d'attesa**: iscrizione per spettacoli sold-out + notifiche quando si liberano posti
- **Persistenza**: stato salvato su file JSON tra un'esecuzione e l'altra

---

## 📦 Requisiti

- **Python 3.10+**
- Nessuna dipendenza esterna (usa solo librerie standard)

---

## 🚀 Installazione

1. **Clona o scarica il progetto**:
   ```bash
   cd /path/to/Applicativo\ Cinema
   ```

2. **Verifica la struttura**:
   ```
   Applicativo Cinema/
   ├── main.py
   └── cinema_ticketing/
       ├── __init__.py
       ├── domain.py
       ├── repositories.py
       ├── adapters.py
       ├── persistence.py
       ├── services.py
       └── app.py
   ```

3. **Nessuna installazione necessaria** (Python puro)

---

## 🏗️ Architettura

Il sistema segue un'architettura a layer:

### **Domain Layer** (`domain.py`)
Entità del modello:
- `Cliente`, `Film`, `SalaCinema`, `Spettacolo`, `Posto`
- `OrdineAcquisto`, `Pagamento`, `Biglietto`
- `DisponibilitaPosti`, `IscrizioneListaAttesa`

### **Repository Layer** (`repositories.py`)
- `InMemoryDB`: repository in-memory per persistenza dati

### **Service Layer** (`services.py`)
Logica di business:
- `ServizioSpettacoli`: gestione catalogo spettacoli
- `ServizioPosti`: disponibilità, blocco, vendita posti
- `ServizioOrdini`: creazione e aggiornamento ordini
- `ServizioBiglietti`: emissione biglietti
- `ServizioListaAttesa`: iscrizioni e notifiche
- `GestoreAcquisto`: coordinatore del flusso completo

### **Adapter Layer** (`adapters.py`)
- `MockAdattatorePagamenti`: simulazione provider pagamento
- `ConsoleAdattatoreNotifiche`: invio notifiche su console

### **Persistence Layer** (`persistence.py`)
- Serializzazione/deserializzazione JSON dello stato

---

## 💻 Utilizzo

### Comandi disponibili

```bash
python3 main.py <comando> [opzioni]
```

| Comando | Descrizione |
|---------|-------------|
| `list-shows` | Elenca tutti gli spettacoli disponibili |
| `show-seats --spettacolo <id>` | Mostra posti liberi per uno spettacolo |
| `buy --cliente <id> --spettacolo <id> --posto <etichetta>` | Avvia acquisto biglietto |
| `webhook --pagamento <id> --esito <AUTORIZZATO\|RIFIUTATO\|ANNULLATO>` | Simula callback pagamento |
| `waitlist-join --cliente <id> --spettacolo <id>` | Iscrizione lista d'attesa |
| `waitlist-process` | Processa lista d'attesa (invia notifiche) |
| `waitlist-list [--spettacolo <id>]` | Visualizza iscrizioni lista d'attesa |
| `orders-list` | Visualizza tutti gli ordini |
| `admin-free-seat --spettacolo <id> --posto <etichetta>` | Libera un posto (admin) |

### Opzioni globali

- `--state-file <path>`: percorso file JSON per persistenza (default: `.cinema_state.json`)

---

## 📖 Esempi d'uso

### 1️⃣ Consultare gli spettacoli disponibili

```bash
python3 main.py list-shows
```

**Output**:
```
Spettacoli disponibili:

 - sp1 | Interstellar | Sala 1 | 2026-01-10 18:00 | €9.90
 - sp2 | Inception | Sala 1 | 2026-01-10 21:00 | €8.50
```

---

### 2️⃣ Visualizzare posti liberi

```bash
python3 main.py show-seats --spettacolo sp1
```

**Output**:
```
Posti liberi per sp1:
 - A1, A2, A3, A4, A5, B1, B2, B3, B4, B5, C1, C2, C3, C4, C5, D1, D2, D3, D4, D5
```

---

### 3️⃣ Acquistare un biglietto

**Passo 1: Avvia acquisto**

```bash
python3 main.py buy --cliente c1 --spettacolo sp1 --posto A1
```

**Output**:
```
Ordine creato e posto bloccato:
 - ordine_id:   ord_6d8b8d2ea4dc
 - totale:      €9.90

Pagamento avviato (simulato):
 - pagamento_id: pay_80205b4aa77b
 - provider:     MockPay
 - checkout_ref: MockPay-CHK-ord_6d8b8d2ea4dc-1768048718

Per simulare il webhook del provider pagamento:
  python3 main.py webhook --pagamento pay_80205b4aa77b --esito AUTORIZZATO
```

**Passo 2: Simula esito pagamento**

```bash
python3 main.py webhook --pagamento pay_80205b4aa77b --esito AUTORIZZATO
```

**Output**:
```
=== NOTIFICA (biglietto) ===
A: mario.rossi@example.com
Ticket ID: tkt_a3f9c1b8e5d2
QR: xY9kL2mP4nQ8rT1vW3zB
Emesso il: 2026-01-10T17:30:45.123456
============================

Webhook OK: pagamento autorizzato, biglietto emesso e notificato.
 - ticket_id: tkt_a3f9c1b8e5d2
```

---

### 4️⃣ Lista d'attesa (spettacolo sold-out)

**Prova ad acquistare su spettacolo sold-out**:

```bash
python3 main.py buy --cliente c2 --spettacolo sp2 --posto A1
```

**Output**:
```
ERRORE: Posto A1 non libero (stato=VENDUTO).

Sembra che non ci siano posti disponibili.
Puoi iscriverti alla lista d'attesa con:
  python3 main.py waitlist-join --cliente c2 --spettacolo sp2
```

**Iscrizione alla lista d'attesa**:

```bash
python3 main.py waitlist-join --cliente c2 --spettacolo sp2
```

**Libera un posto (admin)**:

```bash
python3 main.py admin-free-seat --spettacolo sp2 --posto A1
```

**Processa lista d'attesa (invia notifiche)**:

```bash
python3 main.py waitlist-process
```

**Output**:
```
=== NOTIFICA (lista d'attesa) ===
A: giulia.bianchi@example.com
Si è liberato un posto per lo spettacolo: sp2
Accedi e prova ad acquistare.
=================================

Processo lista d'attesa completato. Notifiche inviate: 1
```

---

### 5️⃣ Visualizzare ordini

```bash
python3 main.py orders-list
```

**Output**:
```
- ord_6d8b8d2ea4dc | cliente=c1 | spettacolo=sp1 | posto=p1 | stato=PAGATO | €9.90
```

---

## 💾 Persistenza dati

Lo stato dell'applicazione (ordini, pagamenti, posti, lista d'attesa) viene salvato automaticamente in:

```
.cinema_state.json
```

**Reset completo**:

```bash
rm -f .cinema_state.json
```

Al prossimo comando, verrà ricreato lo stato iniziale (seed):
- 2 clienti (`c1`, `c2`)
- 2 film (`Interstellar`, `Inception`)
- 1 sala (4 righe × 5 colonne)
- 2 spettacoli (`sp1` con posti liberi, `sp2` sold-out)

---

## 🔧 Troubleshooting

### Errore: `python: command not found`

Usa `python3` invece di `python`:

```bash
python3 main.py list-shows
```

### Errore: `ModuleNotFoundError: No module named 'cinema_ticketing'`

Assicurati di eseguire i comandi dalla cartella radice del progetto:

```bash
cd /path/to/Applicativo\ Cinema
python3 main.py list-shows
```

### Errore: `Pagamento non trovato: pay_...`

Hai cancellato `.cinema_state.json` dopo aver creato l'ordine. Ricrea l'ordine:

```bash
python3 main.py buy --cliente c1 --spettacolo sp1 --posto A1
```

### Stato corrotto o comportamento anomalo

Elimina il file di stato e ricomincia:

```bash
rm -f .cinema_state.json
python3 main.py list-shows
```

### Pulire la cache Python

Se modifichi il codice e non vedi i cambiamenti:

```bash
find . -name "__pycache__" -type d -prune -exec rm -rf {} +
```

---

## 📝 Note

- **Clienti disponibili**: `c1` (Mario Rossi), `c2` (Giulia Bianchi)
- **Spettacoli disponibili**: `sp1` (Interstellar), `sp2` (Inception, sold-out)
- **Formato posti**: lettera (riga) + numero (colonna), es. `A1`, `B3`, `D5`
- **Blocco temporaneo**: i posti vengono bloccati per 10 minuti dopo l'acquisto (prima dell'esito pagamento)
- **Provider pagamento**: simulato (non effettua transazioni reali)

---

## 📚 Riferimenti

Il sistema implementa i seguenti pattern architetturali:

- **Domain-Driven Design**: separazione tra domain, services, repositories
- **Adapter Pattern**: per pagamenti e notifiche
- **Dependency Injection**: nei servizi e nel gestore di acquisto
- **Repository Pattern**: per accesso dati
- **Service Layer**: per logica di business

I diagrammi di progettazione (BPMN, C4, Class Diagram) sono disponibili nella cartella `Progettazione/`.

---

## 👨‍💻 Autore

Progetto sviluppato da <a href="https://github.com/Robert0Falcon1">Roberto Falconi</a> per l'esercitazione su modellazione del software.