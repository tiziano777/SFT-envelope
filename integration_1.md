# 📁 AI Experiment Lineage System: Master-Worker Architecture

Questo documento definisce l'architettura tecnica per la gestione del lineage di modelli AI, ottimizzata per la resilienza e il tracciamento granulare delle derivazioni (Fine-tuning, LoRA, Merging).

---

## 1. Schema Neo4j (Graph Data Model)

Il grafo modella la causalità tra l'intento logico (Esperimento) e il prodotto fisico (Checkpoint).

### Nodi e Proprietà
* **Recipe**: Il punto di ingresso. Contiene il `recipe_id` e il `recipe_configuration` (JSON/YML), e anche. le altre info ereditate da una dataclass SQL: 
esempio:
sql entity(sarà python @dataclass):
```sql
CREATE TABLE recipe (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    scope TEXT NOT NULL,
    tasks TEXT[] DEFAULT '{}'::TEXT[],
    tags TEXT[] DEFAULT '{}'::TEXT[],
    issued TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    modified TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    derived_from UUID,
    CONSTRAINT fk_recipe_derived_from
        FOREIGN KEY (derived_from)
        REFERENCES recipe(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    CONSTRAINT fk_recipe_scope
        FOREIGN KEY (scope)
        REFERENCES vocab_dataset_type(code)
        ON UPDATE CASCADE
);
```
config file yml example:
```yaml
/Users/T.Finizzi/repo/ETL_agent/nfs/mapped-data/velvet_v1/allenai/ai2_arc/ARC-Challenge/downsampled__0.7__en:
  chat_type: simple_chat_cycle2
  dist_id: ecef45fc-ba10-471d-a8ba-39172cdbf388
  dist_name: Downsampled__0.70__mapped__ARC-Challenge/en
  dist_uri: /Users/T.Finizzi/repo/ETL_agent/nfs/mapped-data/velvet_v1/allenai/ai2_arc/ARC-Challenge/downsampled__0.7__en
  replica: 1
  samples: 1603
  schema_template: ...
  system_prompt:
  - p1
  system_prompt_name: 
  - p1
  tokens: 141889
  words: 102521
```

* **Model**: Il modello di partenza su scui eseguire SFT. Proprietà: `id`, `model_id`, `model_name`(unique),`version`, `uri`, `url`, `doc_url`, `architecture_info_ref`, `description` .
* **Experiment**: L'istanza di esecuzione. Proprietà: `exp_id`, `model_id`, `status`, `exit_status`, `exit_msg`,`hash_committed_code`, `sw_requirements_json`,`scaffold_local_uri`,`scaffold_remote_uri`, `usable`, `manual_save`, `hyperparams_json`, `config_json`, `metrics_uri`, `hw_metrics_uri`, `description`.
* **Checkpoint**: L'entità atomica dei pesi. Proprietà: `ckp_id`, `epoch`, `run`, `metrics_snapshot`, `uri` (Puntatore a Master, Worker, Cloud o NULL se scartato/perso), `is_usable`, `is_merging`,  `description` .
* **Component**: Lo stack tecnologico, rachiude mimplicitamente matrice di compatibilita framework e sft technique. Proprietà: `technique_code`, `framework_code`, `docs_url`, `description` .

### Relazioni 
* **(Component)-[:USED_FOR]->(Experiment)**: Lega l'esperimento a una matrice di compatibilità framework e tecnica di SFT.
* **(Model)-[:SELECTED_FOR]->(Experiment)**: Lega l'esperimento ai dati di input.
* **(Experiment)-[:BASED_ON]->(Recipe)**: Lega l'esperimento ai dati di input.
* **(Experiment)-[:PRODUCED]->(Checkpoint)**: Ogni checkpoint appartiene a una specifica run, generando una timeseries di risultati di un esperimento.

--> [ Branching: CASE I & II] setup diverso esperimento esistente, crea nuovo esperimento nuovo, riparti da zero
* **(Experiment)-[:DERIVED_FROM {diff_patch}]->(Experiment)**: Traccia il branching logico (cambio parametri).

--> [Branching: CASE II] setup diverso esperimento esistente, ma voglio caricare un ckp dal  esperimento corrente, creandone uno nuovo ericato, come fatto sopra, e tracciare anche il fatto che siamo partiti da un ckp del vecchio esperimento.
* **(Experiment)-[:STARTED_FROM]->(Checkpoint)**: Indica da quale stato fisico è partito il training (caso di branching in cui si parte da un ckp, non è obbligatorio, si puo anche creare experiment nuovo derivato, che parte dal modello raw del precedetne esperimento!).

---> [ RESUME ] caso in cui vogliamo continuare esperimento interrotto, ma parametri cambiati,  viene creato nuovo esperimento, ma si fa partire da un ckp di pesi esistente.
* **(Experiment)-[:STARTED_FROM]->(Checkpoint)**: Indica da quale stato fisico è partito il training.

