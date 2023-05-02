from datetime import datetime, timedelta
import json
import pytest
import re
import shutil
from time import sleep

from python.azure_api.test_plan_rest import AzureTestPlanRest
from python.azure_api.test_rest import AzureTestRest
from python.testing.adapter.hardware.launcher.communication_manager import CommunicationManager
from python.testing.adapter.hardware.launcher.power_manager import PowerManager
from python.testing.adapter.hardware.monitor.monitor import Monitor
from python.testing.adapter.hardware.network.pc_env_preparer import prepare
from python.testing.adapter.hardware.network.wired_identifier import (
    set_ip_config,
    set_globalhost_ip,
    get_ip_ftp_client,
    up_interface
)
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer
from python.testing.datasource.permissions.generator_pair_opcua import generate_pair_opcua
from scripts.hardware.ftp_client import FTPClient
from python.testing.retriever.mindsphere.aspects_manager import AspectsManager
from python.testing.retriever.mindsphere.assets_manager import AssetsManager
from python.testing.retriever.mindsphere.types_manager import TypesManager
from python.testing.retriever.mindsphere.datasource_manager import DataSourceManager
from python.testing.retriever.mindsphere.data_mapping_manager import DataMappingManager
from python.testing.retriever.mindsphere.timeseries_manager import TimeseriesManager
from python.testing.retriever.mindsphere.config_generator import ConfigGenerator


def get_fixture(configs_path, name_fixture):
    with open(configs_path + name_fixture, "r") as file:
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


@pytest.fixture(scope='class')
def pc_env_prepare():
    prepare(fixtures_path=fixtures_path)
    print("PC environment prepared")


@pytest.fixture(scope='function')
def monitor():
    with Monitor() as mon:
        yield mon


@pytest.fixture(scope='class')
def monitor_boot_ftp_bootstrap():
    mon = call_monitor_boot_ftp_bootstrap()
    yield mon
    mon.disconnect()


def call_monitor_boot_ftp_bootstrap():
    mon = Monitor()
    mon.connect()
    if mon.find_data(trigger="Press enter to boot the selected OS", time_out=20):
        mon.write_data(b"\033[B")
        mon.write_data(b"\r\n")
        print("Boot FTP Bootstrap choice")
    else:
        raise ConnectionError("Monitor don't capture line")
    if mon.find_data(
        trigger=f"using static address {get_ip_ftp_client(fixtures_path + 'DEV/dhcpcd.conf')}/24"
    ):
        print("Boot FTP Bootstrap is ready")
    else:
        raise ConnectionError("Monitor don't capture line")
    return mon


@pytest.fixture(scope='class')
def monitor_boot_kaspersky_os():
    mon = call_monitor_boot_kaspersky_os()
    yield mon
    mon.disconnect()


def call_monitor_boot_kaspersky_os(logging_file="monitor_kos.log"):
    mon = Monitor(logging_file=logging_file)
    mon.connect()
    if mon.find_data(trigger="Boot Kaspersky OS", time_out=20):
        mon.write_data(b"\n")
        print("Boot Kaspersky OS choice")
    else:
        raise ConnectionError("Monitor don't capture line")
    if mon.find_data(trigger="adding route to 192.168.65.0/24"):
        print("Boot Kaspersky OS is ready")
    else:
        raise ConnectionError("Monitor don't capture line")
    return mon


@pytest.fixture(scope='class')
def power_manager():
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
        yield power_manager

    finally:
        power_manager.turn_off()
        print("Power manager was turned off")


@pytest.fixture(scope='class')
def power_manager_reset():
    call_power_manager_reset()


def call_power_manager_reset(manual_switching=False):
    power_manager = PowerManager(fixture_obj=get_fixture(fixtures_path, "network_interface.json"))
    power_manager.set_connection(connecting=True)
    power_manager.reset(manual_switching=manual_switching)
    print("Power manager was reset")


@pytest.fixture(scope='class')
def mindsphere():
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

        timeseries_inst = TimeseriesManager(aspects_inst.variables, asset_id, fixture_obj["systemTestAspectName"])
        yield timeseries_inst

    finally:
        aspects_inst.delete_aspect()
        types_inst.delete_type()
        assets_inst.delete_asset()
        datasource_inst.delete_datasource()
        dm_inst.delete_datamappings()
        print("Created artifacts of MindSphere removed")


