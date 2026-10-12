# Registro modifiche

Tutte le modifiche rilevanti del progetto sono documentate in questo file.

## 0.1.0 - Non rilasciata

- Prima integrazione Home Assistant in sola lettura per DVBViewer Media Server.
- Config flow nativo, aggiornamenti basati su coordinator e diagnostica.
- Entità per connettività, stato del server, timer e registrazioni.
- Timestamp dei timer gestiti con fuso orario Europe/Rome.
- La durata riportata da DMS viene trattata come metadato non autorevole; sono gestiti valori non validi e timer che attraversano la mezzanotte.
- Set di entità operative ridotto e archivio registrazioni limitato per tutelare la privacy.
- Persistenza della prossima accensione DMS indipendentemente dalla disponibilità del server.
- Entità `number` configurabili da interfaccia per anticipo accensione e soglia timer ravvicinati.
- Configurazione disponibile anche quando DMS è offline; non sono incluse automazioni energetiche né comandi diretti di accensione o spegnimento del computer.
- Rimossi i riferimenti e la logica specifica di un ambiente personale: nessun endpoint esterno di verifica registrazioni e nessuna configurazione dedicata a un computer specifico.
- Documentazione e interfaccia italiana rese generiche per un utilizzo pubblico tramite HACS.
