from itertools import product
import json

from python.testing.adapter.hardware.launcher.connection import Manager


def get_fixture(pathname_fixture):
    with open(pathname_fixture, "r") as file:
        return json.load(file)


class TestConnection:
    def setup_class(cls):
        cls.manager = Manager(fixture_obj=get_fixture("../fixtures/network_interface.json"))
        cls.all_variants = ([False, True], [True, False])
        cls.test_data = [
            {"interfaces", "connection", "fixture_obj", "eth"}, {"interfaces", "connection", "fixture_obj", "eth"},
            {"interfaces", "connection", "fixture_obj", "eth"}, {"interfaces", "connection", "fixture_obj", "eth"}
        ]

    def test_apply_configuration(self):
        connection = self.manager.apply_configuration()
        assert connection.username == "api", "username is not valid"
        assert connection.host == "192.168.65.2", "host is not valid"
        assert connection.plaintext_login, "plaintext_login is not valid"
        assert connection.use_ssl, "use_ssl is not valid"
        assert not connection.ssl_verify, "ssl_verify is not valid"
        assert not connection.ssl_verify_hostname, "ssl_verify_hostname is not valid"
        assert connection.interface == "ether8", "interface is not valid"
        assert connection.resource == "/interface/ethernet", "resource is not valid"
        assert connection.reset_interval == 0.1, "reset_interval is not valid"

    def test_check_connect_all(self):
        for pair_mode, item_data in zip(product(*self.all_variants), self.test_data):
            @Manager.check_connect(connecting=pair_mode[0], disconnecting=pair_mode[1])
            def mock_func(self): return None
            assert mock_func(self.manager) is None, "function response has been changed"
            assert set(self.manager.__dict__.keys()) == item_data, "some attribute not set"

    def test_lazy_check_connect_all(self):
        for pair_mode, item_data in zip(product(*self.all_variants), self.test_data):
            @Manager.lazy_check_connect(connecting=pair_mode[0], disconnecting=pair_mode[1])
            def mock_func(self): return [None, ]
            res = next(mock_func(self.manager))
            assert res is None, "function response has been changed"
            assert set(self.manager.__dict__.keys()) == item_data, "some attribute not set"
