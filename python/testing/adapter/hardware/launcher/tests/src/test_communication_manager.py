import json

from python.testing.adapter.hardware.launcher.communication_manager import CommunicationManager


def get_fixture(pathname_fixture):
    with open(pathname_fixture, "r") as file:
        return json.load(file)


class TestCommunicationManager:
    def setup_class(cls):
        cls.communication_manager = CommunicationManager(fixture_obj=get_fixture("../fixtures/network_interface.json"))

    def test_get_valid_pair_params(self):
        row_answer = self.communication_manager.get_all_elements(l2mtu="1592")
        for item in row_answer:
            assert "l2mtu" in item, "object 'l2mtu' dont contains in answer"
            assert "1592" in item.values(), "object '1592' dont contains in answer"

    def test_get_unvalid_key(self):
        row_answer = self.communication_manager.get_all_elements(no_valid_key="1592")
        assert not row_answer, "answer is not empty list"

    def test_get_unvalid_value(self):
        row_answer = self.communication_manager.get_all_elements(l2mtu="no_valid_value")
        assert not row_answer, "answer is not empty list"

    def test_get_unvalid_key_value(self):
        row_answer = self.communication_manager.get_all_elements(no_valid_key="no_valid_value")
        assert not row_answer, "answer is not empty list"

    def test_call_root_command_print_single_address(self):
        row_answer = self.communication_manager.call_root_command("ip/address/print", {})
        count_address = 0
        for item in row_answer:
            if "address" in item:
                count_address += 1
        assert count_address == 1, "more than one address is used"

    def test_call_root_command_print_default_address(self):
        row_answer = next(self.communication_manager.call_root_command("ip/address/print", {}))
        if "address" in row_answer:
            assert row_answer["address"] == b"192.168.65.2/24", "non-default address is used"

    def test_call_root_command_ping_unvalid(self):
        for i, item_answer in enumerate(
                self.communication_manager.call_root_command(
                    "ping", {"address": "192.168.65.228", "count": "4"})):
            assert item_answer["seq"] == "{0}".format(i).encode(), "status is not valid"
            assert item_answer["host"] == b"192.168.65.2" or item_answer["host"] == b"192.168.65.228", \
                "host is not valid"
            assert item_answer["status"] == b"host unreachable" or item_answer["status"] == b"timeout", \
                "status is not valid"
            assert item_answer["sent"] == "{0}".format(i+1).encode(), "sent is not valid"
            assert item_answer["received"] == b"0", "received is not valid"
            assert item_answer["packet-loss"] == b"100", "packet-loss is not valid"

    def test_call_root_command_ping_valid(self):
        for i, item_answer in enumerate(self.communication_manager.call_root_command(
                "ping", {"address": "192.168.65.2", "count": "4"})):
            assert item_answer["seq"] == "{0}".format(i).encode(), "status is not valid"
            assert item_answer["host"] == b"192.168.65.2", "host is not valid"
            assert item_answer["sent"] == "{0}".format(i+1).encode(), "sent is not valid"
            assert item_answer["received"] == "{0}".format(i+1).encode(), "received is not valid"
            assert item_answer["packet-loss"] == b"0", "packet-loss is not valid"
