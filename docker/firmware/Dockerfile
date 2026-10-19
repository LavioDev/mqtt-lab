FROM debian:13-slim
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates python3 python3-serial \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh
RUN arduino-cli config init --additional-urls https://espressif.github.io/arduino-esp32/package_esp32_index.json \
    && arduino-cli core update-index && arduino-cli core install esp32:esp32 \
    && arduino-cli lib install ArduinoMqttClient
WORKDIR /workspace
ENTRYPOINT ["arduino-cli", "compile", "--fqbn", "esp32:esp32:esp32", "--output-dir", "/workspace/build", "/workspace/mqtt_sensor"]