--> [ RERUN ] stesso identico setup, ma nuovo esperimento da zero.
* **(Experiment)-[:RETRY_OF]->(Experiment)**: Lega riesecuzioni identiche (stesso hash, no ckp partenza).

* **(Checkpoint)-[:MERGED_FROM]->(Checkpoint)**: Relazione N-a-1 che traccia il merging di pesi, se ho N checkpoint di inter o intra esperiemento, voglio poterli unificare (se possibile, molte tecniche modificano set di pesi in modo diverso o diveri set, useremo mergekit package, se esecuzione riesce, allora creiamo nuovo ckp e relazioni) .

---

## 2. Casistiche e Logica di Branching

### Architettura
Stiamo assumendo che DB neo4j e macchina con GPU che eseguirà fisicamente il train siano scollegate e possano comunicare solo grazie a un pool di protocolli, assumiamo per il momento solo SSH, ma vorremmo cheappunto il metodo di comunicazione e la logica dei messaggi venga disaccoppiata.

### Resume (Continuità)
Se il Worker invia un Hash Config identico (triplo controllo: hash(`hyperparams_json`), hash(`config_json`), `hash_committed_code`) e richiede di partire dall'ultimo Checkpoint della stessa Run, il Master autorizza il proseguimento sullo stesso nodo Experiment.

### Branching (Cambio Traiettoria)
Se l'Hash Config cambia ma viene richiesto un Checkpoint di partenza, il Master crea un nuovo Experiment, lo lega al precedente con `DERIVED_FROM` e al punto di partenza con `STARTED_FROM`. Questo è il caso tipico del fine-tuning o del cambio di Learning Rate in corso d'opera.

### Re-run (Nuovo Tentativo)
Se Hash e Config sono identici ma non viene fornito un Checkpoint (start from zero), il Master crea un nuovo nodo Experiment legato al precedente tramite `RETRY_OF`. Questo preserva lo storico dei fallimenti senza corrompere i nuovi dati.

### Merging (On-top User Story)
Quando N checkpoint vengono fusi, il sistema genera un nuovo nodo Checkpoint. Questo nodo non è necessariamente prodotto da un `PRODUCED_BY` di un training attivo, ma è collegato ai suoi genitori fisici tramite l'arco `MERGED_FROM`. L'esperimento che ha orchestrato il merge (se esiste, è opzionale, lo facciamo solo se non aumenta complessita, altrimenti anche solo sapere da quali ckp è stato creto un merging va piu che bene, si puo ricostruire tutto il grafo delle dipendenze comunque) viene salvato e collegato come producer.

---

## 3. Protocollo di Comunicazione e Lazy Update

### Funzionamento della Memoria Locale (Worker)

Il Worker non attende mai il Master.
I checkpoint (e sue configurazioni/log ) prodotti vengono scritti localmente nel worker, pronti per aggiornare il DB con i metadati richiesti e fare download/flush delle metriche e/o ckp rilevanti.

Gestisce una directory per i chcekpoints in `to_transfer/{id_exp}/checkpoints/{id_ckp}/*`
e parallelamente (se pissibile, cosi conserviamo metadati, ma non pesi) `to_transfer/{id_exp}/checkpoints/results/{id_ckp}/*` in modo che se dobbiamo scartare il ckp, possiamo almeno ricostruire le performance di quello specifico punto nel train, anche se teoricamente queste info gia sono in trianign_metrics che vdremo dopo, che hanno info su tutte le runs, non solo sui ckp.