@pytest.fixture(scope='class')
def ftp_client():
    client_names = [
        "DEV/dhcpcd.conf",
        "ENW/dhcpcd_dynamic.conf",
        "ENW/hosts",
        "INW/dhcpcd.conf",
        "INW/hosts",
        "IDS/MindSphereAgentSettings-0.json",
        "IDS/MqttPublisherSettings-0.json",
        "IDS/GuideSettings-0.json",
        # "IDS/GuideSettings-1.json",
        "IDS/OpcUaClientSettings-0.json",
        "IDS/valid_der_client.crt",
        "IDS/valid_der_server.crt",
        "IDS/mindsphere.io.crt",
        "IDS/valid_der_client.key",
        "LOG/.log"
    ]
    server_names = [
        "/DEV/etc/dhcpcd.conf",
        "/ENW/etc/dhcpcd.conf",
        "/ENW/etc/hosts",
        "/INW/etc/dhcpcd.conf",
        "/INW/etc/hosts",
        "/IDS/app/Core/config/transfer/mind_sphere/agent/MindSphereAgentSettings-0.json",
        "/IDS/app/Core/config/transfer/mqtt/publisher/MqttPublisherSettings-0.json",
        "/IDS/app/Core/config/transfer/navigation/GuideSettings-0.json",
        # "/IDS/app/Core/config/transfer/navigation/GuideSettings-1.json",
        "/IDS/app/Core/config/transfer/opc_ua/client/OpcUaClientSettings-0.json",
        "/IDS/app/Core/pki/certs/transfer/opc_ua/client/client.crt",
        "/IDS/app/Core/pki/certs/transfer/opc_ua/client/server.crt",
        "/IDS/app/Core/pki/certs/transfer/mind_sphere/agent/mindsphere.io.crt",
        "/IDS/app/Core/pki/private/transfer/opc_ua/client/client.key",
        "/LOG/.log"
    ]
    with FTPClient(
        host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
    ) as ftp_client:
        ftp_client.write_on_server_more(client_names=client_names, server_names=server_names)
    print("FTPClient pass data")


@pytest.fixture(scope='class')
def remove_ftp_logs_upload_ftp_client():
    call_remove_ftp_logs_upload_ftp_client()


def call_remove_ftp_logs_upload_ftp_client():
    path_logs = "/LOG/logs"
    client_names = [
        "DEV/dhcpcd.conf",
        "ENW/dhcpcd_dynamic.conf",
        "ENW/hosts",
        "INW/dhcpcd.conf",
        "INW/hosts",
        "IDS/MindSphereAgentSettings-0.json",
        "IDS/MqttPublisherSettings-0.json",
        "IDS/GuideSettings-0.json",
        "IDS/GuideSettings-1.json",
        "IDS/OpcUaClientSettings-0.json",
        "IDS/valid_der_client.crt",
        "IDS/valid_der_server.crt",
        "IDS/mindsphere.io.crt",
        "IDS/valid_der_client.key",
        "LOG/.log"
    ]
    server_names = [
        "/DEV/etc/dhcpcd.conf",
        "/ENW/etc/dhcpcd.conf",
        "/ENW/etc/hosts",
        "/INW/etc/dhcpcd.conf",
        "/INW/etc/hosts",
        "/IDS/app/Core/config/transfer/mind_sphere/agent/MindSphereAgentSettings-0.json",
        "/IDS/app/Core/config/transfer/mqtt/publisher/MqttPublisherSettings-0.json",
        "/IDS/app/Core/config/transfer/navigation/GuideSettings-0.json",
        "/IDS/app/Core/config/transfer/navigation/GuideSettings-1.json",
        "/IDS/app/Core/config/transfer/opc_ua/client/OpcUaClientSettings-0.json",
        "/IDS/app/Core/pki/certs/transfer/opc_ua/client/client.crt",
        "/IDS/app/Core/pki/certs/transfer/opc_ua/client/server.crt",
        "/IDS/app/Core/pki/certs/transfer/mind_sphere/agent/mindsphere.io.crt",
        "/IDS/app/Core/pki/private/transfer/opc_ua/client/client.key",
        "/LOG/.log"
    ]
    with FTPClient(
        host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
        configs_path=fixtures_path,
        timeout=240
    ) as ftp_client:
        ftp_client.mkd(path_logs)
        list_catalog = ftp_client.list_on_server(path_ls=path_logs)
        if bool(list_catalog):
            for item_path in list_catalog:
                ftp_client.delete_on_server(item_path)
        print("FTPClient all log files have been deleted")
        ftp_client.write_on_server_more(client_names=client_names, server_names=server_names)
    print("FTPClient pass data")


@pytest.fixture(scope='class')
def opcua_server():
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
        yield

    finally:
        opc.stop()
        print("OpcUaServer stop")


@pytest.fixture(scope='class')
def prepare_opcua_connection():
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


