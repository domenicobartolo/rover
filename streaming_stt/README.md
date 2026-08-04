# 5G Streaming + Speech-to-Text — Gregorio

Trasmissione video via 5G e pipeline speech-to-text → interpretazione comando.
Pubblica su `comando/interpretato` e `rete/metriche`
(vedi [`../docs/interface_contract.md`](../docs/interface_contract.md)).

## Da fare

- [ ] Valutare RTSP/RTP vs WebRTC vs pipeline GStreamer per lo streaming video
- [ ] Setup Whisper (locale o remoto) per lo speech-to-text
- [ ] Parser deterministico su vocabolario chiuso (+ eventuale LLM vincolato)
- [ ] Publisher MQTT verso `comando/vocale_raw` e `comando/interpretato`
- [ ] Misura parametri rete: RTT, jitter, banda, perdita pacchetti, bitrate video
      (Wireshark, tcpdump, iperf3)
- [ ] Confronto rete 5G privata vs commerciale

## Setup locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install openai-whisper paho-mqtt
# GStreamer: seguire https://gstreamer.freedesktop.org/documentation/
```
