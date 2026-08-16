# AI Detection — Domenico

Human detection e stima distanza. Pubblica su `percezione/detection`
(vedi [`../docs/interface_contract.md`](../docs/interface_contract.md)).

## Stato di avanzamento

- [x] Confronto modelli: YOLOv8n vs RT-DETR (large) — vedi sezione dedicata nella relazione
- [x] Detection persone in tempo reale da webcam (YOLOv8n e RT-DETR)
- [x] Stima distanza monoculare (altezza bbox + focale approssimata)
- [x] Containerizzazione Docker (testata in locale, da verificare su Jetson)
- [x] Logging strutturato su CSV (confidence, distanza, tempo di inferenza, FPS)
- [x] Validazione quantitativa su COCO (val2017 completo per YOLOv8n, COCO128 per confronto diretto)
- [ ] Publisher MQTT con detection reale (attualmente `main.py` pubblica dati mock)
- [ ] Test all'interno del container Docker con detection reale (solo mock testato finora)
- [ ] Valutazione NVIDIA PeopleNet (in attesa di accesso alla Jetson in laboratorio)
- [ ] Calibrazione precisa della focale per la stima distanza (attualmente valore approssimato)

## File

- `webcam_test.py` — verifica accesso webcam
- `detection_test_yolo.py` — detection + distanza + logging con YOLOv8n
- `detection_test_rtdetr.py` — detection + distanza + logging con RT-DETR
- `distance_estimator.py` — modulo di stima distanza monoculare
- `metrics_logger.py` — logging strutturato su CSV
- `main.py` — publisher MQTT (attualmente con dati mock, da integrare con detection reale)

## Risultati principali

Confronto YOLOv8n vs RT-DETR (large), su CPU (Apple M5), classe "persona":

| Test | Precision | Recall | mAP50 | mAP50-95 | Inferenza |
|---|---|---|---|---|---|
| YOLOv8n — COCO val2017 (5000 img) | 0.786 | 0.653 | 0.742 | 0.508 | 95.4 ms |
| YOLOv8n — COCO128 (128 img) | 0.813 | 0.669 | 0.761 | 0.533 | 97.5 ms |
| RT-DETR — COCO128 (128 img) | 0.910 | 0.744 | 0.858 | 0.635 | 1361.7 ms |

Test live su webcam (551 frame YOLOv8n, 127 frame RT-DETR): YOLOv8n mantiene il 96.7% dei frame con detection a 15 FPS medi; RT-DETR il 74.0% dei frame a 2.3 FPS medi.

Dettagli completi nella relazione tecnica (`docs/` o file diario di lavoro).

## Setup locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install ultralytics opencv-python paho-mqtt
```

## Esecuzione

```bash
python detection_test_yolo.py       # detection con YOLOv8n
python detection_test_rtdetr.py     # detection con RT-DETR
```
Premi `q` per uscire. I log vengono salvati in `results/metrics_live.csv` (cartella esclusa da Git).