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


class TestCmpOpcUaMonitor:
    def setup_method(self):
        self.fixtures_path = __file__.split("src/")[0] + "fixtures/"
        self.logs_path = __file__.split("src/")[0] + "src/logs/"

    def test_init_valid(self):
        cmp_opcua_monitor = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(self.logs_path, "Boolean.log")
        )
        assert str(type(cmp_opcua_monitor.gen_log_monitor)) == "<class \'generator\'>", \
            "field 'gen_log_monitor' is not generator"
        assert str(type(cmp_opcua_monitor.gen_log_opcua)) == "<class \'generator\'>", \
            "field 'gen_log_opcua' is not generator"

    def test_init_invalid_unnecessary_arguments(self):
        with pytest.raises(AttributeError) as exc_check:
            _ = comparators.OpcUaMonitor(
                regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
                gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
                regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
                gen_log_variable=lazy_get_file(self.logs_path, "Boolean.log"),
                gen_log_general=lazy_get_file(self.logs_path, "general.log")
            )
        assert "Second argument" in str(exc_check.value), "Another exception thrown"

    def test_cmp_boolean(self):
        res_boolean = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(self.logs_path, "Boolean.log"),
        )()
        assert 1.0 >= res_boolean[1] / res_boolean[0] > 0.9, "Loss on test data is too large"

    def test_cmp_int(self):
        res_int = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(self.logs_path, "Int.log"),
        )()
        assert 1.0 >= res_int[1] / res_int[0] > 0.9, "Loss on test data is too large"

    def test_cmp_long(self):
        res_long = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(self.logs_path, "Long.log"),
        )()
        assert 1.0 >= res_long[1] / res_long[0] > 0.9, "Loss on test data is too large"

    def test_cmp_double(self):
        res_double = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(self.logs_path, "Double.log"),
        )()
        assert 1.0 >= res_double[1] / res_double[0] > 0.9, "Loss on test data is too large"

    def test_cmp_string(self):
        res_string = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(self.logs_path, "String.log"),
        )()
        assert 1.0 >= res_string[1] / res_string[0] > 0.9, "Loss on test data is too large"

    def test_cmp_all_variables(self):
        res_general = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(self.fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(self.logs_path, "all_monitor_kos.log"),
            regex_opcua=get_fixture(self.fixtures_path, "regex_opcua.json"),
            gen_log_general=lazy_get_file(self.logs_path, "all_variables.log"),
        )()
        assert 1.0 >= res_general[1] / res_general[0] > 0.9, "Loss on test data is too large"
