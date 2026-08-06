"""
Scheletro del bridge MQTT/ROS2.
Si iscrive a percezione/detection e comando/interpretato,
e (per ora) si limita a stampare cosa riceve.
"""
import json
import paho.mqtt.client as mqtt

BROKER_HOST = "mosquitto"
BROKER_PORT = 1883

TOPIC_DETECTION = "percezione/detection"
TOPIC_COMMAND = "comando/interpretato"
TOPIC_VALIDATED = "rover/comando_validato"

def on_connect(client, userdata, flags, rc):
    print(f"Connesso al broker con codice {rc}")
    client.subscribe(TOPIC_DETECTION)
    client.subscribe(TOPIC_COMMAND)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload.decode())
    print(f"Ricevuto su {msg.topic}: {payload}")
    # TODO: logica di validazione qui

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
client.loop_forever()
