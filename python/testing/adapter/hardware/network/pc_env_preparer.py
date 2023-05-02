import json
import os


def _check_necessary(components, **kwargs):
    if (
        components.get("ip_dhcpcd_inw", False) or components.get("interface_mikrotik", False)
    ) and "fixtures_path" not in kwargs.keys():
        raise AttributeError("Prepare internal network, need know path to fixtures")


def _get_settings(config_prepare, components):
    prepare_settings = {}
    with open(os.path.expanduser('~') + "/" + config_prepare, "r+") as file:
        config_settings = json.load(file)
    diff = set(config_settings.keys()) ^ set(components.keys())
    if bool(diff):
        print("Expected components and configuration files dont match: ", diff)
    for component, expected in components.items():
        if expected:
            prepare_settings[component] = config_settings[component]
    return prepare_settings


def _prepare_dhcpcd_inw(ip_dhcpcd_inw, fixtures_path):
    edit_line = None
    with open(fixtures_path + "INW/dhcpcd.conf", "r") as file:
        write_lines = file.readlines()
    for i, line in enumerate(write_lines):
        if "static ip_address=" in line:
            edit_line = i
            break
    if edit_line is None:
        raise ValueError("Static address settings are not registered")
    write_lines[edit_line] = "static ip_address=" + ip_dhcpcd_inw
    with open(fixtures_path + "INW/dhcpcd.conf", "w") as file:
        file.writelines(write_lines)


def _prepare_mikrotik(interface_mikrotik, fixtures_path):
    with open(fixtures_path + "network_interface.json", "r+") as file:
        data = json.load(file)
        data["interface"] = interface_mikrotik
        file.seek(0)
        json.dump(data, file, indent=4)
        file.truncate()


def prepare(config_prepare="pc_test_config.json", components=None, **kwargs):
    if components is None:
        components = {
            "ip_dhcpcd_inw": True,
            "interface_mikrotik": True,
        }
    _check_necessary(components, **kwargs)
    prepare_settings = _get_settings(config_prepare, components)

    if components.get("ip_dhcpcd_inw", False):
        _prepare_dhcpcd_inw(prepare_settings["ip_dhcpcd_inw"], **kwargs)
    if components.get("interface_mikrotik", False):
        _prepare_mikrotik(prepare_settings["interface_mikrotik"], **kwargs)
