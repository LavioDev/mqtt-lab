#include <ArduinoMqttClient.h>
#include <WiFi.h>
#include <cstring>

#include "firmware_config.h"

WiFiClient networkClient;
MqttClient mqttClient(networkClient);

unsigned long lastPublishMs = 0;
unsigned long messageNumber = 0;

void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.printf("Connecting to Wi-Fi SSID '%s'\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.printf("\nWi-Fi connected; IP=%s\n", WiFi.localIP().toString().c_str());
}

void connectMqtt() {
  while (!mqttClient.connected()) {
    connectWiFi();
    mqttClient.setId(MQTT_CLIENT_ID);
    mqttClient.setUsernamePassword(MQTT_USERNAME, MQTT_PASSWORD);

    Serial.printf("Connecting to MQTT %s:%u\n", MQTT_HOST, MQTT_PORT);
    if (mqttClient.connect(MQTT_HOST, MQTT_PORT)) {
      Serial.println("MQTT_CONNECTED");
      break;
    }
    Serial.printf("MQTT connection failed, error=%d; retrying in 2s\n", mqttClient.connectError());
    delay(2000);
  }
}

void setup() {
  Serial.begin(115200);
  delay(500);
  mqttClient.setKeepAliveInterval(30 * 1000);
  connectWiFi();
  connectMqtt();
}

void loop() {
  if (WiFi.status() != WL_CONNECTED || !mqttClient.connected()) {
    connectMqtt();
  }
  mqttClient.poll();

  const unsigned long now = millis();
  if (now - lastPublishMs < PUBLISH_INTERVAL_MS) return;
  lastPublishMs = now;

  const float temperature = 38.0f + static_cast<float>((messageNumber * 7) % 91) / 10.0f;
  const float vibration = 1.0f + static_cast<float>((messageNumber * 13) % 25) / 10.0f;
  char payload[192];
  snprintf(payload, sizeof(payload),
           "{\"message_id\":\"%s-%06lu\",\"device_id\":\"%s\",\"temperature_c\":%.1f,\"vibration_mm_s\":%.1f,\"uptime_ms\":%lu}",
           MQTT_CLIENT_ID, messageNumber, DEVICE_ID, temperature, vibration, now);

  const int messageSize = mqttClient.beginMessage(MQTT_TOPIC, false, MQTT_QOS);
  const size_t written = mqttClient.print(payload);
  const int result = mqttClient.endMessage();
  if (messageSize && written == strlen(payload) && result == 1) {
    Serial.printf("PUBLISH_ACKED %s %s\n", MQTT_TOPIC, payload);
    ++messageNumber;
  } else {
    Serial.printf("PUBLISH_FAILED result=%d\n", result);
  }
}
