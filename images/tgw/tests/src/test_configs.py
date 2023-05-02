import pytest
import random
import re
import shutil
from time import sleep

from images.tgw.tests.src.conftest import (
    get_fixture,
    fixtures_path,
    call_power_manager_reset,
    call_monitor_boot_ftp_bootstrap,
    call_monitor_boot_kaspersky_os,
    logging_result,
)
from python.testing.adapter.hardware.network.wired_identifier import (
    get_ip_ftp_client,
    set_ip_config
)
from python.testing.datasource.content_config.editor_config import EditorConfig
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer
from scripts.hardware.ftp_client import FTPClient


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "prepare_mqtt_connection",
    "remove_ftp_logs_upload_ftp_client"
)
class TestFormatConfig:
    @classmethod
    def setup_class(cls):
        cls.data_points_obj = get_fixture(fixtures_path, "data_points.json")
        cls.opc_settings_obj = get_fixture(fixtures_path, "opc_ua_settings.json")
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    test_data = [
        (
            "mqtt_settings.json",
            "/IDS/app/Core/config/transfer/mqtt/publisher/",
            "MqttPublisherSettings-0.json",
            "MqttPublisherSettings-0.yaml"
        ),
        (
            "opc_ua_settings.json",
            "/IDS/app/Core/config/transfer/opc_ua/client/",
            "OpcUaClientSettings-0.json",
            "OpcUaClientSettings-0.yaml"
        ),
    ]

    @staticmethod
    def pass_config(client_name, server_path, server_name_correct, server_name_incorrect):
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=server_path + server_name_correct)
            ftp_client.write_on_server(
                client_name=client_name,
                server_name=server_path + server_name_incorrect
            )

    def payload_opcua(self):
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            data_points_obj=self.data_points_obj,
            opc_settings_obj=self.opc_settings_obj,
            logging_mode=self.logging_mode,
            gen_infinity=self.gen_infinity
        )
        try:
            opc.start()
            sleep(10)
        finally:
            opc.stop()

    @pytest.mark.parametrize("client_name,server_path,server_name_correct,server_name_incorrect", test_data)
    def test_contains_lines_output_invalid_format(
        self,
        client_name,
        server_path,
        server_name_correct,
        server_name_incorrect
    ):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16988
        """
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        self.pass_config(client_name, server_path, server_name_correct, server_name_incorrect)
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        self.payload_opcua()
        mon.disconnect()
        check_line = f"Warning: Key does not match pattern and has been ignored (key = {server_name_incorrect})"
        count_occurrence = 0
        label_test = client_name[:-5]
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                if check_line in line:
                    count_occurrence += 1
        assert logging_result(
            count_occurrence == 1,
            "logs/monitor_kos.log",
            f"tmp_logs/test_contains_lines_output_invalid_format_{label_test}.log"
        ), f"Invalid format warning {label_test} is not correct"
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=server_path + server_name_incorrect)


@pytest.fixture
def collect_data(request):
    test_data = [
        {
            "naming": {
                "client_name_template": "mqtt_settings.json",
                "server_path": "/IDS/app/Core/config/transfer/mqtt/publisher/",
                "server_name": "MqttPublisherSettings-0.json",
                "client_name_edit": "mqtt_settings_edit.json"
            },
            "network": {
                "key_ip": "serverUri",
                "prefix_url": "tcp://",
                "suffix_url": ":1883",
                "select_filter": ".66.",
            }
        },
        {
            "naming": {
                "client_name_template": "opc_ua_settings.json",
                "server_path": "/IDS/app/Core/config/transfer/opc_ua/client/",
                "server_name": "OpcUaClientSettings-0.json",
                "client_name_edit": "opc_ua_settings_edit.json"
            },
            "network": {
                "key_ip": "url",
                "prefix_url": "opc.tcp://",
                "suffix_url": ":4840",
                "select_filter": ".65.",
            }
        },
    ]
    index_select_data = 0 if request.param_index < 14 else 1
    test_data[index_select_data]["test_data"] = request.param
    return test_data[index_select_data]


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_mqtt_connection",
    "remove_ftp_logs_upload_ftp_client"
)
class TestContentConfig:
    @classmethod
    def setup_class(cls):
        cls.data_points_obj = get_fixture(fixtures_path, "data_points.json")
        cls.opc_settings_obj = get_fixture(fixtures_path, "opc_ua_settings.json")
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    test_data_mqtt_skeleton = get_fixture(fixtures_path, "data/mqtt_client_content_config.json")
    test_data_opcua_skeleton = get_fixture(fixtures_path, "data/opcua_client_content_config.json")
    full_test_data = test_data_mqtt_skeleton + test_data_opcua_skeleton

    @staticmethod
    def pass_config(naming):
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=fixtures_path,
            timeout=240
        ) as ftp_client:
            ftp_client.delete_on_server(name=naming["server_path"] + naming["server_name"])
            ftp_client.write_on_server(
                client_name=naming["client_name_edit"],
                server_name=naming["server_path"] + naming["server_name"]
            )

    @staticmethod
    def check_output_contains(check_lines):
        count_occurrence = 0
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                if re.search(check_lines, line) is not None:
                    count_occurrence += 1
        return count_occurrence == 1

    @pytest.mark.parametrize("collect_data", full_test_data, indirect=True)
    def test_contains_lines_output_invalid_content(self, collect_data):
        """
        missing content: https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/17173
        invalid value: https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/17224
        """
        naming = collect_data["naming"]
        network = collect_data["network"]
        test_data = collect_data["test_data"]
        expected_line = {
            "no_pair": fr"Warning: Failed to parse settings from the storage \(key = {naming['server_name']}\): .*" + \
                       r"\[json.exception.out_of_range.403\] .*' not found",
            "invalid_type": fr"Warning: Failed to parse settings from the storage \(key = {naming['server_name']}\): .*" + \
                            r"\[json.exception.type_error.302\] .*type must be string|array|number, but is number",
            "invalid_struct": r"Warning: Failed to parse settings from the storage " + \
                              fr"\(key = {naming['server_name']}\): .*\[json.exception.type_error.304\] .*" + \
                              r"cannot use at\(\) with number",
        }
        shutil.copyfile(
            fixtures_path + naming["client_name_template"],
            fixtures_path + naming["client_name_edit"]
        )
        client_editor = EditorConfig(fixtures_path=fixtures_path, name_edit=naming["client_name_edit"])
        check_fields_data_item = test_data["data_item"]
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        set_ip_config(
            path_file=fixtures_path + naming["client_name_edit"],
            key_ip=network["key_ip"],
            prefix_url=network["prefix_url"],
            suffix_url=network["suffix_url"],
            select_filter=network["select_filter"]
        )
        if test_data["way_edit_config"] == "setup_field":
            value_field = client_editor.edit_config(
                test_data["way_edit_config"],
                check_fields_data_item,
                random.random()
            )
        elif test_data["way_edit_config"] == "delete_field":
            value_field = client_editor.edit_config(
                test_data["way_edit_config"],
                check_fields_data_item
            )
        else:
            raise ValueError("Test data has an invalid value in field 'way_edit_config'")
        self.pass_config(naming)
        client_editor.edit_config("setup_field", check_fields_data_item, value_field)
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        sleep(10)
        mon.disconnect()
        check_lines = expected_line[test_data["expected_item"]]
        status = self.check_output_contains(check_lines)
        substring_test_data_items = '_'.join(test_data['data_item'])
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            f"tmp_logs/test_contains_lines_output_{test_data['expected_item']}_{substring_test_data_items}.log"
        ), "Invalid format warning is not correct"
