# Scelta tecnologica: MQTT vs ROS 2 nativo vs Zenoh

## Decisione
Usiamo **MQTT** (broker Mosquitto) come livello di messaggistica tra i tre moduli
(ai_detection, mqtt_ros_bridge, streaming_stt), con un bridge verso **ROS 2** che
verrà aggiunto quando il modulo si integra con il rover reale in laboratorio.

## Motivazioni
- MQTT è leggero, semplice da testare in locale con Docker (nessun ambiente ROS 2
  richiesto durante lo sviluppo iniziale)
- Il contratto di interfaccia (docs/interface_contract.md) è già definito su
  topic/schema MQTT-style, condiviso da tutti e tre i moduli
- ROS 2 nativo richiederebbe un ambiente rclpy configurato su ogni macchina di
  sviluppo, rallentando il lavoro in parallelo prima dell'accesso al laboratorio
- Zenoh è stato scartato per ora: più moderno e performante di MQTT, ma meno
  documentato per il nostro caso d'uso e richiederebbe più tempo di setup

## Piano di integrazione ROS 2
Il bridge (questo modulo) riceve i messaggi via MQTT e, quando sarà disponibile
l'ambiente ROS 2 (Jetson/rover in laboratorio), pubblicherà le azioni validate
su topic/action ROS 2 tramite rclpy, mantenendo MQTT come livello di trasporto
verso gli altri due moduli (ai_detection, streaming_stt).