Vogliamo anche visibilità completa di tutti i log del modello durante il training, e il suo setup, questi dati sono salvati in `to_transfer/{id_exp}/hw_metrics/*`, `to_transfer/{id_exp}/training_metrics/*` (quest'ultime in append mode perche son file di logs), inoltre vorremmo che la configurazione nella root nel file config.yml, deve essere copiata in `to_transfer/{id_exp}/config/*` e anche i requisiti sw/hw in `to_transfer/{id_exp}/{sw/hw}_requirements/requirements.txt` e anche le ipotetiche rewards in rewards/* siano copiate in to_transfer/{id_exp}/rewards/*.

Questi dati sono utili, perche se i dati vengono cambiati dentro il training setup, allora possiamo facilmente riscontrare un cambiamento rispetto, e creare un nuovo esperimento derivato!
facendo sovrascrizione (o copia nel caso una parte della configurazione sia rimasta invariata, o anche copia se vogliamo fare rerun in un twin experiment) in un nuovo folder `to_transfer/{new_ckp_id}/*`

Un **Sync Daemon** in background monitora la directory, e decide quando/se trasferire i risultati nel DB e se trasferire il config, {hw/sw}_requirements, hw_metrics/, training_metrics/ e i ckp in uno storage (che puo essere filesystem del master o un altro disco come nfs/ o cloud, queta parte va astratta con una chiamata API, che sotto sara collegata con un Writer custom).

Se un checkpoint viene scartato per logica di risparmio spazio, il Worker invia comunque il metadato al Master ma imposta `uri = NULL`. Se il checkpoint è critico (es. Best Model), viene trasferito allo storage definitivo e l'URI aggiornato nel Grafo.

### Primitive del Middleware
* **Handshake Protocol**: Fase bloccante iniziale. Il Worker propone un setup; il Master valida e ritorna l'ID corretto (nuovo o esistente) e la strategia di caricamento pesi.
* **Staged Sync**: Il Worker invia pacchetti di metadati in modalità "fire and forget". Il Master garantisce l'idempotenza: se riceve due volte lo stesso checkpoint per la stessa epoca, ignora il secondo.
* **URI Management**: Gli URI sono dinamici. Il sistema supporta puntatori locali (`worker://path`), centralizzati (`master://path`) o remoti (`s3://path`). Il Path Manager traduce questi schemi in base alla macchina che effettua la lettura.

---

## 4. Moduli Software Core

### Layer di Connessione e Dati
* **Shared Dataclasses**: Definizione universale di Experiment, Checkpoint e Recipe tramite Pydantic. Include la logica di calcolo dell'Hash per la configurazione.
* **Neo4j Repository**: Implementa le query Cypher per la gestione atomica dei rami (es. creazione simultanea di nodo e relazione di discendenza).

### Layer Master (Orchestratore)
* **Lineage Controller**: Il cervello che decide se un esperimento è un Resume, un Branch o un Retry.
* **Consistency Guard**: Modulo che impedisce la scrittura di checkpoint orfani o relazioni circolari.

### Layer Worker (Esecutore)
* **Local Persistence Manager**: Gestisce il manifest locale e la rotazione dei checkpoint su disco GPU.
* **Asynchronous Pusher**: Il middleware che gestisce la coda di invio verso il Master, gestendo i retry in caso di downtime della rete.

---

## 5. Criticità e Soluzioni

* **Riferimenti a Checkpoint Eliminati**: Se un Checkpoint ha `uri = NULL`, la UI deve mostrare il nodo nel lignaggio (per coerenza storica) ma disabilitare il tasto "Resume" o "Download".
* **Sincronizzazione degli Orologi**: Per i log temporali, il Master usa il timestamp di ricezione come riferimento di sistema, ma preserva il timestamp del Worker per l'analisi delle performance.
* **Inconsistenza del Path**: Risolta tramite un **URI Resolver** che mappa i prefissi (master://, worker://) in path assoluti dipendenti dall'ambiente di esecuzione.

# 6. Addtional system attirbutes

Mancano informazioni importanti come timestamping di creazione/modifica e altre informazioni di sistema spesso rilevanti, inoltre non so se neo4j supporta triggers o valori di riempimento come now() per il timestamp, ad ogni modo dobbiamo poter garantire tracing e lineage e logging in maniera compeleta, non solo per quanto rigurada lo scope, ma anche per quanto riguarda il sistema e le comunicazioni tra le due macchine (per poter effettuare backup o risolvere conflitti) inoltre non so ne neo4j ha la capacita di creare de trigger a livello d schema dati, in tal caso ci vorrebbe un layer di connessione dati esteso per il nostro caso d'uso che valida la consistenza delle operazioni (esempio se inserisco un nodo ch dovrebbe avere una relazione ma il nodo sorgente non esiste, o cose cosi, legate allo schema dati del grafo specifico)

# 7. integraizione

Attualemente il nostro progetto prevede solo di creare un setup tramite comandi make.
ti lascio il contributo de file markdown workflow e README. Sono la sdocuentazione comprensiva di tutto il progetto attuale, che ha come scopo quello di creare scaffolds personalizzati selezionando appunto modello/framework/tecnica di training. Genera dwntro setups/* un nuvo scaffold:
```
setups/setup_grpo-math-v1/
├── prepare.py       # Preparazione dataset con caching idempotente
├── train.py           # Script completo, contiene resolve_hparam() per env vars
├── run.sh             # Script di lancio (python / accelerate launch / torchrun)
├── config.yaml        # Config frozen (snapshot immutabile)
├── requirements.txt   # Dipendenze pip
└── rewards/           # (solo per tecniche RL)
    ├── __init__.py
    └── ...
```
noi vogliamo che DENTRO questo scaffold vengano create anche folders per memoria degli esperimnti da migrare su NEO4J, middleware di worker per comunuicare modifiche negli esperimenti e inserimento di checkpoint, e update di info di log e results. In modo da far si che. l'attuale progetto produca dei workers che possono esser loaded manualmente su ujna vera macchina esterna e possanmo comunuicare con un qualsiasi protocollo di comunicaziione definito. Inoltre l'attuale creatore di scaffold dovra prevedere un altre area dove appunto puo tirar su istanza neo4j per ricevere update dai risultati del trianing e salvare nel DB i metadati, we su Filesystem interno le copie dei ckp e dei risultati (referenizati nel DB con campi *_uri)  
