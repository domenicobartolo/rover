"""
streaming_stt/streaming_receiver.py

Riceve lo stream video RTP/UDP inviato da streaming_sender.py, lo
decodifica e misura le metriche di rete richieste dalla traccia:
jitter, pacchetti persi, bitrate effettivo ricevuto.

Le metriche vengono:
  - stampate periodicamente a console
  - pubblicate su MQTT sul topic rete/metriche (schema del contratto)
  - salvate in logs/streaming_metrics.csv per la relazione tecnica

Nota sul RTT: essendo un flusso video mono-direzionale (solo RTP, senza
RTCP di ritorno), questo script NON misura il RTT. Per quello, in
parallelo, usate un test attivo separato (es. `ping` o `iperf3`) verso
lo stesso host — indicato nei comandi di verifica in fondo al file.

Uso:
    python streaming_receiver.py                     # riceve su porta 5000, nessun display
    python streaming_receiver.py --display            # mostra anche il video (richiede ambiente grafico)
    python streaming_receiver.py --mqtt-host localhost
"""

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime

import gi
import paho.mqtt.client as mqtt

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402

TOPIC_METRICS = "rete/metriche"
LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "streaming_metrics.csv")


def build_pipeline(args) -> Gst.Pipeline:
    sink = "autovideosink" if args.display else "fakesink"
    pipeline_str = (
        f"udpsrc port={args.port} name=usrc "
        f"! application/x-rtp,media=video,encoding-name=H264,payload=96 "
        f"! rtpjitterbuffer name=jbuf latency=200 "
        f"! rtph264depay ! h264parse ! avdec_h264 "
        f"! videoconvert ! {sink}"
    )
    print(f"[PIPELINE] {pipeline_str}")
    return Gst.parse_launch(pipeline_str)


def log_metrics_csv(row: dict) -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    file_exists = os.path.isfile(LOG_FILE)
    with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="Receiver video RTP/UDP con misurazione metriche")
    parser.add_argument("--port", type=int, default=5000, help="Porta UDP in ascolto")
    parser.add_argument("--display", action="store_true", help="Mostra il video (richiede ambiente grafico)")
    parser.add_argument("--interval", type=float, default=2.0, help="Secondi tra una misura e l'altra")
    parser.add_argument(
        "--mqtt-host", type=str, default=os.environ.get("MQTT_HOST", "localhost"), help="Host broker MQTT"
    )
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument(
        "--setting",
        type=str,
        default="edge",
        choices=["edge", "remote_5g_private", "remote_5g_commercial", "local_test"],
        help="Etichetta del setting sperimentale corrente, per confrontare i risultati",
    )
    args = parser.parse_args()

    Gst.init(None)
    pipeline = build_pipeline(args)
    jbuf = pipeline.get_by_name("jbuf")

    mqtt_client = mqtt.Client()
    mqtt_client.connect(args.mqtt_host, args.mqtt_port, keepalive=60)
    mqtt_client.loop_start()

    stats_state = {"bytes_since_last": 0, "last_time": time.time()}

    def on_pad_probe(pad, info):
        buf = info.get_buffer()
        if buf:
            stats_state["bytes_since_last"] += buf.get_size()
        return Gst.PadProbeReturn.OK

    udpsrc = pipeline.get_by_name("usrc")
    if udpsrc is not None:
        pad = udpsrc.get_static_pad("src")
        pad.add_probe(Gst.PadProbeType.BUFFER, on_pad_probe)
    else:
        print("[WARN] Elemento udpsrc non trovato: il bitrate non verra' misurato.")

    def poll_metrics():
        now = time.time()
        elapsed = now - stats_state["last_time"]
        bytes_received = stats_state["bytes_since_last"]
        bitrate_kbps = round((bytes_received * 8 / 1000) / elapsed, 1) if elapsed > 0 else 0.0
        stats_state["bytes_since_last"] = 0
        stats_state["last_time"] = now

        jitter_ms, packets_lost, packets_received = None, None, None
        if jbuf is not None:
            stats = jbuf.get_property("stats")
            if stats is not None:
                jitter_ns = stats.get_value("avg-jitter") if stats.has_field("avg-jitter") else None
                jitter_ms = round(jitter_ns / 1e6, 2) if jitter_ns is not None else None
                packets_lost = stats.get_value("num-lost") if stats.has_field("num-lost") else None
                packets_received = stats.get_value("num-pushed") if stats.has_field("num-pushed") else None

        loss_pct = None
        if packets_lost is not None and packets_received is not None and (packets_received + packets_lost) > 0:
            loss_pct = round(100 * packets_lost / (packets_received + packets_lost), 2)

        row = {
            "timestamp": datetime.now().isoformat(),
            "setting": args.setting,
            "bitrate_kbps": bitrate_kbps,
            "jitter_ms": jitter_ms,
            "packets_lost": packets_lost,
            "packets_received": packets_received,
            "packet_loss_pct": loss_pct,
        }

        print(
            f"[METRICHE] bitrate={bitrate_kbps}kbps  jitter={jitter_ms}ms  "
            f"persi={packets_lost}  ricevuti={packets_received}  loss={loss_pct}%"
        )

        mqtt_message = {
            "timestamp": time.time(),
            "setting": args.setting,
            "bitrate_kbps": bitrate_kbps,
            "jitter_ms": jitter_ms,
            "packet_loss_pct": loss_pct,
        }
        mqtt_client.publish(TOPIC_METRICS, json.dumps(mqtt_message))
        log_metrics_csv(row)

        return True

    GLib.timeout_add(int(args.interval * 1000), poll_metrics)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()

    def on_message(_bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"[RECEIVER][ERROR] {err} — {debug}")
            loop.quit()

    bus.connect("message", on_message)

    pipeline.set_state(Gst.State.PLAYING)
    print(f"[RECEIVER] In ascolto su porta {args.port}, setting='{args.setting}' (Ctrl+C per fermare)")
    print(
        "[RECEIVER][NOTA] Per il RTT, esegui in parallelo: "
        "ping -c 20 <host_sender>  oppure  iperf3 -c <host_sender>"
    )

    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n[RECEIVER] Interrotto dall'utente.")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    sys.exit(main())