@pytest.fixture(scope='class')
def prepare_mqtt_connection():
    up_interface("enx00e04a6a08e8")
    set_globalhost_ip("enx00e04a6a08e8", "192.168.66.52")
    set_ip_config(
        path_file=__file__.split("src/")[0] + "fixtures/" + "IDS/MqttPublisherSettings-0.json",
        key_ip="serverUri",
        prefix_url="tcp://",
        suffix_url=":1883",
        select_filter=".66."
    )
    set_ip_config(
        path_file=__file__.split("src/")[0] + "fixtures/" + "mqtt_settings.json",
        key_ip="serverUri",
        prefix_url="tcp://",
        suffix_url=":1883",
        select_filter=".66."
    )
    print("MQTT configs of client updated")


@pytest.fixture(scope='class')
def sleep_test():
    start_time = datetime.now() - timedelta(hours=3)
    print("Test configured: ", start_time)
    sleep(240)
    end_time = datetime.now() + timedelta(minutes=20)
    print("Test completed: ", end_time)
    yield start_time, end_time


def logging_result(condition, result_file, saved_file):
    if not condition:
        shutil.copyfile(result_file, saved_file)
    return condition


@pytest.fixture(scope='class')
def valid_generate_pair_opcua():
    generate_pair_opcua(fixtures_path=fixtures_path, owner_pair="server", format_pair="DER", mode_pair="valid", output_dir="", output_name="valid_der_server")
    generate_pair_opcua(fixtures_path=fixtures_path, owner_pair="client", format_pair="DER", mode_pair="valid", output_dir="IDS/", output_name="valid_der_client")
    shutil.copyfile(fixtures_path + "valid_der_server.crt", fixtures_path + "IDS/valid_der_server.crt")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call":
        comment_test_class = getattr(item.parent.obj, "__doc__", "")
        comment_test_func = getattr(item.obj, "__doc__", "")
        all_comments_test = "".join(
            ["" if item is None else item for item in [comment_test_class, comment_test_func]]
        )
        map_parsing_id = {
            "plan_id": r"planId=(\d+)",
            "suite_id": r"suiteId=(\d+)",
            "test_case_id": r"_workitems\/edit\/(\d+)"
        }
        for name_id, regex_id in map_parsing_id.items():
            results_search = re.findall(regex_id, all_comments_test)
            map_parsing_id[name_id] = results_search if bool(results_search) else False
        if False in map_parsing_id.values():
            missing_id = ''.join(
                [name_id + ', ' if not result_search else '' for name_id, result_search in map_parsing_id.items()]
            )
            print("[WARNING] Test results are not loaded\n"
                  f"There is no link with {missing_id}in comments to test")
            return
        elif len(map_parsing_id["plan_id"]) != len(map_parsing_id["suite_id"]):
            raise ValueError("Found different number\n"
                             f"of plans ID: {map_parsing_id['plan_id']}\n"
                             f"and suites ID: {map_parsing_id['suite_id']}\n"
                             f"test cases ID: {map_parsing_id['test_case_id']}")
        azure_test_plan = AzureTestPlanRest(fixture_obj=get_fixture(fixtures_path, "azure_devops.json"))
        azure_test = None
        count_uploaded = 0
        for plan_id, suite_id in zip(map_parsing_id["plan_id"], map_parsing_id["suite_id"]):
            print(f"Plan ID: {plan_id}, Suite ID: {suite_id}")
            test_points = azure_test_plan.get_test_points(plan_id, suite_id)
            for test_case_id in map_parsing_id["test_case_id"]:
                test_point_id = azure_test_plan.filter_test_point_id_by_test_case_id(
                    test_points=test_points,
                    test_case_id=test_case_id
                )
                print(f"Case ID: {test_case_id}, Point ID: {test_point_id}")
                if test_point_id is not None:
                    count_uploaded += 1
                    azure_test_plan.upload_test_result(plan_id, suite_id, test_point_id, rep.outcome)
                    print("Test results has been uploaded")
                    if azure_test is None:
                        azure_test = AzureTestRest(fixture_obj=get_fixture(fixtures_path, "azure_devops.json"))
                    test_point_name = azure_test.get_test_point_name(plan_id, suite_id, test_point_id)
                    test_run = azure_test.create_get_test_run(test_point_name)
                    test_run_id = azure_test.get_test_run_id(test_run)
                    azure_test.create_test_run_attachment(test_run_id)
                    print("Test run created and log of TGW attached")
                    test_result = azure_test.add_get_test_result(test_run_id, rep.outcome, test_point_name, rep.duration)
                    test_result_id = azure_test.get_test_result_id(test_result)
                    print(f"Run ID: {test_run_id}, Result ID: {test_result_id}")
                    azure_test.create_test_result_attachment(test_run_id, test_result_id)
                    print("Test result created and log of TGW attached")
                    azure_test.update_test_run_state(test_run_id, rep.outcome)
        if count_uploaded != len(map_parsing_id["test_case_id"]):
            raise ValueError("Number if test case ID found does not match number of test results loaded")
