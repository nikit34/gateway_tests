#!/usr/bin/env pipenv-shebang
import ast
import pytest
import re
import shutil
import subprocess
from time import sleep

from conftest import (
    call_monitor_boot_kaspersky_os,
    call_monitor_boot_ftp_bootstrap,
    call_power_manager_reset,
    fixtures_path,
    get_fixture,
    logging_result
)
from python.testing.adapter.hardware.comparator.parsers import ParserMonitor, ParserOpcUa
from python.testing.adapter.hardware.network.wired_identifier import (
    get_ip_ftp_client,
    get_globalhost_ip,
    get_globalhost_interface
)
from python.testing.datasource.content_config.editor_config import EditorConfig
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer
from python.testing.receiver.mqtt.broker import Broker
from python.testing.receiver.mqtt.subscriber import Subscriber
from scripts.hardware.ftp_client import FTPClient


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "remove_ftp_logs_upload_ftp_client",
    "power_manager_reset",
    "monitor_boot_kaspersky_os"
)
class TestOutput:
    @staticmethod
    def diff_lines(found_lines, check_lines):
        return len(found_lines) == len(check_lines), \
               "Not all tuning lines were found in output: " + str(set(check_lines) - set(found_lines)) + \
               " reverse should be set(): " + str(set(found_lines) - set(check_lines))

    def test_contains_lines_output_setup_connection(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/18751
        '''
        check_lines = [
            "Starting the MQTT Publisher Manager Server service",
            "The MQTT Publisher Manager Server service has been started",
            "Info: All MqttPublisherSettings has been loaded",
            "Info: Starting the MQTT Demo Publisher service",
            "Info: MQTT Demo Publisher is trying to start connection attempts",
            "Info: The MQTT Demo Publisher service has been started",
            "Info: The MQTT Publisher Manager service has been started"
        ]
        found_lines = []
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for check_line in check_lines:
                    if check_line in line:
                        assert check_line not in found_lines, "MQTT output is repeated"
                        found_lines.append(check_line)
        status, msg = self.diff_lines(found_lines, check_lines)
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            "tmp_logs/test_contains_lines_output_mqtt_setup_connection.log"
        ), msg


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "prepare_mqtt_connection",
    "remove_ftp_logs_upload_ftp_client"
)
class TestOutputCompletenessCompliance:
    @classmethod
    def setup_class(cls):
        cls.timeout = 100
        cls.logging_mode = "INFO"
        cls.gen_infinity = True
        cls.parser_opcua = ParserOpcUa(regex_opcua=get_fixture(fixtures_path, "regex_opcua.json"))
        cls.parser_monitor = ParserMonitor(regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"))
        cls.subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
        cls.mqtt_sniffer_path = "/home/permi/tmp-tests/tests/scripts/hardware/network/mqtt/"
        cls.template_sniffer_run = [
            "sudo",
            "-S",
            "python3",
            cls.mqtt_sniffer_path + "sniffer.py"
        ]

    @staticmethod
    def pass_dhcp_config():
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
        ) as ftp_client:
            ftp_client.delete_on_server(name="/ENW/etc/dhcpcd.conf")
            ftp_client.write_on_server(client_name="ENW/dhcpcd.conf", server_name="/ENW/etc/dhcpcd.conf")

    def setup_mqtt(self, sniffer):
        self.broker = Broker()
        self.broker.start()
        sleep(1)
        self.subscriber = Subscriber(host=get_globalhost_ip(select_filter=".66."))
        self.subscriber.start()
        if sniffer:
            subprocess.Popen(
                self.template_sniffer_run + [
                    "--interface",
                    get_globalhost_interface(select_filter=".66."),
                    "--timeout",
                    str(self.timeout)
                ],
                stdin=self.subprocess_superuser.stdout
            )
        sleep(2)

    def payload_opcua(self):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            data_points_obj=get_fixture(fixtures_path, "data_points.json"),
            opc_settings_obj=get_fixture(fixtures_path, "opc_ua_settings.json"),
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity,
            logging_general=True
        )
        opc.start()
        sleep(self.timeout)
        opc.stop()

    def teardown_mqtt(self):
        self.broker.stop()
        self.subscriber.stop()
        self.subscriber.save_accepted()

    def prepare_test(self, sniffer):
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        self.pass_dhcp_config()
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.setup_mqtt(sniffer)
        self.payload_opcua()
        self.teardown_mqtt()
        mon.disconnect()

    @staticmethod
    def parse_mqtt_data_item(status, timestamp, value):
        return status[-1:], timestamp.replace("T", " ")[:-1], value.split(".")[0]

    def test_pass_data_tgw_mosquitto(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/18755
        '''
        self.prepare_test(sniffer=False)
        mqtt_file = open("logs/mqtt.log", "r")
        opcua_file = open("logs/all_variables.log", "r")
        for opcua_line in opcua_file.readlines():
            opcua_value = self.parser_opcua.parse_opcua_value(opcua_line)
            opcua_timestamp = self.parser_opcua.parse_opcua_timestamp(opcua_line)
            opcua_status = self.parser_opcua.parse_opcua_status(opcua_line)
            if None not in [opcua_value, opcua_timestamp, opcua_status]:
                line_found = False
                for mqtt_line in mqtt_file.readlines()[1:]:
                    raw_mqtt_status, raw_mqtt_timestamp, _, raw_mqtt_value = mqtt_line.rstrip().split(",")
                    mqtt_status, mqtt_timestamp, mqtt_value = self.parse_mqtt_data_item(
                        raw_mqtt_status, raw_mqtt_timestamp, raw_mqtt_value
                    )
                    if mqtt_status == opcua_status and \
                       mqtt_timestamp == opcua_timestamp and \
                       mqtt_value == opcua_value:
                        line_found = True
                        break
                assert logging_result(
                    line_found,
                    "logs/monitor_kos.log",
                    f"tmp_logs/test_pass_opcua_mqtt.log"
                ), "OPC UA values were not found\n" \
                   "Value: " + str(opcua_value) + "\n" + \
                   "Timestamp: " + str(opcua_timestamp) + "\n" + \
                   "Status: " + str(opcua_status)
        opcua_file.close()
        mqtt_file.close()

    def test_pass_data_opcua_sniffer(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/19124
        '''
        self.prepare_test(sniffer=True)
        sniffer_file = open("logs/mqtt_sniffer_history.log", "r")
        opcua_file = open("logs/all_variables.log", "r")
        for opcua_line in opcua_file.readlines():
            opcua_value = self.parser_opcua.parse_opcua_value(opcua_line)
            opcua_timestamp = self.parser_opcua.parse_opcua_timestamp(opcua_line)
            opcua_status = self.parser_opcua.parse_opcua_status(opcua_line)
            if None not in [opcua_value, opcua_timestamp, opcua_status]:
                line_found = False
                for sniffer_line in sniffer_file.readlines()[1:]:
                    raw_line = sniffer_line.rstrip().split(",")
                    raw_sniffer_status, raw_sniffer_timestamp, _, raw_sniffer_value = raw_line[3:7]
                    sniffer_status, sniffer_timestamp, sniffer_value = self.parse_mqtt_data_item(
                        raw_sniffer_status, raw_sniffer_timestamp, raw_sniffer_value
                    )
                    if sniffer_status == opcua_status and \
                        sniffer_timestamp == opcua_timestamp and \
                        sniffer_value == opcua_value:
                        line_found = True
                        break
                assert logging_result(
                    line_found,
                    "logs/monitor_kos.log",
                    f"tmp_logs/test_pass_opcua_sniffer.log"
                ), "OPC UA values were not found\n" \
                   "Value: " + str(opcua_value) + "\n" + \
                   "Timestamp: " + str(opcua_timestamp) + "\n" + \
                   "Status: " + str(opcua_status)
        opcua_file.close()
        sniffer_file.close()

    def test_pass_data_monitor_sniffer(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/19128
        '''
        self.prepare_test(sniffer=True)
        sniffer_file = open("logs/mqtt_sniffer_history.log", "r")
        monitor_file = open("logs/monitor_kos.log", "r")
        for monitor_line in monitor_file.readlines():
            monitor_value = self.parser_monitor.parse_monitor_value(monitor_line)
            monitor_timestamp = self.parser_monitor.parse_monitor_timestamp(monitor_line)
            monitor_status = self.parser_monitor.parse_monitor_status(monitor_line)
            if None not in [monitor_value, monitor_timestamp, monitor_status]:
                line_found = False
                for sniffer_line in sniffer_file.readlines()[1:]:
                    raw_line = sniffer_line.rstrip().split(",")
                    raw_sniffer_status, raw_sniffer_timestamp, _, raw_sniffer_value = raw_line[3:7]
                    sniffer_status, sniffer_timestamp, sniffer_value = self.parse_mqtt_data_item(
                        raw_sniffer_status, raw_sniffer_timestamp, raw_sniffer_value
                    )
                    if sniffer_status == monitor_status and \
                        sniffer_timestamp == monitor_timestamp and \
                        sniffer_value == monitor_value:
                        line_found = True
                        break
                assert logging_result(
                    line_found,
                    "logs/monitor_kos.log",
                    f"tmp_logs/test_pass_monitor_sniffer.log"
                ), "Monitor values were not found\n" \
                   "Value: " + str(monitor_value) + "\n" + \
                   "Timestamp: " + str(monitor_timestamp) + "\n" + \
                   "Status: " + str(monitor_status)
        monitor_file.close()
        sniffer_file.close()

    def test_count_success_dataitems(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/18753
        '''
        count_dataitems = 0
        last_found_counter = None
        self.prepare_test(sniffer=False)
        with open("logs/monitor_kos.log", "r") as monitor_file:
            for monitor_line in monitor_file.readlines():
                found_counter = re.search(r"success: ([0-9]+)", monitor_line)
                if found_counter is not None:
                    last_found_counter = found_counter.group(1)
        with open("logs/all_variables.log", "r") as opcua_file:
            for opcua_line in opcua_file.readlines():
                opcua_value = self.parser_opcua.parse_opcua_value(opcua_line)
                opcua_timestamp = self.parser_opcua.parse_opcua_timestamp(opcua_line)
                opcua_status = self.parser_opcua.parse_opcua_status(opcua_line)
                if None not in [opcua_value, opcua_timestamp, opcua_status]:
                    count_dataitems += 1
        assert logging_result(
            count_dataitems - int(last_found_counter) < 5,
            "logs/monitor_kos.log",
            "tmp_logs/test_count_success_dataitems.log"
        ), "Number dataItems successfully transferred: " \
            f"{count_dataitems} does not match counted value of MQTT counter: {last_found_counter}"


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "prepare_mqtt_connection",
    "remove_ftp_logs_upload_ftp_client"
)
class TestFlags:
    @classmethod
    def setup_class(cls):
        cls.timeout = 100
        cls.logging_mode = "INFO"
        cls.gen_infinity = True
        cls.name_edit = "mqtt_settings_edit.json"
        cls.mqtt_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=cls.name_edit)
        cls.subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
        cls.mqtt_sniffer_path = "/home/permi/tmp-tests/tests/scripts/hardware/network/mqtt/"
        cls.template_sniffer_run = [
            "sudo",
            "-S",
            "python3",
            cls.mqtt_sniffer_path + "sniffer.py"
        ]

    def pass_configs(self):
        server_config = "/IDS/app/Core/config/transfer/mqtt/publisher/MqttPublisherSettings-0.json"
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
        ) as ftp_client:
            ftp_client.delete_on_server(name="/ENW/etc/dhcpcd.conf")
            ftp_client.delete_on_server(name=server_config)
            ftp_client.write_on_server(client_name="ENW/dhcpcd.conf", server_name="/ENW/etc/dhcpcd.conf")
            ftp_client.write_on_server(client_name=self.name_edit, server_name=server_config)

    def setup_mqtt(self):
        self.broker = Broker()
        self.broker.start()
        sleep(1)
        self.subscriber = Subscriber(host=get_globalhost_ip(select_filter=".66."))
        self.subscriber.start()
        subprocess.Popen(
            self.template_sniffer_run + [
                "--interface",
                get_globalhost_interface(select_filter=".66."),
                "--timeout",
                str(self.timeout)
            ],
            stdin=self.subprocess_superuser.stdout
        )
        sleep(2)

    def payload_opcua(self):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            data_points_obj=get_fixture(fixtures_path, "data_points.json"),
            opc_settings_obj=get_fixture(fixtures_path, "opc_ua_settings.json"),
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity,
            logging_general=True
        )
        opc.start()
        sleep(self.timeout)
        opc.stop()

    def teardown_mqtt(self):
        self.broker.stop()
        self.subscriber.stop()
        self.subscriber.save_accepted()

    def prepare_test(self):
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        self.pass_configs()
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.setup_mqtt()
        self.payload_opcua()
        self.teardown_mqtt()
        mon.disconnect()

    test_data_lastwill = [
        ("1", "NotExist", "no exist"),
        ("1", "Boolean", "false"),
        ("1", "Int", "gregrh")
    ]

    @pytest.mark.parametrize("flag,topic_name,message", test_data_lastwill)
    def test_pass_will_fields_sniffer(self, flag, topic_name, message):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/19364
        '''
        shutil.copyfile(fixtures_path + "mqtt_settings.json", fixtures_path + self.name_edit)
        self.mqtt_editor.edit_config(
            "setup_field",
            ("lastWill",),
            {
                "topicName": topic_name,
                "message": message
            }
        )
        self.prepare_test()
        was_connect = False
        with open("logs/mqtt_sniffer_history.log", "r") as file:
            for line in file.readlines()[1:]:
                if was_connect:
                    raw_flag, raw_topic_name, raw_message = line.split(",")[13:16]
                    check_topic_name = ast.literal_eval(raw_topic_name).decode("utf-8")
                    check_message = ast.literal_eval(raw_message).decode("utf-8")
                    assert flag == raw_flag, f"Discrepancy Flag - Expected: {flag} Actual: {raw_flag}"
                    assert topic_name == check_topic_name, \
                        f"Discrepancy Topic Name - Expected: {topic_name} Actual: {check_topic_name}"
                    assert message == check_message, \
                        f"Discrepancy Message - Expected: {topic_name} Actual: {check_topic_name}"
                else:
                    if line.split(",", maxsplit=2)[1] == "MQTT connect":
                        was_connect = True
        assert was_connect, "Broker connection failed"

    test_data_qos = [("1", "0"), ("1", "1"), ("1", "2"), ("0", None)]

    @pytest.mark.parametrize("flag,qos", test_data_qos)
    def test_pass_qos_fields_sniffer(self, flag, qos):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/19366
        '''
        shutil.copyfile(fixtures_path + "mqtt_settings.json", fixtures_path + self.name_edit)
        if qos is not None:
            self.mqtt_editor.edit_config("setup_field", ("qualityOfService",), qos)
        else:
            qos = "0"
        self.prepare_test()
        was_connect = False
        with open("logs/mqtt_sniffer_history.log", "r") as file:
            for line in file.readlines()[1:]:
                if was_connect:
                    raw_flag, raw_qos = line.split(",")[11:13]
                    assert flag == raw_flag, f"Discrepancy Flag - Expected: {flag} Actual: {raw_flag}"
                    assert qos == raw_qos, \
                        f"Discrepancy QOS - Expected: {qos} Actual: {raw_qos}"
                else:
                    if line.split(",", maxsplit=2)[1] == "MQTT connect":
                        was_connect = True
        assert was_connect, "Broker connection failed"

    test_data_keep_alive = ["10", "-10", None]

    @pytest.mark.parametrize("keep_alive", test_data_keep_alive)
    def test_pass_keep_alive_fields_sniffer(self, keep_alive):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/19367
        '''
        shutil.copyfile(fixtures_path + "mqtt_settings.json", fixtures_path + self.name_edit)
        if keep_alive is not None:
            self.mqtt_editor.edit_config("setup_field", ("keepAlive",), keep_alive)
        else:
            keep_alive = "120"
        self.prepare_test()
        was_connect = False
        with open("logs/mqtt_sniffer_history.log", "r") as file:
            for line in file.readlines()[1:]:
                if was_connect:
                    raw_keep_alive = line.split(",")[8]
                    assert keep_alive == raw_keep_alive, \
                        f"Discrepancy Keep Alive - Expected: {keep_alive} Actual: {raw_keep_alive}"
                else:
                    if line.split(",", maxsplit=2)[1] == "MQTT connect":
                        was_connect = True
        assert was_connect, "Broker connection failed"
