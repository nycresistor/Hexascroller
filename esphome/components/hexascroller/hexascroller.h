#ifndef HEXASCROLLER_H
#define HEXASCROLLER_H

#include "esphome.h"
#include <string>

class HexascrollerComponent : public esphome::Component {
 public:
  HexascrollerComponent();
  virtual ~HexascrollerComponent() = default;

  void setup() override;
  void update() override;

  // Called via API to display a custom message on the panels
  void display_message(const std::string &message);
  // Called via API to switch back to displaying the time
  void display_time();

 protected:
  std::string current_message_;
  bool show_time_{true};
};

#endif  // HEXASCROLLER_H
