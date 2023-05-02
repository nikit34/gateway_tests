#!/usr/bin/env pipenv-shebang
import datetime
import json
import sys
from time import sleep

sys.path.insert(0, __file__.split("/images/")[0])
from python.testing.adapter.hardware.comparator import comparators
from python.testing.adapter.hardware.launcher.communication_manager import CommunicationManager
from python.testing.adapter.hardware.launcher.power_manager import PowerManager
from python.testing.adapter.hardware.monitor.monitor import Monitor
from python.testing.adapter.hardware.network.wired_identifier import set_ip_config, get_ip_ftp_client
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer
from scripts.hardware.ftp_client import FTPClient
from python.testing.retriever.mindsphere.aspects_manager import AspectsManager
from python.testing.retriever.mindsphere.assets_manager import AssetsManager
from python.testing.retriever.mindsphere.types_manager import TypesManager
from python.testing.retriever.mindsphere.datasource_manager import DataSourceManager
from python.testing.retriever.mindsphere.data_mapping_manager import DataMappingManager
from python.testing.retriever.mindsphere.timeseries_manager import TimeseriesManager
from python.testing.retriever.mindsphere.config_generator import ConfigGenerator


def get_fixture(fixture_path, name_fixture):
    with open(fixture_path + name_fixture, "r") as file:
        return json.load(file)


def lazy_get_file(file_path, name_file):
    with open(file_path + name_file, "r") as file:
        for line in file.readlines():
            yield line


def create_cfg(config_path, name_config, json_data):
    with open(config_path + name_config, "w") as fp:
        json.dump(json_data, fp, indent=4)


fixtures_path = __file__.split("src/")[0] + "fixtures/"
logs_path = __file__.split("src/")[0] + "src/logs/"

communication_manager = CommunicationManager(fixture_obj=get_fixture(fixtures_path, "network_interface.json"))
power_manager = PowerManager(fixture_obj=get_fixture(fixtures_path, "network_interface.json"))

