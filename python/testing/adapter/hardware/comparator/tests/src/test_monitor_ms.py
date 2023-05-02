import json
import pytest

from python.testing.adapter.hardware.comparator import comparators


def get_fixture(fixture_path, name_fixture):
    with open(fixture_path + name_fixture, "r") as file:
        return json.load(file)


def lazy_get_file(file_path, name_file):
    with open(file_path + name_file, "r") as file:
        for line in file.readlines():
            yield line


class TestCmpOpcUaMS:
    def setup_method(self):
        self.fixtures_path = __file__.split("src/")[0] + "fixtures/"
        self.logs_path = __file__.split("src/")[0] + "src/logs/"

    def test_init_valid(self):
        cmp_monitor_ms = comparators.MonitorMS(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(self.logs_path, "Boolean_ms.log")
        )
        assert str(type(cmp_monitor_ms.gen_log_monitor)) == "<class \'generator\'>", \
            "field 'gen_log_monitor' is not generator"
        assert str(type(cmp_monitor_ms.gen_log_variable_ms)) == "<class \'generator\'>", \
            "field 'gen_log_opcua' is not generator"

    def test_cmp_boolean(self):
        res_boolean = comparators.MonitorMS(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(self.logs_path, "Boolean_ms.log")
        )()
        assert 1.0 >= res_boolean[1] / res_boolean[0] > 0.9, "Loss on test data is too large"

    def test_cmp_int(self):
        res_int = comparators.MonitorMS(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(self.logs_path, "Int_ms.log")
        )()
        assert 1.0 >= res_int[1] / res_int[0] > 0.9, "Loss on test data is too large"

    def test_cmp_long(self):
        res_long = comparators.MonitorMS(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(self.logs_path, "Long_ms.log")
        )()
        assert 1.0 >= res_long[1] / res_long[0] > 0.9, "Loss on test data is too large"

    def test_cmp_double(self):
        res_double = comparators.MonitorMS(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(self.logs_path, "Double_ms.log")
        )()
        assert 1.0 >= res_double[1] / res_double[0] > 0.9, "Loss on test data is too large"

    def test_cmp_string(self):
        res_string = comparators.MonitorMS(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(self.logs_path, "String_ms.log")
        )()
        assert 1.0 >= res_string[1] / res_string[0] > 0.9, "Loss on test data is too large"
