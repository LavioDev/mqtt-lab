#include <ArduinoMqttClient.h>
#include <esp_system.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>
#include <cstring>

#include "ca_cert.h"
#include "firmware_config.h"

#ifndef NTP_SERVER
#define NTP_SERVER "pool.ntp.org"
#endif

WiFiClientSecure networkClient;
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

// mbedtls checks the certificate validity dates, so the clock must be set first.
void syncClock() {
  if (time(nullptr) > 1700000000) return;
  configTime(0, 0, NTP_SERVER);
  while (time(nullptr) < 1700000000) {
    delay(500);
    Serial.print('t');
  }
  Serial.println("\nClock synchronized");
}

void connectMqtt() {
  while (!mqttClient.connected()) {
    connectWiFi();
    syncClock();
    networkClient.setCACert(CA_CERT);
    mqttClient.setId(MQTT_CLIENT_ID);
    mqttClient.setUsernamePassword(MQTT_USERNAME, MQTT_PASSWORD);

    Serial.printf("Connecting to MQTT/TLS %s:%u\n", MQTT_HOST, MQTT_PORT);
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
  randomSeed(esp_random());
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

  const float temperature = static_cast<float>(random(360, 451)) / 10.0f;
  const float vibration = static_cast<float>(random(5, 41)) / 10.0f;
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
