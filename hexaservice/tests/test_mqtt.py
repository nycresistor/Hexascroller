"""MQTT lifecycle checks without a broker or attached display hardware."""

import importlib.util
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


class MQTTTests(unittest.TestCase):
    def setUp(self):
        dependencies = {
            name: MagicMock()
            for name in ("paho", "paho.mqtt", "paho.mqtt.client", "PIL",
                         "led_panel", "fontutil")
        }
        dependencies["led_panel"].PANEL_WIDTH = 120
        dependencies["led_panel"].PANEL_HEIGHT = 7
        spec = importlib.util.spec_from_file_location(
            "service_under_test", Path(__file__).resolve().parents[1] / "service.py"
        )
        self.service = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, dependencies), patch.object(
            sys, "argv", ["service.py"]
        ), patch.dict(os.environ, {"MQTT_HOST": "test-broker.local"}):
            spec.loader.exec_module(self.service)
        self.client = MagicMock()
        self.service.state.client = self.client

    def test_connect_and_reconnect_publish_retained_discovery_and_current_state(self):
        service = self.service
        for powered in (False, True):
            self.client.reset_mock()
            service.state.powered = powered
            service.state.inverted = True
            service.on_mqtt_connect(self.client, None, {}, 0)
            configs = {}
            for call in self.client.publish.call_args_list:
                topic, payload = call.args
                self.assertTrue(call.kwargs["retain"])
                if topic.endswith("/config"):
                    configs[topic] = json.loads(payload)
            self.assertEqual(len(configs), 2)
            for unique_id, state_topic in (
                ("hexascroller", "hexascroller/power"),
                ("hexascroller_invert", "hexascroller/invert"),
            ):
                config = configs[f"homeassistant/switch/{unique_id}/config"]
                self.assertEqual(config["unique_id"], unique_id)
                self.assertEqual(config["state_topic"], state_topic)
                self.assertEqual(config["command_topic"], state_topic + "/set")
                self.assertEqual(config["availability_topic"], "hexascroller/available")
                self.assertEqual(config["device"]["identifiers"], ["hexascroller"])
            self.client.publish.assert_any_call(
                service.TOPIC_POWER, b"ON" if powered else b"OFF", qos=0, retain=True
            )
            self.client.publish.assert_any_call(service.TOPIC_INVERT, b"ON", qos=0, retain=True)
            for topic in (service.TOPIC_POWER_SET, service.TOPIC_INVERT_SET, service.TOPIC_MESSAGE):
                self.client.subscribe.assert_any_call(topic, qos=0)

    def test_failed_connection_does_not_announce_availability(self):
        self.service.on_mqtt_connect(self.client, None, {}, 5)
        self.client.publish.assert_not_called()
        self.client.subscribe.assert_not_called()

    def test_commands_update_retained_states(self):
        service = self.service
        for payload in (b"ON", b"OFF"):
            service.on_mqtt_message(self.client, None, SimpleNamespace(
                topic=service.TOPIC_INVERT_SET, payload=payload
            ))
            self.client.publish.assert_called_with(service.TOPIC_INVERT, payload, retain=True)
            service.on_mqtt_message(self.client, None, SimpleNamespace(
                topic=service.TOPIC_POWER_SET, payload=payload
            ))
            with patch.object(service, "render_time_bitmap", return_value=b""), patch.object(service.time, "sleep"):
                service.panel_update()
            self.client.publish.assert_any_call(service.TOPIC_POWER, payload, retain=True)

    def test_last_will_is_set_before_connect_and_shutdown_is_retained(self):
        service = self.service
        service.state.running = False
        with patch.object(service.signal, "signal"):
            service.main()
        calls = self.client.method_calls
        will_index = next(i for i, call in enumerate(calls) if call[0] == "will_set")
        connect_index = next(i for i, call in enumerate(calls) if call[0] == "connect_async")
        self.assertLess(will_index, connect_index)
        self.client.connect_async.assert_called_once_with("test-broker.local", 1883, 60)
        self.client.will_set.assert_called_once_with(
            service.TOPIC_AVAILABILITY, "offline", qos=1, retain=True
        )
        self.client.publish.assert_any_call(service.TOPIC_POWER, b"OFF", qos=0, retain=True)
        self.client.publish.assert_any_call(service.TOPIC_AVAILABILITY, "offline", retain=True)
        self.client.publish.return_value.wait_for_publish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
