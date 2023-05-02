#!/usr/bin/env pipenv-shebang
from datetime import datetime, timedelta
import json
import pytest
import subprocess

from conftest import (
    call_power_manager_reset,
    call_monitor_boot_kaspersky_os,
    call_monitor_boot_ftp_bootstrap,
    fixtures_path,
    get_ip_ftp_client,
)
from python.testing.adapter.hardware.monitor.monitor import Monitor
from scripts.hardware.ftp_client import FTPClient


class PrepareTestsDhcp:
    def power_controller(func):
        def wrapper(*args):
            call_power_manager_reset()
            mon = call_monitor_boot_ftp_bootstrap()
            mon.disconnect()
            func(*args)
            call_power_manager_reset()
        return wrapper

    @classmethod
    @power_controller
    def load_static_ip_address(cls):
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            ftp_client.write_on_server(client_name="INW/dhcpcd_base.conf", server_name="/INW/etc/dhcpcd.conf")

    @classmethod
    @power_controller
    def load_dynamic_ip_address(cls):
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            dhcp_configs = ftp_client.list_on_server(path_ls="/INW/etc")
            for dhcp_config in dhcp_configs:
                ftp_client.delete_on_server(name=dhcp_config)
            ftp_client.write_on_server(client_name="INW/dhcpcd_dynamic.conf", server_name="/INW/etc/dhcpcd.conf")


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "remove_ftp_logs_upload_ftp_client"
)
class TestDhcpcdServer:
    @classmethod
    def setup_class(cls):
        cls.subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
        cls.dhcp_server_path = "/home/permi/tmp-tests/tests/scripts/hardware/network/dhcp/server/"
        cls.template_run_command = [
            "sudo",
            "-S",
            "python3",
            cls.dhcp_server_path + "receiver.py",
            "--timeout",
        ]

    @staticmethod
    def _start_first_part_monitor_boot_kaspersky_os():
        mon = Monitor(logging_file="monitor_kos.log")
        mon.connect()
        if mon.find_data(trigger="Boot Kaspersky OS"):
            mon.write_data(b"\n")
            print("Boot Kaspersky OS choice")
        else:
            raise ConnectionError("Monitor don't capture line")
        return mon

    def test_setup_tgw_static_ip_address(self, check_test=True):
        PrepareTestsDhcp.load_static_ip_address()
        if check_test:
            mon = self._start_first_part_monitor_boot_kaspersky_os()
            with open(fixtures_path + "INW/dhcpcd_base.conf", "r") as file:
                for line in file.readlines():
                    if "static ip_address=" in line:
                        check_ip_address = line.split("=")[1].rstrip("\n")
                        break
                else:
                    raise ValueError("Static IP address was not written to test file")
            assert mon.find_data(trigger="using static address " + check_ip_address), \
                "Setup static IP address not found"
        else:
            mon = call_monitor_boot_kaspersky_os()
        mon.disconnect()

    def test_setup_tgw_dynamic_ip_address(self, check_test=True):
        test_timeout = 100
        self.test_setup_tgw_static_ip_address(check_test=False)
        PrepareTestsDhcp.load_dynamic_ip_address()
        subprocess.Popen(
            self.template_run_command + [str(test_timeout)],
            stdin=self.subprocess_superuser.stdout
        )
        if check_test:
            mon = self._start_first_part_monitor_boot_kaspersky_os()
            with open(self.dhcp_server_path + "db/dhcp_receiver_clients.csv", "r") as file:
                for line in file.readlines():
                    if ".65." in line:
                        check_ip_address = line.split(",", maxsplit=1)[0]
                        break
                else:
                    raise ValueError("Server DB does not contain IP address of desired segment")
            with open(self.dhcp_server_path + "config.json", "r") as file:
                dhcp_settings_obj = json.load(file)
            dhcp_server_ip_address = dhcp_settings_obj["DHCPServer"]
            assert mon.find_data(trigger="offered " + check_ip_address + " from " + dhcp_server_ip_address), \
                "Setup dynamic IP address not found"
        else:
            mon = call_monitor_boot_kaspersky_os()
        mon.disconnect()

    @staticmethod
    def _check_saved_server_packets(test_data, test_time_delta):
        collected_packets = timestamps = []
        with open("logs/dhcp_receiver_history.log", "r") as file:
            for line in file.readlines()[1:]:
                timestamp, packet_name = line.split(",")
                collected_packets.append(packet_name.rstrip("\n"))
                timestamp_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                timestamps.append(timestamp_obj)
        assert test_data == collected_packets, \
            "Compiled packages dont match required ones by name"
        assert max(timestamps) - min(timestamps) < timedelta(seconds=test_time_delta), \
            "Time between first packet and last exceeds set limit"

    def test_saved_server_packets_static_ip_address(self):
        test_data = ["DHCPREQUEST", "DHCPACK"]
        test_time_delta = 1
        self.test_setup_tgw_static_ip_address(check_test=False)
        self._check_saved_server_packets(test_data, test_time_delta)

    def test_saved_server_packets_dynamic_ip_address(self):
        test_data = ["DHCPDISCOVER", "DHCPOFFER", "DHCPREQUEST", "DHCPACK"]
        test_time_delta = 2
        self.test_setup_tgw_dynamic_ip_address(check_test=False)
        self._check_saved_server_packets(test_data, test_time_delta)


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "remove_ftp_logs_upload_ftp_client"
)
class TestDhcpcdServerSniffer:
    @classmethod
    def setup_class(cls):
        cls.subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
        cls.dhcp_path = "/home/permi/tmp-tests/tests/scripts/hardware/network/dhcp/"
        cls.template_receiver_run = [
            "sudo",
            "-S",
            "python3",
            cls.dhcp_path + "server/receiver.py"
        ]
        cls.template_sniffer_run = [
            "sudo",
            "-S",
            "python3",
            cls.dhcp_path + "sniffer.py"
        ]

    @staticmethod
    def _check_saved_sniffer_packets(test_data, test_time_delta):
        collected_packets = timestamps = []
        with open("logs/dhcp_sniffer_history.log", "r") as file:
            for line in file.readlines()[1:]:
                timestamp, *packet_name = line.split(",", maxsplit=2)
                collected_packets.append(packet_name[0].rstrip("\n"))
                timestamp_obj = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S.%f")
                timestamps.append(timestamp_obj)
        assert test_data == collected_packets, \
            "Captured packages dont match required ones by name"
        assert max(timestamps) - min(timestamps) < timedelta(seconds=test_time_delta), \
            "Time between first packet and last exceeds set limit"

    def test_sniffer_static_ip_address(self):
        test_data = ["DHCPREQUEST", "DHCPACK"]
        test_timeout = 100
        test_time_delta = 1
        PrepareTestsDhcp.load_static_ip_address()
        mon = call_monitor_boot_kaspersky_os()
        subprocess.Popen(
            self.template_sniffer_run + [str(test_timeout)],
            stdin=self.subprocess_superuser.stdout
        )
        mon.disconnect()
        self._check_saved_sniffer_packets(test_data, test_time_delta)

    def test_sniffer_dynamic_ip_address(self):
        test_data = ["DHCPDISCOVER", "DHCPOFFER", "DHCPREQUEST", "DHCPACK"]
        test_timeout = 100
        test_time_delta = 2
        PrepareTestsDhcp.load_dynamic_ip_address()
        mon = call_monitor_boot_kaspersky_os()
        subprocess.Popen(
            self.template_receiver_run + [
                "--timeout",
                str(test_timeout)
            ],
            stdin=self.subprocess_superuser.stdout
        )
        subprocess.Popen(
            self.template_sniffer_run + [
                "--timeout",
                str(test_timeout)
            ],
            stdin=self.subprocess_superuser.stdout
        )
        mon.disconnect()
        self._check_saved_sniffer_packets(test_data, test_time_delta)
