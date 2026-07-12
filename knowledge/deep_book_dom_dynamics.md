# Deep Book e Dinamiche DOM (Spoofing, Pulling, Iceberg Orders)

Questo documento sintetizza le dinamiche avanzate di microstruttura del mercato visibili tramite il Depth of Market (DOM) e strumenti di order flow visuale come Bookmap o Jigsaw, integrando i concetti con l'Auction Market Theory (AMT).

---

## 1. STRUMENTI E LETTURA VISUALE

### 1.1 Il DOM (Depth of Market) / Visual Footprint
Il DOM o il visual order flow (es. Bookmap) mostra l'interazione tra ordini passivi (Limit Orders) e ordini aggressivi (Market Orders).
- **Muri (Walls) / Heatmap**: Blocchi di liquidità passiva (ordini limit) sul Bid o sull'Ask. Su Bookmap appaiono come linee o aree di colore acceso (es. rosso/arancio).
- **Volume Bubbles**: Ordini eseguiti (aggressione).
  - *Bolle Rosse*: Vendite aggressive (Market Sells che colpiscono il Bid).
  - *Bolle Verdi*: Acquisti aggressivi (Market Buys che colpiscono l'Ask).
  La dimensione della bolla indica il volume scambiato.

---

## 2. DINAMICHE DI MANIPOLAZIONE: SPOOFING E PULLING

### 2.1 Spoofing
**Definizione**: Pratica istituzionale (spesso algoritmica) in cui un ordine limit di dimensioni anomale viene piazzato sul DOM con l'esplicita intenzione di **non essere eseguito**. Lo scopo è creare un'"illusione" di supporto o resistenza per spingere i trader retail nella direzione opposta (verso il vero obiettivo di liquidità del market maker).

**Come identificarlo sul DOM**:
1. **Size anomala**: Muro enormemente sproporzionato rispetto al contesto (es. 2000+ contratti dove la media è 300).
2. **Comparsa improvvisa**: Non cresce gradualmente, ma appare in un blocco unico.
3. **Scomparsa (Pulling) pre-contatto**: Il muro scompare *prima* che il prezzo lo raggiunga o lo testi realmente.

### 2.2 Pulling (Cancellazione)
**Definizione**: Il ritiro di un ordine limit dal book prima che venga eseguito. 
- **Pulling Manipolativo**: Conclude lo spoofing. Il muro "finto" scompare all'improvviso, rivelando un *liquidity void*.
- **Conseguenza Dinamica**: Il mercato tende a reagire violentemente muovendosi **verso** la direzione in cui il muro "spingeva". I trader retail rimangono intrappolati (Trapped Traders).

**Regole Operative su Spoofing/Pulling**:
- *Regola A*: Non posizionare MAI stop loss dietro a muri statici giganteschi ed evidenti. Sono esche.
- *Regola B*: Non tradare mai basandoti solo sulla size statica; la verità sta nel movimento (nell'aggressione e nel refresh).
- *Setup (Spoof Reversal)*: Se un muro enorme viene improvvisamente *pullato* senza esecuzione, aspettati un movimento violento nella direzione opposta a quella che il muro sembrava difendere.

---

## 3. DIFESA ISTITUZIONALE: ICEBERG ORDERS

### 3.1 Definizione
Un Iceberg Order è un grande ordine Limit istituzionale, di cui solo una frazione ("tip of the iceberg") è visibile sul DOM.
- Quando la parte visibile viene eseguita da un market order, il sistema la rigenera automaticamente.
- Indica **assorbimento** e una **reale intenzione** di difesa o accumulazione istituzionale, a differenza dello spoofing.

**Come identificarlo (Visual Footprint)**:
- Il prezzo colpisce ripetutamente un livello con grande aggressione (es. grandi bolle rosse che colpiscono il Bid).
- Il prezzo *non progredisce* ("Effort vs No Result").
- Su Bookmap si osserva un cluster di bolle che continua a riformarsi allo stesso livello.

### 3.2 I 3 Pilastri di Validazione dell'Iceberg
Prima di agire su un presunto Iceberg, il trader deve porsi tre domande:
1. **Quantità ("How many?")**: Quanti iceberg si stanno aggiungendo al tape? Un evento isolato è rumore; un'accumulazione costante conferma l'istituzione.
2. **Dimensione ("How large?")**: Quanto volume sta venendo assorbito? La dimensione definisce l'importanza del livello.
3. **Direzione ("Are they pulling price up or down?")**: L'Iceberg sul Bid sta spingendo/assorbendo per far salire il prezzo? O l'Iceberg sull'Ask sta schiacciando il prezzo verso il basso?

**Regole Operative sugli Iceberg**:
- *Regola A*: Mai tradare contro un Iceberg confermato. È una difesa istituzionale reale.
- *Setup (Spring / Failed Auction Invertito)*: 
  1. Il mercato mostra un "Liquidity Sweep" (es. enormi bolle rosse che innescano stop retail sotto un minimo strutturale).
  2. Immediatamente, compaiono Iceberg (grandi bolle verdi ripetute) allo stesso livello, bloccando la discesa (Effort vs No Result).
  3. Il trader prende posizione *Long*, con stop loss nascosto strettamente sotto l'Iceberg/cluster di stop appena verificatosi.

---

## 4. MATRICE DI DISTINZIONE: SPOOFING vs ICEBERG

| Caratteristica | Spoofing | Iceberg |
|----------------|----------|---------|
| **Intento** | Ingannevole (ritirare prima dell'esecuzione) | Genuino (accumulare/distribuire size) |
| **Visibilità** | Massima (muro anomalo e ovvio) | Minima (si rigenera in piccoli blocchi) |
| **Comportamento al Test** | Scompare (Pulling) prima del contatto | Assorbe l'impatto, blocca il prezzo |
| **Implicazione AMT** | Manipolazione / Creazione di Trapped Traders | Assorbimento Istituzionale (Response) |
| **Azione Operativa** | Tradare *contro* la direzione in cui spingeva il muro | Tradare *a favore* dell'Iceberg (assorbimento) |
