# MQTT / ROS 2 Bridge — Antonio

Riceve `percezione/detection` e `comando/interpretato`, valida i comandi contro il
vocabolario chiuso e i vincoli di sicurezza, pubblica su `rover/comando_validato`.

## Da fare

- [ ] Scegliere MQTT vs ROS 2 nativo vs Zenoh (documentare la scelta)
- [ ] Script mock che simula `ai_detection` (pubblica su `percezione/detection`)
- [ ] Script mock che simula `streaming_stt` (pubblica su `comando/interpretato`)
- [ ] Logica di validazione comandi (vocabolario chiuso, distanza minima, timeout)
- [ ] Bridge verso topic/service/action ROS 2
- [ ] Log sincronizzato per le metriche end-to-end (latenza pipeline)

## Setup locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install paho-mqtt
# ROS 2: seguire https://docs.ros.org per l'installazione della distro scelta
```
