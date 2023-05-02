import json

from python.testing.adapter.hardware.launcher.communication_manager import CommunicationManager
from python.testing.adapter.hardware.launcher.power_manager import PowerManager


def get_fixture(pathname_fixture):
    with open(pathname_fixture, "r") as file:
        return json.load(file)


class TestPowerManager:
    def setup_class(cls):
        cls.power_manager = PowerManager(fixture_obj=get_fixture("../fixtures/network_interface.json"))
        cls.communication_manager = CommunicationManager(fixture_obj=get_fixture("../fixtures/network_interface.json"))

    def setup_method(self):
        self.power_manager.turn_on()

    def test_availability_after_turn_on(self):
        row_answer = self.communication_manager.get_all_elements(name="ether8")
        for item in row_answer:
            assert item["poe-out"] == "forced-on", "PoE interface has invalid state"

    def test_unavailability_after_turn_off(self):
        self.power_manager.turn_off()
        row_answer = self.communication_manager.get_all_elements(name="ether8")
        for item in row_answer:
            assert item["poe-out"] == "off", "PoE interface has invalid state"

    def test_availability_after_reset(self):
        self.power_manager.reset()
        row_answer = self.communication_manager.get_all_elements(name="ether8")
        for item in row_answer:
            assert item["poe-out"] == "forced-on", "PoE interface has invalid state"
