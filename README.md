# DVBViewer Media Server per Home Assistant

Custom integration non ufficiale per integrare **DVBViewer Media Server** in Home Assistant.

L'integrazione comunica direttamente con le API locali di DVBViewer Media Server e rende disponibili in Home Assistant le informazioni principali sullo stato del server, sulle registrazioni e sui timer programmati.

È pensata per installazioni domestiche nelle quali DVBViewer Media Server viene eseguito su un computer della rete locale e Home Assistant deve poter conoscere lo stato delle registrazioni e disporre delle informazioni necessarie per eventuali automazioni di gestione energetica.

## Funzioni principali

L'integrazione crea un dispositivo **DVBViewer Media Server** in Home Assistant ed espone le seguenti entità.

### Stato del server

- **Connesso**: indica se Home Assistant riesce a comunicare correttamente con DVBViewer Media Server.
- **Stato**: indica se il server è inattivo (`idle`) oppure sta effettuando una registrazione (`recording`).

### Registrazioni

- **Prossima registrazione**: mostra data e ora di inizio della prossima registrazione programmata. Negli attributi sono disponibili, quando presenti, identificativo del timer, titolo, canale, ora di inizio, ora di fine, durata e stato della registrazione.
- **Registrazione in corso**: mostra la registrazione attualmente attiva e i relativi metadati.
- **Archivio registrazioni**: mostra il numero di registrazioni presenti nell'archivio DVBViewer Media Server e rende disponibili informazioni sull'ultima registrazione e sulle registrazioni più recenti.

Per ragioni di privacy non vengono esposti percorsi locali dei file o descrizioni estese dei programmi.

## Gestione energetica

L'integrazione fornisce le informazioni necessarie per costruire automazioni Home Assistant dedicate all'accensione e allo spegnimento del computer che ospita DVBViewer Media Server.

### Prossima accensione DMS

L'entità **Prossima accensione DMS** viene calcolata automaticamente in base a:

- data e ora della prossima registrazione;
- anticipo di accensione configurato dall'utente.

Esempio:

- prossima registrazione: 14:30;
- anticipo di accensione: 10 minuti;
- prossima accensione DMS: 14:20.

Il valore viene conservato anche quando il computer che ospita DVBViewer Media Server è spento o temporaneamente non raggiungibile e viene ripristinato dopo un riavvio di Home Assistant.

### Parametri configurabili

Dall'interfaccia di Home Assistant sono disponibili due parametri:

- **Anticipo accensione DMS**: numero di minuti prima della registrazione in cui il computer dovrebbe essere acceso. Valore predefinito: 10 minuti; intervallo 1–120 minuti.
- **Soglia timer ravvicinati**: intervallo utilizzabile dalle automazioni Home Assistant per decidere se una registrazione è troppo vicina per consentire lo spegnimento del computer. Valore predefinito: 30 minuti; intervallo 0–240 minuti.

L'integrazione calcola e rende disponibili questi dati, ma **non accende e non spegne direttamente il computer**.

Wake-on-LAN, spegnimento, notifiche e altre logiche operative vengono gestite tramite normali automazioni o altre integrazioni Home Assistant.

## Entità esposte

Gli ID entità normalmente generati sono:

- `binary_sensor.dvbviewer_media_server_connesso`
- `sensor.dvbviewer_media_server_stato`
- `sensor.dvbviewer_media_server_prossima_registrazione`
- `sensor.dvbviewer_media_server_registrazione_in_corso`
- `sensor.dvbviewer_media_server_archivio_registrazioni`
- `sensor.dvbviewer_media_server_prossima_accensione_dms`
- `number.dvbviewer_media_server_anticipo_accensione_dms`
- `number.dvbviewer_media_server_soglia_timer_ravvicinati`

Home Assistant può modificare automaticamente un ID se esiste già un'entità con lo stesso identificativo.

## Installazione tramite HACS

1. Aprire HACS.
2. Aggiungere questo repository come repository personalizzato di tipo **Integration**.
3. Installare **DVBViewer Media Server**.
4. Riavviare Home Assistant.
5. Aprire **Impostazioni → Dispositivi e servizi → Aggiungi integrazione**.
6. Cercare **DVBViewer Media Server**.
7. Inserire i dati di connessione del server.

