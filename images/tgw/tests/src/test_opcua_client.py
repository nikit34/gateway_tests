#!/usr/bin/env pipenv-shebang
from datetime import datetime, timedelta
import json
import pytest
import random
from time import sleep
import re
import shutil

from conftest import (
    fixtures_path,
    lazy_get_file,
    logs_path,
    get_fixture,
    call_power_manager_reset,
    call_monitor_boot_ftp_bootstrap,
    call_monitor_boot_kaspersky_os,
    logging_result
)
from python.testing.datasource.content_config.editor_config import EditorConfig
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer
from python.testing.datasource.permissions.generator_pair_opcua import generate_pair_opcua
from python.testing.adapter.hardware.comparator import comparators
from python.testing.adapter.hardware.network.wired_identifier import (
    get_globalhost_ip,
    get_ip_ftp_client,
    set_ip_config
)
from scripts.hardware.ftp_client import FTPClient
from scripts.hardware.multithread_ftp_client import FTPClientMultiThreaded


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "remove_ftp_logs_upload_ftp_client"
)
class TestSubscription:
    @classmethod
    def setup_class(cls):
        cls.data_points_obj = get_fixture(fixtures_path, "data_points.json")
        cls.opc_settings_obj = get_fixture(fixtures_path, "opc_ua_settings.json")
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    @staticmethod
    def diff_lines(found_lines, check_lines):
        return len(found_lines) == len(check_lines), \
               "Not all tuning lines were found in output: " + str(set(check_lines) - set(found_lines)) + \
               " reverse should be set(): " + str(set(found_lines) - set(check_lines))

    def whisper_opcua_server(self, timeout):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            data_points_obj=self.data_points_obj,
            opc_settings_obj=self.opc_settings_obj,
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity
        )
        opc.start()
        sleep(timeout)
        opc.stop()

    def test_contains_lines_output_setup_connection(self):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16969
        """
        check_lines = [
            "info/client	Selected Endpoint opc.tcp://" + get_globalhost_ip() +
            ":4840 with SecurityMode None and SecurityPolicy http://opcfoundation.org/UA/SecurityPolicy#None",
            "info/client	Client Status: ChannelState: Open, SessionState: Activated, ConnectStatus: Good",
            "Info: OPC UA Demo Client has established connection"
        ]
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.whisper_opcua_server(10)
        mon.disconnect()
        found_lines = []
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for check_line in check_lines:
                    if check_line in line:
                        assert check_line not in found_lines, "OPS UA output is repeated"
                        found_lines.append(check_line)
        status, msg = self.diff_lines(found_lines, check_lines)
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            "tmp_logs/test_contains_lines_output_opcua_setup_connection.log"
        ), msg

    def test_contains_lines_output_inactive_connection(self):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16975
        """
        check_lines = [
            "info/client	Client Status: ChannelState: Open, SessionState: Activated, ConnectStatus: Good",
            "Error: OPC UA Demo Client is processed in an invalid state",
            "Warning: OPC UA Demo Client is not disconnected after error, request reconnection",
            "Info: OPC UA Demo Client was requested to reconnect, trying to disconnect"
        ]
        repeat_check_lines = [
            "warn/channel	Connection 0 | SecureChannel 0 | Could not receive with StatusCode BadConnectionClosed",
            "Info: OPC UA Demo Client is establishing connection",
            "warn/network	Connection to opc.tcp://" + get_globalhost_ip() +
            ":4840 failed with error: Connection refused",
            "Error: Can't connect OPC UA Demo Client: BadDisconnect",
            "Info: OPC UA Demo Client will try to reconnect after timeout"
        ]
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.whisper_opcua_server(10)
        sleep(20)
        mon.disconnect()
        found_lines = []
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for check_line in check_lines:
                    if check_line in line:
                        assert check_line not in found_lines, "OPS UA output is repeated"
                        found_lines.append(check_line)
                for repeat_check_line in repeat_check_lines:
                    if repeat_check_line in line and repeat_check_line not in found_lines:
                        found_lines.append(repeat_check_line)
        status, msg = self.diff_lines(found_lines, check_lines + repeat_check_lines)
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            "tmp_logs/test_contains_lines_output_inactive_connection.log"
        ), msg

    def test_contains_lines_output_repeat_connection(self):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16977
        """
        check_lines = [
            "info/client	Client Status: ChannelState: Open, SessionState: Activated, ConnectStatus: Good",
            "Info: OPC UA Demo Client has established connection"
        ]
        after_lines = [
            "info/client	Client Status: ChannelState: Fresh, SessionState: Closed, ConnectStatus: BadDisconnect",
            "Info: OPC UA Demo Client will try to reconnect after timeout"
        ]
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.whisper_opcua_server(10)
        sleep(20)
        self.whisper_opcua_server(10)
        mon.disconnect()
        found_lines = []
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for after_line in after_lines:
                    if after_line in line and after_line not in found_lines:
                        found_lines.append(after_line)
                if len(found_lines) >= len(after_lines):
                    for check_line in check_lines:
                        if check_line in line and check_line not in found_lines:
                            found_lines.append(check_line)
        status, msg = self.diff_lines(found_lines, list(check_lines + after_lines))
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            "tmp_logs/test_contains_lines_output_repeat_connection.log"
        ), msg


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "remove_ftp_logs_upload_ftp_client"
)
class TestReadingCycle:
    """
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/17408
    """

    @classmethod
    def setup_class(cls):
        cls.config_path_opcua = "/IDS/app/Core/config/transfer/opc_ua/client/"
        cls.config_path_navigation = "/IDS/app/Core/config/transfer/navigation/"
        cls.config_path_mindsphere = "/IDS/app/Core/config/transfer/mind_sphere/agent/"
        cls.client_config_name = "OpcUaClientSettings-0.json"
        cls.template_config_name = "opc_ua_settings.json"
        cls.mapping_config_name = "GuideSettings-0.json"
        cls.mindsphere_config_name = "MindSphereAgentSettings-0.json"
        cls.client_config_edit_name = "opc_ua_settings_edit_client.json"
        cls.server_config_edit_name = "opc_ua_settings_edit_server.json"
        cls.mapping_config_edit_name = "GuideSettings_generated-0.json"
        cls.mindsphere_config_edit_name = "MindSphereAgentSettings_generated-0.json"
        shutil.copyfile(fixtures_path + cls.mapping_config_name, fixtures_path + cls.mapping_config_edit_name)
        shutil.copyfile(fixtures_path + cls.mindsphere_config_name, fixtures_path + cls.mindsphere_config_edit_name)
        shutil.copyfile(fixtures_path + cls.template_config_name, fixtures_path + cls.client_config_edit_name)
        shutil.copyfile(fixtures_path + cls.template_config_name, fixtures_path + cls.server_config_edit_name)
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    test_data = [
        (5, 0, 20, {"Int": 10}),
        (5, 10, 20, {"Int": 10}),
        (10, 0, 30, {"Int": 10}),
        (10, 10, 30, {"Int": 10})
    ]

    @staticmethod
    def edit_config_mindsphere(config_name, gen_count_types):
        data_points = []
        with open(fixtures_path + config_name, "r+") as file:
            data = json.load(file)
            for name_data_point, count_data_point in gen_count_types.items():
                index_subtract = count_data_point
                while index_subtract > 0:
                    current_index = count_data_point - index_subtract
                    data_points.append({
                        "id": current_index,
                        "name": name_data_point + str(current_index),
                        "dataPointId": name_data_point + str(current_index)
                    })
                    index_subtract -= 1
            data["dataPoints"] = data_points
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()

    @staticmethod
    def edit_config_mapping(config_name, gen_count_types):
        roadmap = []
        with open(fixtures_path + config_name, "r+") as file:
            data = json.load(file)
            count_data_points = gen_count_types.values()
            for i in range(sum(count_data_points)):
                roadmap.append({
                    "sourcePortId": i,
                    "targetPortId": i
                })
            data["roadmap"] = roadmap
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()

    @staticmethod
    def edit_config_readig_cycle(config_name, reading_cycle_value):
        with open(fixtures_path + config_name, "r+") as file:
            data = json.load(file)
            data["readingCycle"] = reading_cycle_value
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()

    @staticmethod
    def edit_config_nodes(config_name, gen_count_types):
        nodes = []
        with open(fixtures_path + config_name, "r+") as file:
            data = json.load(file)
            for name_data_point, count_data_point in gen_count_types.items():
                index_subtract = count_data_point
                while index_subtract > 0:
                    current_index = count_data_point - index_subtract
                    nodes.append({
                        "id": current_index,
                        "name": name_data_point + str(current_index),
                        "nodeId": "ns=2;s=" + name_data_point + str(current_index)
                    })
                    index_subtract -= 1
            data["nodes"] = nodes
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()

    def pass_opcua_config(self):
        client_names = [
            self.client_config_edit_name,
            self.mapping_config_edit_name,
            self.mindsphere_config_edit_name
        ]
        server_names = [
            self.config_path_opcua + self.client_config_name,
            self.config_path_navigation + self.mapping_config_name,
            self.config_path_mindsphere + self.mindsphere_config_name
        ]
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=self.config_path_opcua + self.client_config_name)
            ftp_client.write_on_server_more(
                client_names=client_names,
                server_names=server_names
            )

    def payload_opcua(self, gen_count_types, writing_cycle_server, timeout):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            gen_count_types=gen_count_types,
            opc_settings_obj=get_fixture(fixtures_path, self.server_config_edit_name),
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity,
            sleep_interval_global=writing_cycle_server
        )
        opc.start()
        sleep(timeout)
        opc.stop()

    @staticmethod
    def check_output_interval_dataitems(gen_count_types, reading_cycle_client):
        reading_cycle_client_ms = reading_cycle_client * 1250
        lower_bound_reading_cycle_client_ms = reading_cycle_client * 750
        count_lines_dataitem = 0
        line_operation = None
        bound_count_data_points = sum(gen_count_types.values()) * 2
        with open("logs/monitor_kos.log", "r") as file:
            for line in file.readlines():
                split_line = line.split(" ", maxsplit=4)
                if len(split_line) != 5:
                    continue
                line_time = split_line[1]
                line_operation = split_line[3]
                if line_operation in ["PUT", "GET"]:
                    if count_lines_dataitem == bound_count_data_points:
                        current_time = datetime.strptime(line_time, "%H:%M:%S,%f")
                        try:
                            assert timedelta(milliseconds=lower_bound_reading_cycle_client_ms) < \
                                   current_time - last_start_time, "lower bound"
                            assert current_time - last_start_time < \
                                   timedelta(milliseconds=reading_cycle_client_ms), "top bound"
                        except AssertionError as err:
                            print("Variables are not grouped by time for "
                                  f"{err}\nCurrent time: {current_time}\nLast start time: {last_start_time}")
                            logging_result(
                                False,
                                "logs/monitor_kos.log",
                                "tmp_logs/test_contains_lines_output_less_value_client.log"
                            )
                            raise err
                        count_lines_dataitem = 1
                        last_start_time = current_time
                    elif count_lines_dataitem != 0:
                        count_lines_dataitem += 1
                    else:
                        last_start_time = datetime.strptime(line_time, "%H:%M:%S,%f")
        return line_operation is not None

    @pytest.mark.parametrize("reading_cycle_client,writing_cycle_server,timeout,gen_count_types", test_data)
    def test_contains_lines_output_less_value_client(
        self,
        reading_cycle_client,
        writing_cycle_server,
        timeout,
        gen_count_types
    ):
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        set_ip_config(
            path_file=fixtures_path + self.client_config_edit_name,
            key_ip="url",
            prefix_url="opc.tcp://",
            suffix_url=":4840",
            select_filter=".65."
        )
        set_ip_config(
            path_file=fixtures_path + self.server_config_edit_name,
            key_ip="url",
            prefix_url="opc.tcp://",
            suffix_url=":4840",
            select_filter=".65."
        )
        self.edit_config_mindsphere(self.mindsphere_config_edit_name, gen_count_types)
        self.edit_config_mapping(self.mapping_config_edit_name, gen_count_types)
        self.edit_config_readig_cycle(self.client_config_edit_name, reading_cycle_client)
        self.edit_config_readig_cycle(self.server_config_edit_name, writing_cycle_server)
        self.edit_config_nodes(self.client_config_edit_name, gen_count_types)
        self.edit_config_nodes(self.server_config_edit_name, gen_count_types)
        self.pass_opcua_config()
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        sleep(5)
        self.payload_opcua(gen_count_types, writing_cycle_server, timeout)
        mon.disconnect()
        status = self.check_output_interval_dataitems(gen_count_types, reading_cycle_client)
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            "tmp_logs/test_contains_lines_output_less_value_client.log"
        ), "Interval time check was not performed"


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "remove_ftp_logs_upload_ftp_client",
)
class TestPassCompletenessCompliance:
    @classmethod
    def setup_class(cls):
        cls.errors = []
        cls.name_edit = "opc_ua_settings_edit.json"
        cls.config_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.name_edit)
        shutil.copyfile(fixtures_path + "opc_ua_settings.json", fixtures_path + cls.name_edit)
        cls.gen_count_types = {"Int": 5}
        cls.timeout = 300
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    def setup_data_points(self):
        global_index = 0
        nodes = []
        for type_data_points, count_data_points in self.gen_count_types.items():
            for i in range(count_data_points):
                node = {
                    "id": i + global_index,
                    "name": type_data_points + str(i),
                    "nodeId": "ns=2;s=" + type_data_points + str(i)
                }
                nodes.append(node)
            global_index += count_data_points + 1
        self.config_editor.edit_config("setup_field", ("nodes",), nodes)

    def pass_opcua_config(self):
        server_config = "/IDS/app/Core/config/transfer/opc_ua/client/OpcUaClientSettings-0.json"
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=server_config)
            ftp_client.write_on_server(
                client_name=self.name_edit,
                server_name=server_config
            )

    def payload_opcua(self):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            gen_count_types=self.gen_count_types,
            opc_settings_obj=get_fixture(fixtures_path, self.name_edit),
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity,
            sleep_interval_global=2
        )
        opc.start()
        sleep(self.timeout)
        opc.stop()

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
        assert logging_result(
            give_in - take <= 5,
            "logs/monitor_kos.log",
            "tmp_logs/test_pass_int_opcua_monitor.log"
        ), f"Transmitted {name} incorrectly"

    def test_pass_int_monitor(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/17601
        '''
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        self.setup_data_points()
        self.pass_opcua_config()
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.payload_opcua()
        mon.disconnect()
        for name_type in self.gen_count_types.keys():
            res_int = comparators.OpcUaMonitor(
                regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"),
                gen_log_variable=lazy_get_file(logs_path, name_type + ".log"),
                regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"),
                gen_log_monitor=lazy_get_file(logs_path, "monitor_kos.log")
            )()
            self.compare("CmpOpcUaMonitor", res_int[0], res_int[1], name_type)

    @classmethod
    def teardown_class(cls):
        if cls.errors:
            raise AssertionError(cls.errors)


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "prepare_opcua_connection",
    "remove_ftp_logs_upload_ftp_client",
)
class TestSecurityConnect:
    """
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16966
    """

    @classmethod
    def setup_class(cls):
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        cls.prepare_pairs_opcua()
        cls.server_name_edit = "opc_ua_settings_edit_server.json"
        cls.client_name_edit = "opc_ua_settings_edit_client.json"
        cls.server_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.server_name_edit)
        cls.client_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.client_name_edit)
        cls.errors = []
        cls.data_points_obj = get_fixture(fixtures_path, "data_points.json")
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    @staticmethod
    def generate_pairs_opcua():
        client_names = []
        server_names = []
        set_owner_pairs = ("client", "server")
        set_format_pairs = ("DER", "PEM")
        set_mode_pairs = ("valid", "old", "bad", "short")
        for owner_pair in set_owner_pairs:
            for format_pair in set_format_pairs:
                for mode_pair in set_mode_pairs:
                    output_name = mode_pair + "_" + format_pair.lower() + "_" + owner_pair
                    generate_pair_opcua(
                        fixtures_path,
                        owner_pair=owner_pair,
                        format_pair=format_pair,
                        mode_pair=mode_pair,
                        output_dir="IDS/",
                        output_name=output_name
                    )
                    client_names.append("IDS/" + output_name + ".crt")
                    server_names.append("/IDS/app/Core/pki/certs/transfer/opc_ua/client/" + output_name + ".crt")
                    if owner_pair == "client":
                        client_names.append("IDS/" + output_name + ".key")
                        server_names.append("/IDS/app/Core/pki/private/transfer/opc_ua/client/" + output_name + ".key")
        return client_names, server_names

    @classmethod
    def prepare_pairs_opcua(cls):
        client_names, server_names = cls.generate_pairs_opcua()
        with FTPClientMultiThreaded(
            count_threads=3,
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.write_on_server_more(
                client_names=client_names,
                server_names=server_names
            )
        print("FTP upload certificates and private keys for test is compiled")

    test_data = get_fixture(fixtures_path, "data/opcua_client_security_connect.json")

    @staticmethod
    def _prepare_lines(check_lines):
        known_functions = [
            "get_globalhost_ip"
        ]
        for index_line, check_line in enumerate(check_lines):
            for known_function in known_functions:
                if known_function in check_line:
                    index_start_func = check_line.index(known_function)
                    for i, symbol in enumerate(check_line[index_start_func + 2:]):
                        if symbol == ")":
                            index_end_func = index_start_func + i + 3
                            break
                    else:
                        raise ValueError("Called function was not found in string")
                    output = eval(check_line[index_start_func:index_end_func])
                    if not isinstance(output, str):
                        raise TypeError("Return type not expected")
                    check_lines[index_line] = check_line[:index_start_func] + output + check_line[index_end_func:]
        return check_lines

    @staticmethod
    def _prepare_regex_lines(check_regex_lines):
        template_replacement = "(id"
        for i in range(len(check_regex_lines)):
            if template_replacement in check_regex_lines[i]:
                edit_line = check_regex_lines[i].replace(template_replacement, "\\" + template_replacement)
                len_edit_line = len(edit_line) - 1
                check_regex_lines[i] = edit_line[:len_edit_line] + edit_line[len_edit_line].replace(")", "\)")
        return check_regex_lines

    def prepare_check_lines(self, check_lines, check_regex_lines):
        return self._prepare_lines(check_lines), self._prepare_regex_lines(check_regex_lines)

    def pass_opcua_config(self):
        client_config = "/IDS/app/Core/config/transfer/opc_ua/client/OpcUaClientSettings-0.json"
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=client_config)
            ftp_client.write_on_server(
                client_name=self.client_name_edit,
                server_name=client_config
            )
        print("FTP upload config of OPC clients for test is compiled")

    def payload_opcua(self, security_pair_name):
        opc = OpcUaServer(
            name_source_dir=fixtures_path + "IDS/",
            data_points_obj=self.data_points_obj,
            opc_settings_obj=get_fixture(fixtures_path, self.server_name_edit),
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity,
            security_pair_name=security_pair_name
        )
        try:
            opc.start()
            print("Payload OPC UA in processing")
            sleep(10)
        finally:
            opc.stop()

    @staticmethod
    def get_count_regex_option_lines(check_regex_lines):
        count_regex_option_lines = len(check_regex_lines)
        for regex_line in check_regex_lines:
            count_regex_option_lines += regex_line.count("|") - regex_line.count("\|")
        return count_regex_option_lines

    def check_lines_output_contains(self, check_lines, check_regex_lines, name_log):
        print("Check result test in processing")
        found_lines = []
        found_indexes = []
        len_check_lines_sep_index = len(check_lines)
        repeat_index = 0
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for i, check_line in enumerate(check_lines):
                    if check_line in line:
                        found_lines.append(check_line)
                        found_indexes.append(i)
                        break
                else:
                    for i, check_regex_line in enumerate(check_regex_lines):
                        if re.search(check_regex_line, line) is not None:
                            if check_regex_line in found_lines:
                                repeat_index += 1
                            else:
                                found_lines.append(check_regex_line)
                            found_indexes.append(i + len_check_lines_sep_index + repeat_index)
                            break
        len_general_check_lines = len_check_lines_sep_index + self.get_count_regex_option_lines(check_regex_lines)
        if len(found_indexes) != len_general_check_lines:
            for i in range(len_general_check_lines):
                try:
                    assert logging_result(
                        i in found_indexes,
                        "logs/monitor_kos.log",
                        "tmp_logs/" + name_log + ".log"
                    ), "Security settings you set were not validated: " \
                       f"Correct template № {i}:\n'{check_line}'\n" \
                       f"Was found: {check_line in found_lines}\n" \
                       "Description test: " + name_log + ".log"
                except AssertionError as err:
                    self.errors.append(err)

    @pytest.mark.parametrize("server_security,client_security,check_lines,check_regex_lines,name_log", test_data)
    def test_security(self, server_security, client_security, check_lines, check_regex_lines, name_log):
        check_lines, check_regex_lines = self.prepare_check_lines(check_lines, check_regex_lines)
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        shutil.copyfile(fixtures_path + "opc_ua_settings.json", fixtures_path + self.client_name_edit)
        shutil.copyfile(fixtures_path + "opc_ua_settings.json", fixtures_path + self.server_name_edit)
        self.server_editor.edit_config("setup_field", ("security", "mode",), server_security["mode"])
        self.server_editor.edit_config("setup_field", ("security", "policy",), server_security["policy"])
        self.client_editor.edit_config("setup_field", ("security",), client_security)
        self.pass_opcua_config()
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.payload_opcua(security_pair_name=server_security["security_pair_name"])
        mon.disconnect()
        self.check_lines_output_contains(check_lines, check_regex_lines, name_log)

    @classmethod
    def teardown_class(cls):
        if cls.errors:
            for error in cls.errors:
                print(error)
            raise AssertionError(cls.errors)


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "prepare_opcua_connection",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client",
)
class TestHeartbeat:
    @staticmethod
    def setup_class(cls):
        cls.server_name_edit = "opc_ua_settings_edit_server.json"
        cls.client_name_edit = "opc_ua_settings_edit_client.json"
        cls.mapping_name_edit = "GuideSettings-0_edit.json"
        shutil.copyfile(fixtures_path + "opc_ua_settings.json", fixtures_path + cls.client_name_edit)
        shutil.copyfile(fixtures_path + "opc_ua_settings.json", fixtures_path + cls.server_name_edit)
        shutil.copyfile(fixtures_path + "GuideSettings-0.json", fixtures_path + cls.mapping_name_edit)
        cls.server_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.server_name_edit)
        cls.client_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.client_name_edit)
        cls.mapping_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.mapping_name_edit)
        cls.regex_monitor = get_fixture(fixtures_path, "regex_monitor.json")
        cls.data_points_obj = get_fixture(fixtures_path, "data_points.json")
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    _mapping_roadmap = [
        {
            "sourcePortId": i,
            "targetPortId": i
        } for i in range(6)
    ]

    test_data = [
        (
            {
                "id": 5,
                "name": "Heartbeat",
                "timeout": 3
            },
            _mapping_roadmap
        ),
        (
            {
                "id": 5,
                "name": "Heartbeat",
                "timeout": 5
            },
            _mapping_roadmap
        )
    ]

    def pass_opcua_config(self):
        client_names = [
            self.client_name_edit,
            self.mapping_name_edit
        ]
        client_config = "/IDS/app/Core/config/transfer/opc_ua/client/OpcUaClientSettings-0.json"
        mapping_config = "/IDS/app/Core/config/transfer/navigation/GuideSettings-0.json"
        server_names = [
            client_config,
            mapping_config
        ]
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=client_config)
            ftp_client.delete_on_server(name=mapping_config)
            ftp_client.write_on_server_more(
                client_names=client_names,
                server_names=server_names
            )
        print("FTP upload config of OPC clients for test is compiled")

    def payload_opcua(self):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            data_points_obj=self.data_points_obj,
            opc_settings_obj=get_fixture(fixtures_path, "opc_ua_settings_edit_server.json"),
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity
        )
        try:
            opc.start()
            sleep(15)
        finally:
            opc.stop()

    def get_timestamp(self, line):
        raw = re.search(self.regex_monitor["dataItem"]["timestamp"], line)
        if raw is not None:
            return datetime.strptime(raw.group(1), "%Y-%m-%dT%H:%M:%S.%fZ")

    def prepare_heartbeat(self, heartbeat, roadmap):
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        self.server_editor.edit_config("setup_field", ("heartbeat",), heartbeat)
        self.client_editor.edit_config("setup_field", ("heartbeat",), heartbeat)
        self.mapping_editor.edit_config("setup_field", ("roadmap",), roadmap)
        self.pass_opcua_config()
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.payload_opcua()
        mon.disconnect()

    @pytest.mark.parametrize("heartbeat,roadmap", test_data)
    def test_count_heartbeats(self, heartbeat, roadmap):
        name_log = "test_count_heartbeats_" + str(heartbeat["timeout"])
        self.prepare_heartbeat(heartbeat, roadmap)
        count_heartbeat_get = 0
        count_heartbeat_put = 0
        with open("logs/monitor_kos.log", "r") as file:
            for line in file.readlines():
                if "Heartbeat" in line:
                    if "PUT" in line:
                        count_heartbeat_put += 1
                    elif "GET" in line:
                        count_heartbeat_get += 1
        assert logging_result(
            count_heartbeat_put > 2,
            "logs/monitor_kos.log",
            "tmp_logs/" + name_log + ".log"
        ), "Number of heartbeats per PUT operation is less than minimum limit"
        assert logging_result(
            count_heartbeat_get > 2,
            "logs/monitor_kos.log",
            "tmp_logs/" + name_log + ".log"
        ), "Number of heartbeats per GET operation is less than minimum limit"

    @pytest.mark.parametrize("heartbeat,roadmap", test_data)
    def test_timedelta_heartbeat(self, heartbeat, roadmap):
        name_log = "test_timedelta_heartbeat_" + str(heartbeat["timeout"])
        self.prepare_heartbeat(heartbeat, roadmap)
        max_timedelta_heartbeat_get_put = 0.5
        last_timestamp_hearbeat_put = last_timestamp_hearbeat_get = None
        max_timedelta_heartbeat_put = max_timedelta_heartbeat_get = heartbeat["timeout"] * 1.25
        with open("logs/monitor_kos.log", "r") as file:
            for line in file.readlines():
                if "Heartbeat" in line:
                    timestamp = self.get_timestamp(line)
                    if "PUT" in line:
                        if last_timestamp_hearbeat_put is not None:
                            assert logging_result(
                                timestamp - last_timestamp_hearbeat_put < timedelta(
                                    seconds=max_timedelta_heartbeat_put
                                ),
                                "logs/monitor_kos.log",
                                "tmp_logs/" + name_log + ".log"
                            ), "Timeout heartbeat for operation PUT exceeds allowable limit"
                            assert logging_result(
                                timestamp - last_timestamp_hearbeat_get < timedelta(
                                    seconds=max_timedelta_heartbeat_get_put
                                ),
                                "logs/monitor_kos.log",
                                "tmp_logs/" + name_log + ".log"
                            ), "Timeout heartbeat between operations GET-PUT exceeds allowable limit"
                        last_timestamp_hearbeat_put = timestamp
                    elif "GET" in line:
                        if last_timestamp_hearbeat_get is not None:
                            assert logging_result(
                                timestamp - last_timestamp_hearbeat_get < timedelta(
                                    seconds=max_timedelta_heartbeat_get
                                ),
                                "logs/monitor_kos.log",
                                "tmp_logs/" + name_log + ".log"
                            ), "Timeout heartbeat for operation GET exceeds allowable limit"
                        last_timestamp_hearbeat_get = timestamp
