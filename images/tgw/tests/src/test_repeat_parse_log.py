#!/usr/bin/env pipenv-shebang
import pytest
from random import randint
import shutil

from conftest import (
    fixtures_path,
    get_fixture,
    call_power_manager_reset,
    call_monitor_boot_kaspersky_os
)
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "prepare_opcua_connection",
    "valid_generate_pair_opcua",
    "remove_ftp_logs_upload_ftp_client"
)
class TestRepeatLoadWork:
    @classmethod
    def setup_class(cls):
        cls.check_line = "Unhandled Page Fault, address"

    def _calc_time_split(_general_time):
        time_split = []
        day_divisor = 24
        while _general_time > 100 and day_divisor:
            random_time = randint(0, int(_general_time / day_divisor))
            day_divisor -= 1
            _general_time -= random_time
            time_split.append(random_time)
        return time_split

    _general_time = 86400
    _time_split = _calc_time_split(_general_time)
    test_data = [(number_test, test_time_load, ) for number_test, test_time_load in enumerate(_time_split)]

    @staticmethod
    def payload_opcua():
        opc = OpcUaServer(
            name_source_dir=fixtures_path,
            data_points_obj=get_fixture(fixtures_path, "data_points.json"),
            opc_settings_obj=get_fixture(fixtures_path, "opc_ua_settings.json"),
            logging_mode="INFO",
            gen_infinity=True
        )
        opc.start()
        return opc

    @pytest.mark.parametrize("number_test,test_time_load", test_data)
    def test_repeat_load_work(self, number_test, test_time_load):
        error_log = ""
        call_power_manager_reset()
        mon = call_monitor_boot_kaspersky_os()
        opc = self.payload_opcua()
        if mon.find_data(trigger=self.check_line, time_out=test_time_load):
            error_log = f"tmp_logs/result_test_repeat_load_work-{str(number_test)}.log"
            opc.stop()
            mon.disconnect()
            shutil.copyfile("logs/monitor_kos.log", error_log)
        else:
            opc.stop()
            mon.disconnect()
        assert not error_log, f"Error SDK was found when running, see files: {error_log}"
