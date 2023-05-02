#!/usr/bin/env pipenv-shebang
from datetime import datetime, timedelta
import os
import re
from time import sleep

import pytest

from conftest import (
    fixtures_path,
    call_power_manager_reset,
    call_monitor_boot_ftp_bootstrap,
    call_monitor_boot_kaspersky_os
)
from python.testing.adapter.hardware.network.wired_identifier import get_ip_ftp_client
from scripts.hardware.ftp_client import FTPClient
from scripts.hardware.multithread_ftp_client import FTPClientMultiThreaded


def call_double_bootstrap():
    call_power_manager_reset()
    mon = call_monitor_boot_kaspersky_os()
    mon.disconnect()
    call_power_manager_reset()
    mon = call_monitor_boot_ftp_bootstrap()
    mon.disconnect()


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client"
)
class TestReadLog:
    @classmethod
    def setup_class(cls):
        cls.template_hours = "log-" + (datetime.now() - timedelta(hours=3)).strftime("%Y%m%dT%H")
        cls.tmp_dir = "tmp_logs/"

    def check_contains_name_log_files(self, server_name):
        item_name = server_name.rsplit("/", 1)[1]
        if "log-" in item_name:
            actual_name_hours = item_name[:item_name.index("T") + 3]
            if self.template_hours == actual_name_hours:
                return True
        return False

    def test_created_named_log(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14816
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/9507
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14867
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10395
        '''
        call_double_bootstrap()
        pass_test = False
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            list_catalog = ftp_client.list_on_server(path_ls="/LOG/logs")
        assert len(list_catalog) == 1, "Number of files in log partition not as expected"
        for item_path in list_catalog:
            if "/LOG/logs/log-" in item_path:
                server_name = item_path.rsplit("/", 1)[1]
                actual_name_hours = server_name[:server_name.index("T") + 3]
                if self.template_hours == actual_name_hours:
                    pass_test = True
        assert pass_test, "File with required name was not found"

    def test_content_log(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14815
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/9509
        '''
        call_double_bootstrap()
        pass_test = True
        bootstrap_name_log = self.tmp_dir + "tgw-kos-bootstrap.log"
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            log_file_exist = False
            list_catalog = ftp_client.list_on_server(path_ls="/LOG/logs")
            for server_name in list_catalog:
                if self.check_contains_name_log_files(server_name):
                    log_file_exist = True
                    ftp_client.read_on_server(server_name=server_name, client_name=bootstrap_name_log)
            if not log_file_exist:
                raise ValueError("[ERROR] Log file not found")
        with open(bootstrap_name_log, "r") as bootstrap_file,\
            open("logs/monitor_kos.log", "r") as monitor_file:
            monitor_lines = monitor_file.readlines()
            for bootstrap_line in bootstrap_file.readlines():
                bootstrap_line = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', bootstrap_line)
                bootstrap_line = bootstrap_line.rstrip()
                coincidence_line = False
                for monitor_line in monitor_lines:
                    if bootstrap_line in monitor_line or "\00\00\00\00\00" in bootstrap_line:
                        coincidence_line = True
                        break
                if not coincidence_line:
                    pass_test = False
                    break
        assert pass_test, "Log files do not match: " + bootstrap_line

    @classmethod
    def teardown_class(cls):
        for tmp_file in os.listdir(cls.tmp_dir):
            os.remove(cls.tmp_dir + tmp_file)


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client"
)
class TestDisabledLog:
    def test_disabled_log(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14817
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/9508
        '''
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            ftp_client.delete_on_server(name="/LOG/.log")
        call_double_bootstrap()
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            list_catalog = ftp_client.list_on_server(path_ls="LOG/logs")
        assert not list_catalog, "Log files exist when logging is disabled"


def save_log_files_get_count():
    template_name_log = "tmp_logs/log-"
    with FTPClient(
        host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
    ) as ftp_client:
        list_catalog = ftp_client.list_on_server(path_ls="LOG/logs")
        count_logs = len(list_catalog)
        index_name_log = 0
        for server_name in list_catalog:
            if "/LOG/logs/log-" in server_name:
                ftp_client.read_on_server(
                    server_name=server_name,
                    client_name=template_name_log + str(index_name_log) + ".txt"
                )
                index_name_log += 1
    return count_logs


def snip_run_tgw_setting_logs(name_config_log):
    with FTPClient(
        host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
    ) as ftp_client:
        ftp_client.write_on_server(client_name=name_config_log, server_name="/LOG/.log")
    call_power_manager_reset()
    mon = call_monitor_boot_kaspersky_os()
    sleep(3)
    mon.disconnect()
    call_power_manager_reset()
    mon = call_monitor_boot_ftp_bootstrap()
    mon.disconnect()


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client"
)
class TestRotationLogs:
    '''
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14866
    '''

    @staticmethod
    def get_content_log(monitor_file):
        monitor_lines = []
        for monitor_line in monitor_file.readlines():
            split_monitor_line = monitor_line.split(" ", maxsplit=2)
            prepare_monitor_line = split_monitor_line[2] if len(split_monitor_line) == 3 else "\n"
            monitor_lines.append(prepare_monitor_line)
        return monitor_lines

    @staticmethod
    def get_content_start_position_log(monitor_lines):
        monitor_lines_cut = []
        for i, monitor_line in enumerate(monitor_lines):
            if "Loading:" in monitor_line:
                monitor_lines_cut = monitor_lines[i:]
                monitor_lines_cut.insert(0, "\n")
        return monitor_lines_cut

    def test_rotation_logs(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10397
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10398
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10399
        '''
        snip_run_tgw_setting_logs(name_config_log="LOG/.log__little")
        count_logs = save_log_files_get_count()
        missing_line = None
        need_open_log = True
        log_lines = []
        number_log_file = 0
        with open("logs/monitor_kos.log", "r") as monitor_file:
            monitor_file_lines = self.get_content_log(monitor_file)
            monitor_lines = self.get_content_start_position_log(monitor_file_lines)
            for monitor_line in monitor_lines:
                if number_log_file == count_logs - 1:
                    break
                if need_open_log:
                    log_file = open("tmp_logs/log-" + str(number_log_file) + ".txt", "r")
                    log_lines = log_file.readlines()
                    count_log_lines = len(log_lines)
                    current_number_log_line = 0
                    need_open_log = False
                if log_lines[current_number_log_line] not in monitor_line:
                    missing_line = log_lines[current_number_log_line]
                current_number_log_line += 1
                if count_log_lines == current_number_log_line:
                    need_open_log = True
                    number_log_file += 1
        assert missing_line is None, f"File rotation is not working properly, missing line: {missing_line}"


def get_value_config_field(name_config_log, template_config_field):
    with open(fixtures_path + name_config_log, "r") as file:
        for line in file.readlines():
            if template_config_field in line:
                return int(line.split(template_config_field, maxsplit=1)[1].rstrip())
    raise ValueError("Size log limit not found")


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client"
)
class TestSizesLogs:
    '''
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14866
    '''

    @classmethod
    def setup_class(cls):
        cls.name_config_little_log = "LOG/.log__little"
        cls.name_config_minimal_log = "LOG/.log__minimal"
        cls.tmp_dir = "tmp_logs/"

    def test_count_log_files(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10396
        '''
        snip_run_tgw_setting_logs(name_config_log=self.name_config_little_log)
        count_logs = save_log_files_get_count()
        size_log_limit = get_value_config_field(self.name_config_little_log, template_config_field="LogFileSizeLimit=")
        size_log_directory = get_value_config_field(
            self.name_config_little_log, template_config_field="DirectorySizeLimit="
        )
        if size_log_limit >= 100:
            assert int(size_log_directory / size_log_limit) > count_logs > 0, \
                "Number generated log files is less than expected"

    def test_size_log_line(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10400
        '''
        test_line = "Log line is too long and exceed the file size limit"
        count_occurrence = 0
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            ftp_client.write_on_server(client_name=self.name_config_minimal_log, server_name="/LOG/.log")
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        sleep(3)
        mon.disconnect()
        with open("logs/monitor_kos.log", "r") as file:
            for line in file.readlines():
                if test_line in line:
                    count_occurrence += 1
        assert count_occurrence == 1, "Invalid output of error about limit on length of line in log"

    def test_size_log_file(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10396
        '''
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        snip_run_tgw_setting_logs(name_config_log=self.name_config_little_log)
        count_logs = save_log_files_get_count()
        size_log_limit = get_value_config_field(self.name_config_little_log, template_config_field="LogFileSizeLimit=")
        for i in range(count_logs):
            size_log = os.path.getsize("tmp_logs/log-" + str(i) + ".txt")
            assert size_log <= size_log_limit, "Log file size exceeds limit set in configuration settings"

    def test_size_log_folder(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10399
        '''
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        snip_run_tgw_setting_logs(name_config_log=self.name_config_little_log)
        count_logs = save_log_files_get_count()
        size_log_directory = get_value_config_field(
            self.name_config_little_log, template_config_field="DirectorySizeLimit="
        )
        sum_sizes_logs = 0
        for i in range(count_logs):
            sum_sizes_logs += os.path.getsize("tmp_logs/log-" + str(i) + ".txt")
        assert sum_sizes_logs <= size_log_directory, "Directory size exceeds limit set in configuration settings"

    @classmethod
    def teardown_class(cls):
        for tmp_file in os.listdir(cls.tmp_dir):
            os.remove(cls.tmp_dir + tmp_file)


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client"
)
class TestWarningCreateFileNameExist:
    '''
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14868
    '''

    @classmethod
    def setup_class(cls):
        cls.tmp_dir = "tmp_logs/"

    @staticmethod
    def generate_series_files_closest_names(count):
        part_name_time = datetime.now() - timedelta(hours=3)
        for _ in range(count):
            part_name_time = part_name_time + timedelta(milliseconds=10)
            template_name = "tmp_logs/log-" + part_name_time.strftime("%Y%m%dT%H%M%S%f")[:-6] + "Z.txt"
            open(template_name, "w").close()

    @staticmethod
    def make_path_names(prefix_path, names):
        return list(
            map(lambda name: prefix_path + name, names)
        )

    def prepare_warning_create_file(self, count=6000):
        self.generate_series_files_closest_names(count=count)
        client_names_file = [f for f in os.listdir(self.tmp_dir)]
        client_names = self.make_path_names(self.tmp_dir, client_names_file)
        server_names = self.make_path_names("/LOG/logs/", client_names_file)
        with FTPClientMultiThreaded(
            count_threads=20,
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"),
            configs_path=__file__.split("src/")[0] + "src/",
            timeout=count * 2 / 3
        ) as ftp_client:
            ftp_client.write_on_server_more(client_names=client_names, server_names=server_names)
        print("FTPClient pass data")
        call_double_bootstrap()
        return server_names

    @staticmethod
    def clear_log_partition_after_generate(server_names):
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            for server_name in server_names:
                ftp_client.delete_on_server(server_name)

    def test_warning_create_file_lack_output(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10414
        '''
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        server_names = self.prepare_warning_create_file()
        try:
            with open("logs/monitor_kos.log", "r") as file:
                for line in file.readlines():
                    assert not ("has been opened" in line), "Log file has been created"
        finally:
            self.clear_log_partition_after_generate(server_names)

    def test_warning_create_file_name_matching(self):
        '''
        manual
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/10414
        '''
        call_power_manager_reset()
        mon = call_monitor_boot_ftp_bootstrap()
        mon.disconnect()
        server_names = self.prepare_warning_create_file(count=10)
        with FTPClient(
            host=get_ip_ftp_client(fixtures_path + "DEV/dhcpcd.conf"), configs_path=fixtures_path
        ) as ftp_client:
            list_catalog = ftp_client.list_on_server(path_ls="/LOG/logs")
        generated_logs = os.listdir(self.tmp_dir)
        try:
            assert len(list_catalog) == len(generated_logs), "Number of generated files does not match current one"
            for server_log, generated_name_log in zip(list_catalog, generated_logs):
                server_name_log = server_log.rsplit("/", maxsplit=1)[1]
                assert server_name_log == generated_name_log, "Name of generated file does not match saved one"
        finally:
            self.clear_log_partition_after_generate(server_names)

    @classmethod
    def teardown_class(cls):
        for tmp_file in os.listdir(cls.tmp_dir):
            os.remove(cls.tmp_dir + tmp_file)
