# MQTT / ROS 2 Bridge — Antonio

Riceve `percezione/detection` e `comando/interpretato`, valida i comandi contro il
vocabolario chiuso e i vincoli di sicurezza, pubblica su `rover/comando_validato`.

## Setup locale

```bash
python3 -m venv venv
source venv/bin/activate
pip install paho-mqtt
# ROS 2: seguire https://docs.ros.org per l'installazione della distro scelta
```