Repository:

`https://github.com/rvs77/DVB-Media-Server-Custom-Component`

In questa fase il progetto è distribuito come **repository HACS personalizzato** e non come integrazione ufficiale Home Assistant o DVBViewer.

## Configurazione

La configurazione viene effettuata completamente dall'interfaccia grafica di Home Assistant.

Sono richiesti:

- **Host**: indirizzo IP o nome host del computer che esegue DVBViewer Media Server;
- **Porta**: porta HTTP utilizzata dal server, normalmente `8089`;
- **Nome utente**: opzionale;
- **Password**: opzionale.

Non è necessario modificare `configuration.yaml`.

## Comunicazione con DVBViewer Media Server

L'integrazione utilizza esclusivamente API locali in sola lettura di DVBViewer Media Server, tra cui:

- `status2.html`;
- `timerlist.html`;
- `recordings.html`;
- `getchannelsxml.html`;
- `version.html`.

L'integrazione non crea, modifica o elimina timer e non controlla direttamente il computer che ospita DVBViewer Media Server.

## Requisiti di rete

Home Assistant deve poter raggiungere il computer che esegue DVBViewer Media Server sulla porta configurata, normalmente `8089`.

Su Windows è possibile verificare la connettività con:

```powershell
Test-NetConnection <IP_SERVER_DMS> -Port <PORTA_DMS>
```

Il risultato deve contenere:

```text
TcpTestSucceeded : True
```

Se il computer risponde al ping ma la porta non è raggiungibile, verificare nell'ordine:

1. profilo di rete Windows;
2. regole di Windows Firewall;
3. porta configurata in DVBViewer Media Server;
4. host e porta configurati nell'integrazione;
5. eventuali credenziali di accesso.

La porta di DVBViewer Media Server dovrebbe essere accessibile soltanto dalla rete locale e non essere esposta direttamente a Internet.

## Privacy e diagnostica

I dati diagnostici possono includere metadati dei canali e titoli delle registrazioni. Password, host configurato, percorsi dei file e cartelle di registrazione vengono oscurati.

Prima di pubblicare log, diagnostica o segnalazioni su GitHub, verificare comunque che non contengano informazioni personali o riservate.

## Ambito dell'integrazione

Questa integrazione rappresenta **DVBViewer Media Server all'interno di Home Assistant**.

Si occupa di:

- conoscere lo stato del server;
- conoscere la registrazione corrente;
- conoscere la prossima registrazione;
- consultare informazioni recenti sull'archivio;
- calcolare una prossima accensione DMS persistente;
- fornire parametri utili alle automazioni energetiche.

Wake-on-LAN, avvio di Windows, rilevamento della presenza dell'utente, mantenimento acceso, spegnimento sicuro, notifiche e automazioni domestiche restano fuori da questo componente.

## Progetto indipendente

Questo progetto è una custom integration indipendente e mantenuta dalla comunità.

Non è affiliato, approvato, sponsorizzato o supportato da CM&V / DVBViewer, Home Assistant o Open Home Foundation.

I nomi **DVBViewer** e **DVBViewer Media Server** vengono utilizzati esclusivamente per identificare il software di terze parti con cui l'integrazione comunica. Il repository non contiene software, binari, loghi, chiavi di licenza, registrazioni, liste canali o altri contenuti proprietari di DVBViewer.

DVBViewer Media Server deve essere ottenuto, installato, configurato e regolarmente licenziato separatamente dal rispettivo produttore.

## Licenza

Il codice originale di questa integrazione è distribuito con licenza MIT.

La licenza del progetto non concede alcun diritto sui marchi o sul software proprietario di DVBViewer, Home Assistant o altre terze parti. Vedere [NOTICE.md](NOTICE.md).

## Limitazione nota

L'archivio registrazioni viene letto da `/api/recordings.html`. Il componente espone il numero complessivo delle registrazioni e fino a 25 elementi recenti; i percorsi locali dei file, le descrizioni estese dei programmi e l'URL interno del media server non vengono esposti come attributi delle entità.
