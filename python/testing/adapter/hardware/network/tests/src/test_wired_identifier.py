import json
import os

from python.testing.adapter.hardware.network.wired_identifier import \
    get_globalhost_ip, set_ip_config, get_ip_ftp_client


class TestWiredIdentifier:
    def make_copy_test_file(origin_file_name, copy_file_name="test_copy_config.json"):
        def decorator(func):
            def wrapper(*args, **kwargs):
                os.popen(f"cp ../fixtures/{origin_file_name} ../fixtures/{copy_file_name}")
                os.wait()
                try:
                    res = func(*args, **kwargs)
                finally:
                    os.remove(f"../fixtures/{copy_file_name}")
                return res
            return wrapper
        return decorator

    def setup_method(self):
        self.external_ip = get_globalhost_ip()

    def test_type_get_globalhost_ip(self):
        assert 11 <= len(self.external_ip) <= 15, "Have is not valid length"
        assert isinstance(self.external_ip, str), "Have is not valid type"

    @make_copy_test_file("opc_ua_settings.json")
    def test_set_ip_opc_config(self):
        set_ip_config(
            path_file="../fixtures/test_copy_config.json",
            key_ip="url",
            prefix_url="opc.tcp://",
            suffix_url=":4840",
            select_filter=".65."
        )
        with open("../fixtures/test_copy_config.json", "r") as file:
            fixture_obj = json.load(file)
        assert "opc.tcp://" in fixture_obj["url"], "set protocol value is incorrect"
        assert ":4840" in fixture_obj["url"], "set port value is incorrect"
        assert 27 <= len(fixture_obj["url"]) <= 30, "set value is incorrect in length"

    @make_copy_test_file("opc_ua_settings.json")
    def test_set_ip_opc_config_compare_generated_origin_files(self):
        set_ip_config(
            path_file="../fixtures/test_copy_config.json",
            key_ip="url",
            prefix_url="opc.tcp://",
            suffix_url=":4840",
            select_filter=".65."
        )
        with open("../fixtures/opc_ua_settings.json", "r") as file_origin:
            obj_origin = json.load(file_origin)
        with open("../fixtures/test_copy_config.json", "r") as file_generated:
            obj_generated = json.load(file_generated)
        for pair_origin, pair_generated in zip(obj_origin.items(), obj_generated.items()):
            if "url" != pair_origin[0] and isinstance(pair_origin[1], str) and "opc.tcp://" not in pair_origin[1]:
                assert pair_origin == pair_generated, "File has been modified in unnecessary places"

    @make_copy_test_file("dhcpcd.conf", copy_file_name="test_dhcpcd.conf")
    def test_type_get_ip_ftp_client(self):
        ip_ftp_client = get_ip_ftp_client(path_file="../fixtures/test_dhcpcd.conf")
        assert ip_ftp_client == "192.168.65.77", "Read invalid ip address from DEV partition"

