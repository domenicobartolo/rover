# Rover IoT — Human Detection, Smart Surveillance e Controllo Vocale su 5G

Progetto del corso di Internet of Things (IoT) — Gruppo 4, sessione Settembre 2026.

## Componenti del gruppo

| Studente | Modulo | Cartella |
|---|---|---|
| Domenico Bartolo | AI — Human detection e stima distanza | [`ai_detection/`](ai_detection/) |
| Antonio Danglar | MQTT / ROS 2 bridge e validazione comandi | [`mqtt_ros_bridge/`](mqtt_ros_bridge/) |
| Gregorio Brancati | 5G streaming e speech-to-text | [`streaming_stt/`](streaming_stt/) |

## Descrizione generale

Framework per la rilevazione di presenza umana da parte di un rover terrestre in scenari
di smart surveillance e collaborazione uomo-robot. Il sistema rileva una persona tramite
la videocamera di bordo, ne stima la distanza e consente al rover di eseguire azioni
controllate (avvicinati / allontanati / fermati / mantieni distanza), impartite tramite
comando vocale e convertite in azioni ROS 2.

La human detection è sperimentata sia a bordo (Jetson) sia da remoto, con il video
trasmesso via rete 5G (privata e commerciale).

## Struttura del repository

```
ai_detection/       Modello di detection + stima distanza (Domenico)
mqtt_ros_bridge/     Bridge MQTT <-> ROS 2, validazione e sicurezza comandi (Antonio)
streaming_stt/       Streaming video 5G + speech-to-text + interpretazione comando (Gregorio)
docs/
  interface_contract.md   Schema messaggi, topic e vocabolario comandi condiviso
  updates/                 Aggiornamenti periodici (uno per data)
docker/
  docker-compose.yml       Broker MQTT locale + servizi di sviluppo
```

## Come iniziare (ambiente di sviluppo)

```bash
git clone <url-repo>
cd rover-iot-5g
docker compose -f docker/docker-compose.yml up -d
```

Questo avvia un broker MQTT (Mosquitto) locale su `localhost:1883`, così ognuno può
sviluppare e testare il proprio modulo in isolamento usando dati mock, seguendo lo
schema descritto in [`docs/interface_contract.md`](docs/interface_contract.md).

## Setting sperimentali

- **A** — Detection a bordo (Jetson)
- **B1** — Detection remota via 5G privata
- **B2** — Detection remota via 5G commerciale

## Consegne richieste

- Relazione tecnica (~30 pagine)
- Repository Git con README (questo)
- Presentazione (max 15 slide)
- Dataset/log
- Aggiornamenti intermedi periodici (vedi `docs/updates/`)
