#!/usr/bin/env pipenv-shebang
import pytest

from conftest import get_fixture, lazy_get_file, fixtures_path, logs_path
from python.testing.adapter.hardware.comparator import comparators


@pytest.mark.usefixtures(
    "pc_env_prepare",
    'power_manager',
    'monitor_boot_ftp_bootstrap',
    'prepare_opcua_connection',
    "valid_generate_pair_opcua",
    'mindsphere',
    'remove_ftp_logs_upload_ftp_client',
    'power_manager_reset',
    'monitor_boot_kaspersky_os',
    'opcua_server',
    'sleep_test'
)
class TestBaseline:
    @classmethod
    def setup_class(cls):
        cls.errors = []

    def compare(self, test_name, give_in, take, name):
        self.print_result_test(test_name, give_in, take, name)
        try:
            self.check_valid_transfer(give_in, take, name)
        except AssertionError as err:
            self.errors.append(err)

    @staticmethod
    def print_result_test(test_name, give_in, take, name):
        print(f"Name test: {test_name}, Type variable: {name}, Transfer (give -> take): (", give_in, " -> ", take, ")")

    @staticmethod
    def check_valid_transfer(give_in, take, name):
        assert give_in - take <= 5, f"Transmitted {name} incorrectly"

    def test_opcua_monitor(self):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16862
        """
        res_boolean = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_variable=lazy_get_file(logs_path, "Boolean.log"),
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log")
        )()
        res_int = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_variable=lazy_get_file(logs_path, "Int.log"),
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log")
        )()
        res_long = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_variable=lazy_get_file(logs_path, "Long.log"),
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log")
        )()
        res_double = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_variable=lazy_get_file(logs_path, "Double.log"),
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log")
        )()
        res_string = comparators.OpcUaMonitor(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_variable=lazy_get_file(logs_path, "String.log"),
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log")
        )()
        self.compare("CmpOpcUaMonitor", res_boolean[0], res_boolean[1], "boolean")
        self.compare("CmpOpcUaMonitor", res_int[0], res_int[1], "int")
        self.compare("CmpOpcUaMonitor", res_long[0], res_long[1], "long")
        self.compare("CmpOpcUaMonitor", res_double[0], res_double[1], "double")
        self.compare("CmpOpcUaMonitor", res_string[0], res_string[1], "string")

    def test_monitor_ms(self, mindsphere, sleep_test):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16863
        """
        mindsphere.save_values(*sleep_test)
        res_boolean = comparators.MonitorMS(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Boolean_ms.log")
        )()
        res_int = comparators.MonitorMS(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Int_ms.log")
        )()
        res_long = comparators.MonitorMS(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Long_ms.log")
        )()
        res_double = comparators.MonitorMS(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Double_ms.log")
        )()
        res_string = comparators.MonitorMS(
            regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
            gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "String_ms.log")
        )()
        self.compare("CmpMonitorMS", res_boolean[0], res_boolean[1], "boolean")
        self.compare("CmpMonitorMS", res_int[0], res_int[1], "int")
        self.compare("CmpMonitorMS", res_long[0], res_long[1], "long")
        self.compare("CmpMonitorMS", res_double[0], res_double[1], "double")
        self.compare("CmpMonitorMS", res_string[0], res_string[1], "string")

    def test_opcua_ms(self, mindsphere, sleep_test):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16864/
        """
        mindsphere.save_values(*sleep_test)
        res_boolean = comparators.OpcUaMS(
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(logs_path, "Boolean.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Boolean_ms.log")
        )()
        res_int = comparators.OpcUaMS(
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(logs_path, "Int.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Int_ms.log")
        )()
        res_long = comparators.OpcUaMS(
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(logs_path, "Long.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Long_ms.log")
        )()
        res_double = comparators.OpcUaMS(
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(logs_path, "Double.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "Double_ms.log")
        )()
        res_string = comparators.OpcUaMS(
            regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
            gen_log_variable=lazy_get_file(logs_path, "String.log"),
            gen_log_variable_ms=lazy_get_file(logs_path, "String_ms.log")
        )()
        self.compare("CmpOpcUaMs", res_boolean[0], res_boolean[1], "boolean")
        self.compare("CmpOpcUaMs", res_int[0], res_int[1], "int")
        self.compare("CmpOpcUaMs", res_long[0], res_long[1], "long")
        self.compare("CmpOpcUaMs", res_double[0], res_double[1], "double")
        self.compare("CmpOpcUaMs", res_string[0], res_string[1], "string")

    @classmethod
    def teardown_class(cls):
        if cls.errors:
            raise AssertionError(cls.errors)
