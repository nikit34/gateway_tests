#!/usr/bin/env pipenv-shebang
from datetime import datetime, timedelta
import pytest
import re
from time import sleep

from conftest import (
    logging_result,
    get_fixture,
    fixtures_path
)
from python.testing.adapter.hardware.comparator.parsers import ParserMonitor
from python.testing.datasource.opcua.opc_ua_proc_server import OpcUaServer


@pytest.mark.usefixtures(
    "pc_env_prepare",
    "power_manager",
    "monitor_boot_ftp_bootstrap",
    "valid_generate_pair_opcua",
    "prepare_opcua_connection",
    "remove_ftp_logs_upload_ftp_client",
    "power_manager_reset",
    "monitor_boot_kaspersky_os"
)
class TestMonitorPassData:
    @classmethod
    def setup_class(cls):
        cls.data_points_obj = get_fixture(fixtures_path, "data_points.json")
        cls.opc_settings_obj = get_fixture(fixtures_path, "opc_ua_settings.json")
        cls.logging_mode = "INFO"
        cls.gen_infinity = True

    test_data_contains_lines = [
        [
            [
                "Debug: PUT",
                "target",
                "name",
                "MQTT Publisher Manager",
                "hubId",
                "portId",
                "dataItem",
                "timestamp",
                "timestampSource",
                "value",
                "status"
            ],
            "mqtt"
        ], [
            [
                "Debug: GET",
                "source",
                "name",
                "OPC UA Client Manager",
                "hubId",
                "portId",
                "dataItem",
                "timestamp",
                "timestampSource",
                "value",
                "status"
            ],
            "opcua"
        ]
    ]

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
            sleep(20)
        finally:
            opc.stop()

    @staticmethod
    def diff_parts_line(found_parts_line, check_parts_line):
        return len(found_parts_line) == len(check_parts_line), \
               "Not all tuning parts of line were found in line of output: " + \
               str(set(found_parts_line) - set(check_parts_line))

    @pytest.mark.parametrize("parts_lines,tag_log", test_data_contains_lines)
    def test_contains_lines_output_content_data_item(self, parts_lines, tag_log):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16980
        """
        self.payload_opcua()
        found_parts = []
        parts_largest_occurrence = []
        max_occurrence = 0
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for part_check_line in parts_lines:
                    if part_check_line in line and part_check_line not in found_parts:
                        found_parts.append(part_check_line)
                        if len(found_parts) > max_occurrence:
                            if all(
                                part_largest_occurrence in line for part_largest_occurrence in parts_largest_occurrence
                            ):
                                if part_check_line not in parts_largest_occurrence:
                                    parts_largest_occurrence.append(part_check_line)
                                    max_occurrence += 1
                            else:
                                parts_largest_occurrence = found_parts
                        elif len(parts_lines) == max_occurrence:
                            break
                    else:
                        found_parts = []
                else:
                    continue
                break
        status, msg = self.diff_parts_line(parts_largest_occurrence, parts_lines)
        assert logging_result(
            status,
            "logs/monitor_kos.log",
            f"tmp_logs/test_contains_lines_output_{tag_log}_content_data_item.log"
        ), msg

    @pytest.mark.parametrize("parts_lines,tag_log", test_data_contains_lines)
    def test_contains_lines_output_timeout(self, parts_lines, tag_log):
        """
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/16987
        """
        self.payload_opcua()
        parts_check_lines = parts_lines
        parts_check_lines.append("Int")
        found_parts = []
        parts_largest_occurrence = []
        max_occurrence = 0
        max_count_calc_occurrence = 3
        allowed_timedelta = timedelta(seconds=2, milliseconds=500)
        parsed_timeout_parts_lines = []
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                for part_check_line in parts_lines:
                    if part_check_line in line and part_check_line not in found_parts:
                        found_parts.append(part_check_line)
                        if len(parts_check_lines) == max_occurrence:
                            if max_count_calc_occurrence > 0:
                                max_count_calc_occurrence -= 1
                                parsed_timeout_parts_lines.append(line.split(" ", maxsplit=2)[1])
                            else:
                                break
                        elif all(
                            part_largest_occurrence in line for part_largest_occurrence in parts_largest_occurrence
                        ):
                            if part_check_line not in parts_largest_occurrence:
                                parts_largest_occurrence.append(part_check_line)
                                max_occurrence += 1
                        else:
                            parts_largest_occurrence = found_parts
                    else:
                        found_parts = []
                else:
                    continue
                break
        assert logging_result(
            parsed_timeout_parts_lines,
            "logs/monitor_kos.log",
            f"tmp_logs/test_contains_lines_output_{tag_log}_timeout.log"
        ), "times were not parsed"
        for i in range(len(parsed_timeout_parts_lines) - 1):
            time_delta = datetime.strptime(
                parsed_timeout_parts_lines[i], "%H:%M:%S,%f"
            ) - datetime.strptime(
                parsed_timeout_parts_lines[i + 1], "%H:%M:%S,%f"
            )
            assert logging_result(
                time_delta < allowed_timedelta,
                "logs/monitor_kos.log",
                f"tmp_logs/test_contains_lines_output_{tag_log}_timeout.log"
            ), "Time interval between dataItems is more than allowed"


class TestMonitorValueData(TestMonitorPassData):
    parser_monitor = ParserMonitor(regex_monitor=get_fixture(fixtures_path, "regex_monitor.json"))

    def test_values_match_output(self):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/18760
        '''
        self.payload_opcua()
        source_debug_field = "GET"
        target_debug_field = "PUT"
        source_name = "OPC UA Client Manager"
        target_name = "MQTT Publisher Manager"
        check_values_match = (
            "timestamp",
            "value",
            "status"
        )
        source_map = {}
        target_map = {}
        with open("logs/monitor_kos.log") as file:
            for line in file.readlines():
                if all([check_value_match in line for check_value_match in check_values_match]):
                    if source_name in line and source_debug_field in line:
                        source_value = self.parser_monitor.parse_monitor_value(line)
                        source_timestamp = self.parser_monitor.parse_monitor_timestamp(line)
                        source_status = self.parser_monitor.parse_monitor_status(line)
                        source_port_id = self.parser_monitor.parse_monitor_port_id(line)
                        source_map[source_port_id] = {
                            source_value,
                            source_timestamp,
                            source_status
                        }
                    elif target_name in line and target_debug_field in line:
                        target_value = self.parser_monitor.parse_monitor_value(line)
                        target_timestamp = self.parser_monitor.parse_monitor_timestamp(line)
                        target_status = self.parser_monitor.parse_monitor_status(line)
                        target_port_id = self.parser_monitor.parse_monitor_port_id(line)
                        target_map[target_port_id] = {
                            target_value,
                            target_timestamp,
                            target_status
                        }
                if set(source_map.keys()) == set(target_map.keys()) and bool(source_map):
                    assert logging_result(
                        source_map == target_map,
                        "logs/monitor_kos.log",
                        f"tmp_logs/test_values_match_output.log"
                    ), "Mismatched values found: " \
                        "Source: " + str(set(source_map.values()) - set(target_map.values())) + \
                        "Target: " + str(set(target_map.values()) - set(source_map.values()))
                    source_map = {}
                    target_map = {}
