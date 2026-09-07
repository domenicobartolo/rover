# Contratto di interfaccia tra i moduli

Questo documento definisce topic MQTT, schemi dei messaggi e vocabolario comandi
condivisi tra i tre moduli. 

## Topic MQTT

| Topic | Publisher | Subscriber |
|---|---|---|
| `percezione/detection` | ai_detection (Domenico) | mqtt_ros_bridge (Antonio) |
| `comando/vocale_raw` | streaming_stt (Gregorio) | — (debug/log) |
| `comando/interpretato` | streaming_stt (Gregorio) | mqtt_ros_bridge (Antonio) |
| `rover/comando_validato` | mqtt_ros_bridge (Antonio) | ROS 2 / rover |
| `rover/stato` | rover / ROS 2 | mqtt_ros_bridge, log |
| `rete/metriche` | streaming_stt (Gregorio) | log |

## Schema messaggi

### `percezione/detection`
```json
{
  "timestamp": 1735900000.123,
  "frame_id": 4521,
  "setting": "edge",
  "person_detected": true,
  "detections": [
    {
      "bbox": [0, 0, 0, 0],
      "confidence": 0.91,
      "distance_m": 2.4,
      "track_id": 3
    }
  ],
  "inference_time_ms": 42.3
}
```
`setting` è uno tra: `edge`, `remote_5g_private`, `remote_5g_commercial`.

### `comando/interpretato`
```json
{
  "timestamp": 1735900001.500,
  "command": "mantieni_distanza",
  "params": {"target_distance_m": 1.5},
  "raw_text": "mantieni una distanza di sicurezza di un metro e mezzo",
  "stt_confidence": 0.88,
  "interpreter": "rule_based"
}
```

### `rover/comando_validato`
```json
{
  "timestamp": 1735900001.700,
  "action": "hold_distance",
  "target_distance_m": 1.5,
  "validated": true,
  "rejection_reason": null,
  "latency_pipeline_ms": 1577
}
```

## Vocabolario comandi chiuso

| Comando | Parametri | Vincolo di sicurezza |
|---|---|---|
| `avvicinati` | `target_distance_m` | non scendere sotto la distanza minima configurata |
| `allontanati` | `target_distance_m` | — |
| `fermati` | — | sempre eseguibile, priorità massima |
| `mantieni_distanza` | `target_distance_m` | — |

Qualsiasi comando fuori da questo insieme (incluso output di un eventuale LLM) va
scartato dal bridge (`validated: false`, con `rejection_reason` valorizzato).


