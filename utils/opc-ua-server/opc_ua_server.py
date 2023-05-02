#!/usr/bin/env pipenv-shebang
import json

from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer


def get_fixture(pathname_fixture):
    with open(pathname_fixture, "r") as file:
        return json.load(file)


opc = OpcUaServer(
    name_source_dir="config/",
    data_points_obj=get_fixture("config/data_points.json"),
    opc_settings_obj=get_fixture("config/opc_ua_settings.json")
)

try:
    opc.start()
    print("OPC UA Server is running")
    input("Press key for terminate")
finally:
    opc.stop()
