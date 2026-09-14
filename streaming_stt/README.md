# 5G Streaming + Speech-to-Text — Gregorio

Trasmissione video via 5G e pipeline speech-to-text → interpretazione comando.
Pubblica su `comando/interpretato` e `rete/metriche`
(vedi [`../docs/interface_contract.md`](../docs/interface_contract.md)).

## Setup locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install openai-whisper paho-mqtt
# GStreamer: seguire https://gstreamer.freedesktop.org/documentation/
```
