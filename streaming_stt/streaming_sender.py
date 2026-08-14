"""
streaming_stt/streaming_sender.py

Cattura video dalla webcam del dispositivo, lo codifica in H.264 e lo
trasmette via RTP/UDP verso un host/porta di destinazione (il "server
remoto" nel confronto edge vs remoto della traccia).

Se la webcam non e' disponibile (es. su questa VM di sviluppo), usa
automaticamente un pattern sintetico, cosi puoi sviluppare/testare qui
e passare alla webcam vera senza cambiare nulla il giorno della demo.

Uso:
    python streaming_sender.py                          # webcam se c'e', altrimenti pattern
    python streaming_sender.py --test-src                # forza il pattern sintetico
    python streaming_sender.py --device /dev/video1      # webcam su un device diverso
    python streaming_sender.py --host 192.168.1.50 --port 5000
    python streaming_sender.py --bitrate 2000 --width 1280 --height 720
"""

import argparse
import os
import sys

import gi

gi.require_version("Gst", "1.0")
from gi.repository import GLib, Gst  # noqa: E402


def build_pipeline(args) -> Gst.Pipeline:
    use_test_src = args.test_src or not os.path.exists(args.device)
    if use_test_src and not args.test_src:
        print(
            f"[WARN] Webcam '{args.device}' non trovata: uso un pattern di test. "
            f"Sul dispositivo della demo, con la webcam collegata, partira' "
            f"automaticamente lo streaming reale senza modifiche."
        )

    if use_test_src:
        source = "videotestsrc pattern=ball is-live=true"
    else:
        source = f"v4l2src device={args.device}"

    pipeline_str = (
        f"{source} ! video/x-raw,width={args.width},height={args.height},framerate={args.fps}/1 "
        f"! videoconvert "
        f"! x264enc tune=zerolatency bitrate={args.bitrate} speed-preset=ultrafast key-int-max={args.fps} "
        f"! rtph264pay config-interval=1 pt=96 "
        f"! udpsink host={args.host} port={args.port}"
    )
    print(f"[PIPELINE] {pipeline_str}")
    return Gst.parse_launch(pipeline_str)


def main():
    parser = argparse.ArgumentParser(description="Sender video RTP/UDP (webcam o pattern di test)")
    parser.add_argument("--device", default="/dev/video0", help="Device webcam")
    parser.add_argument("--host", default="127.0.0.1", help="Host di destinazione")
    parser.add_argument("--port", type=int, default=5000, help="Porta UDP di destinazione")
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--bitrate", type=int, default=1000, help="Bitrate target in kbps")
    parser.add_argument(
        "--test-src", action="store_true", help="Forza il pattern sintetico anche se la webcam c'e'"
    )
    args = parser.parse_args()

    Gst.init(None)
    pipeline = build_pipeline(args)

    bus = pipeline.get_bus()
    bus.add_signal_watch()
    loop = GLib.MainLoop()

    def on_message(_bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            print("[SENDER] Fine stream (EOS).")
            loop.quit()
        elif t == Gst.MessageType.ERROR:
            err, debug = message.parse_error()
            print(f"[SENDER][ERROR] {err} — {debug}")
            loop.quit()

    bus.connect("message", on_message)

    pipeline.set_state(Gst.State.PLAYING)
    print(f"[SENDER] Trasmissione avviata verso {args.host}:{args.port} (Ctrl+C per fermare)")

    try:
        loop.run()
    except KeyboardInterrupt:
        print("\n[SENDER] Interrotto dall'utente.")
    finally:
        pipeline.set_state(Gst.State.NULL)


if __name__ == "__main__":
    sys.exit(main())
