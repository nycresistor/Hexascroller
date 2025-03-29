#include "hexascroller.h"
#include "esphome/core/log.h"
#include <time.h>

static const char *TAG = "hexascroller";

HexascrollerComponent::HexascrollerComponent() : show_time_(true) {}

void HexascrollerComponent::setup() {
  // Initialisation code for LED panels and relay.
  ESP_LOGI(TAG, "HexascrollerComponent setup");
  // For example, setting up GPIO pins (update these as needed):
  pinMode(12, OUTPUT);  // Relay pin placeholder
  // TODO: Initialize each of the three LED panels on their separate pins.
}

void HexascrollerComponent::update() {
  // This update method is called every 1 second (as defined in hexascroller.yaml).
  if (show_time_) {
    // Display the current time.
    time_t now = time(nullptr);
    struct tm timeinfo;
    localtime_r(&now, &timeinfo);
    char buffer[16];
    strftime(buffer, sizeof(buffer), "%H:%M:%S", &timeinfo);
    ESP_LOGI(TAG, "Displaying time: %s", buffer);
    // TODO: Render the time using the preserved font onto each LED panel.
  } else {
    // Display the current message.
    ESP_LOGI(TAG, "Displaying message: %s", current_message_.c_str());
    // TODO: Render current_message_ onto each LED panel.
  }
}

void HexascrollerComponent::display_message(const std::string &message) {
  // Switch to displaying a custom message.
  current_message_ = message;
  show_time_ = false;
  ESP_LOGI(TAG, "Received message: %s", message.c_str());
  // TODO: Immediately update LED panels to show the new message.
}

void HexascrollerComponent::display_time() {
  // Switch back to displaying the time.
  show_time_ = true;
  ESP_LOGI(TAG, "Switching to time display");
  // TODO: Immediately update LED panels to show the current time.
}
