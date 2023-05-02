import json
from opcua import ua, common

from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer
from python.testing.datasource.opcua.opc_ua_dataclasses import NamesPolitics


def get_fixture(pathname_fixture):
    with open(pathname_fixture, "r") as file:
        return json.load(file)


class TestOpcUaServer:
    def setup_method(self):
        self.opc = OpcUaServer(
            name_source_dir="../fixtures/",
            data_points_obj=get_fixture("../fixtures/data_points.json"),
            opc_settings_obj=get_fixture("../fixtures/opc_ua_settings.json")
        )

    def test_port_attr_after_apply_opc_settings_config(self):
        self.opc.apply_opc_settings_config()
        assert hasattr(self.opc, "port"), "OpcUaServer don't have 'port' attribute"
        assert str(self.opc.port) == '4840', "OpcUaServer has an invalid 'port' value"

    def test_nodes_id_attr_after_apply_opc_settings_config(self):
        self.opc.apply_opc_settings_config()
        assert hasattr(self.opc, "nodes_id"), "OpcUaServer don't have 'nodes_id' attribute"
        for node_id in self.opc.nodes_id:
            assert "ns=2;s=" in node_id, "OpcUaServer has an invalid 'nodes_id' value"

    def test_folder_attr_after_apply_opc_settings_config(self):
        self.opc.apply_opc_settings_config()
        assert hasattr(self.opc, "folder"), "OpcUaServer don't have 'folder' attribute"
        assert str(self.opc.folder) == "ns=2;i=1", "OpcUaServer has an invalid 'folder' value"

    def test_sleep_interval_attribute_after_apply_data_points_config(self):
        self.opc.apply_opc_settings_config()
        self.opc.apply_data_points_config()
        assert hasattr(self.opc, "sleep_interval_global"), "OpcUaServer don't have 'sleep_interval' attribute"
        assert self.opc.sleep_interval_global == 2, "OpcUaServer has an invalid 'sleep_interval' value"

    @staticmethod
    def check_types_data_points(data_points):
        for data_name, timestamp_source, timestamps, values, statuses, \
            count_data_items, sleep_interval_local, variable in data_points:
            assert isinstance(data_name, str), "'data_name' contains invalid type"
            assert isinstance(timestamp_source, str) or timestamp_source is None, \
                "'timestamp_source' contains invalid type"
            assert str(type(timestamps)) == "<class \'generator\'>", "'timestamps' contains invalid type"
            assert str(type(values)) == "<class \'generator\'>", "'values' not is None"
            assert str(type(statuses)) == "<class \'generator\'>", "'statuses' contains invalid type"
            assert isinstance(count_data_items, int), "'count_data_items' contains invalid type"
            assert isinstance(sleep_interval_local, int), "'sleep_interval_local' contains invalid type"
            assert isinstance(variable, common.node.Node), "'variable' contains invalid type"

    def test_types_variables_after_apply_data_points_config(self):
        self.opc.apply_opc_settings_config()
        data_points = self.opc.apply_data_points_config()
        self.check_types_data_points(data_points)

    def test_generated_types_variables_after_apply_data_points_config(self):
        self.opc.name_data_points_config = None
        self.opc.apply_opc_settings_config()
        data_points = self.opc.apply_data_points_config()
        self.check_types_data_points(data_points)

    def test_generated_infinity_types_variables(self):
        self.opc = OpcUaServer(
            name_source_dir="../fixtures/",
            data_points_obj=None,
            opc_settings_obj=get_fixture("../fixtures/opc_ua_settings.json")
        )
        self.opc.apply_opc_settings_config()
        data_points = self.opc.apply_data_points_config()
        self.check_types_data_points(data_points)

    def test_types_after_apply_data_points_config_without_variable(self):
        for variable in ["timestamps", "values", "statuses"]:
            self.opc = OpcUaServer(
                name_source_dir="../fixtures/",
                data_points_obj=get_fixture(f"../fixtures/data_points_without_{variable}.json"),
                opc_settings_obj=get_fixture("../fixtures/opc_ua_settings.json")
            )
            self.opc.apply_opc_settings_config()
            data_points = self.opc.apply_data_points_config()
            self.check_types_data_points(data_points)

    def test_values_variables_after_apply_data_points_config(self):
        self.opc.apply_opc_settings_config()
        data_points = self.opc.apply_data_points_config()
        for data_name, _, _, _, _, _, _, variable in data_points:
            assert data_name == variable.nodeid.Identifier, "Name of node does not match type of node"

    def test_proc_after_start(self):
        self.opc.start()
        assert hasattr(self.opc, "proc"), "OpcUaServer don't have 'proc' attribute"
        assert self.opc.proc.is_alive(), "OpcUaServer does not have running process"
        self.opc.proc.terminate()

    def test_select_one_security_politics(self):
        test_necessary_security_politics = [
            "Basic128Rsa15_Sign",
            "Basic128Rsa15_SignAndEncrypt",
            "Basic256_Sign",
            "Basic256_SignAndEncrypt",
            "Basic256Sha256_Sign",
            "Basic256Sha256_SignAndEncrypt"
        ]
        test_selected_security_politics = [
            [ua.SecurityPolicyType.Basic128Rsa15_Sign],
            [ua.SecurityPolicyType.Basic128Rsa15_SignAndEncrypt],
            [ua.SecurityPolicyType.Basic256_Sign],
            [ua.SecurityPolicyType.Basic256_SignAndEncrypt],
            [ua.SecurityPolicyType.Basic256Sha256_Sign],
            [ua.SecurityPolicyType.Basic256Sha256_SignAndEncrypt]
        ]
        names_politics = NamesPolitics()
        for test_data, test_expected in zip(test_necessary_security_politics, test_selected_security_politics):
            test_actual = self.opc._select_security_politics(names_politics, *test_data.split("_")[::-1])
            assert test_expected == test_actual