try:
    power_manager.turn_off()
    if not communication_manager.check_poe_status():
        print(f"Channel {communication_manager.interfaces.path} is turned off")
    else:
        raise ConnectionError("PoE available")

    power_manager.turn_on()
    if communication_manager.check_poe_status():
        print(f"Channel {communication_manager.interfaces.path} is turned on")
    else:
        raise ConnectionError("PoE not available")

    with Monitor() as mon:
        if mon.check_data(trigger="Press enter to boot the selected OS"):
            mon.write_data(b"\033[B")
            mon.write_data(b"\r\n")
            print("Boot FTP Bootstrap choice")
        else:
            raise ConnectionError("Monitor don't capture line")
        if mon.check_data(
                trigger=f"using static address {get_ip_ftp_client(fixtures_path + 'DEV/dhcpcd.conf')}/24"
        ):
            print("Boot FTP Bootstrap is ready")
        else:
            raise ConnectionError("Monitor don't capture line")

    fixture_obj = get_fixture(fixtures_path, "mindsphere_configuration.json")
    assets_inst = AssetsManager()
    mcl_asset_id = assets_inst.get_asset_id_by_name(fixture_obj["mclAssetName"])
    main_asset_id = assets_inst.get_asset_id_by_name(fixture_obj["parentAsset"])
    aspects_inst = AspectsManager(
        fixture_obj=get_fixture(fixtures_path, "data_points.json"), aspect_name=fixture_obj["systemTestAspectName"]
    )
    types_inst = TypesManager(
        aspect_name=fixture_obj["systemTestAspectName"], type_name=fixture_obj["systemTestTypeName"]
    )
    assets_inst = AssetsManager(type_name=fixture_obj["systemTestTypeName"])
    datasource_inst = DataSourceManager(aspects_inst.variables, mcl_asset_id)
    datasource_id = datasource_inst.get_datasource_id_etag()
    dm_inst = DataMappingManager(datasource_inst.variables, mcl_asset_id)

    try:
        aspects_inst.create_aspect()
        print('Aspects created')
        types_inst.create_type()
        print('Types created')
        asset_id = assets_inst.create_asset(main_asset_id, fixture_obj["systemTestAssetName"])
        print('Assets created')
        datasource_inst.create_datasource()
        print("Datasource's created")
        dm_inst.map_datapoints(asset_id, fixture_obj["systemTestAspectName"])
        print('Data mapping created')

        onb = assets_inst.generate_onb(mcl_asset_id)
        cfg_generator_inst = ConfigGenerator(
            datasource_inst.variables, onb, datasource_id, fixtures_path
        )
        ms_data = cfg_generator_inst.generate_ms_agent_config()
        navigator_data = cfg_generator_inst.generate_transfer_config()

        create_cfg(fixtures_path, "IDS/MindSphereAgentSettings-0.json", ms_data)
        print('MindSphere config generated')
        create_cfg(fixtures_path, "IDS/GuideSettings-0.json", navigator_data)
        print('Hub config generated')

        set_ip_config(
            path_file=__file__.split("src/")[0] + "fixtures/" + "IDS/OpcUaClientSettings-0.json",
            key_ip="url",
            prefix_url="opc.tcp://",
            suffix_url=":4840",
            select_filter=".65."
        )
        set_ip_config(
            path_file=__file__.split("src/")[0] + "fixtures/" + "opc_ua_settings.json",
            key_ip="url",
            prefix_url="opc.tcp://",
            suffix_url=":4840",
            select_filter=".65."
        )
        print("OPC UA configs of client & server updated")

        timeseries_inst = TimeseriesManager(aspects_inst.variables, asset_id, fixture_obj["systemTestAspectName"])

        client_names = [
            "DEV/dhcpcd.conf",
            "ENW/dhcpcd_dynamic.conf",
            "INW/dhcpcd.conf",
            "IDS/MindSphereAgentSettings-0.json",
            "IDS/MqttPublisherSettings-0.json",
            "IDS/GuideSettings-0.json",
            # "IDS/GuideSettings-1.json",
            "IDS/OpcUaClientSettings-0.json",
            "IDS/client.crt",
            "IDS/server.crt",
            "IDS/mindsphere.io.crt",
            "IDS/client.key"
        ]
        server_names = [
            "DEV/etc/dhcpcd.conf",
            "ENW/etc/dhcpcd.conf",
            "INW/etc/dhcpcd.conf",
            "IDS/app/Core/config/transfer/mind_sphere/agent/MindSphereAgentSettings-0.json",
            "IDS/app/Core/config/transfer/mqtt/publisher/MqttPublisherSettings-0.json",
            "IDS/app/Core/config/transfer/navigation/GuideSettings-0.json",
            # "IDS/app/Core/config/transfer/navigation/GuideSettings-1.json",
            "IDS/app/Core/config/transfer/opc_ua/client/OpcUaClientSettings-0.json",
            "IDS/app/Core/pki/certs/transfer/opc_ua/client/client.crt",
            "IDS/app/Core/pki/certs/transfer/opc_ua/client/server.crt",
            "IDS/app/Core/pki/certs/transfer/mind_sphere/agent/mindsphere.io.crt",
            "IDS/app/Core/pki/private/transfer/opc_ua/client/client.key"
        ]
        with FTPClient(
                host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            ftp_client.write_on_server_more(client_names=client_names, server_names=server_names)
        print("FTPClient pass data")

        sleep(1)
        power_manager.reset()
        print("Power manager was reset")

        with Monitor(logging_file="monitor_kos.log") as mon:
            if mon.check_data(trigger="Boot Kaspersky OS"):
                mon.write_data(b"\n")
                print("Boot Kaspersky OS choice")
            else:
                raise ConnectionError("Monitor don't capture line")
            if mon.check_data(trigger="adding route to 192.168.65.0/24"):
                print("Boot Kaspersky OS is ready")
            else:
                raise ConnectionError("Monitor don't capture line")

            opc = OpcUaServer(
                name_source_dir=fixtures_path,
                data_points_obj=get_fixture(fixtures_path, "data_points.json"),
                opc_settings_obj=get_fixture(fixtures_path, "opc_ua_settings.json"),
                logging_mode="INFO",
                gen_infinity=True
            )

            try:
                opc.start()
                print("OpcUaServer start")

                start_time = datetime.datetime.now() - datetime.timedelta(hours=3)
                print("Test configured: ", start_time)
                sleep(240)
                end_time = datetime.datetime.now() + datetime.timedelta(minutes=20)
                print("Test completed: ", end_time)
            finally:
                opc.stop()
                print("OpcUaServer stop")

            timeseries_inst.save_values(start_time, end_time)

    finally:
        aspects_inst.delete_aspect()
        types_inst.delete_type()
        assets_inst.delete_asset()
        datasource_inst.delete_datasource()
        dm_inst.delete_datamappings()
        print("Created artifacts of MindSphere removed")

finally:
    power_manager.turn_off()
    print("Power manager was turned off")


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
print("CmpOpcUaMonitor -> res_boolean: ", res_boolean)
print("CmpOpcUaMonitor -> res_int: ", res_int)
print("CmpOpcUaMonitor -> res_long: ", res_long)
print("CmpOpcUaMonitor -> res_double: ", res_double)
print("CmpOpcUaMonitor -> res_string: ", res_string)

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
print("CmpOpcUaMs -> res_boolean: ", res_boolean)
print("CmpOpcUaMs -> res_int: ", res_int)
print("CmpOpcUaMs -> res_long: ", res_long)
print("CmpOpcUaMs -> res_double: ", res_double)
print("CmpOpcUaMs -> res_string: ", res_string)

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
print("CmpMonitorMS -> res_boolean: ", res_boolean)
print("CmpMonitorMS -> res_int: ", res_int)
print("CmpMonitorMS -> res_long: ", res_long)
print("CmpMonitorMS -> res_double: ", res_double)
print("CmpMonitorMS -> res_string: ", res_string)
