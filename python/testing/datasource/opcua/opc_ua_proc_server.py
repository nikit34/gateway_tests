from datetime import datetime, timedelta
import logging
from multiprocessing import Process
import subprocess
from time import sleep
from opcua import ua, Server
from opcua.common.callback import CallbackType

from .opc_ua_dataclasses import MapTypes, NamesPolitics, LogMode
from .generator_data_points import GeneratorDataPoints


class OpcUaServer(Server):
    def __init__(self, name_source_dir, opc_settings_obj,
                 data_points_obj=None, gen_count_types=None,
                 gen_infinity=False, sleep_interval_global=0,
                 logging_mode=False, logging_general=False,
                 security_pair_name="valid_der_server"
                 ):
        super().__init__()
        self.name_source_dir = name_source_dir
        self.data_points_obj = data_points_obj
        self.opc_settings_obj = opc_settings_obj
        if gen_count_types is None:
            self.gen_count_types = {"Boolean": 1, "Int": 1, "Long": 1, "Double": 1, "String": 1}
        else:
            self.gen_count_types = gen_count_types
        self.gen_infinity = gen_infinity
        self.logging_mode = LogMode(logging_mode)
        self.logging_general = logging_general
        self.map_types = MapTypes()
        self.node_id_settings = []
        self.sleep_interval_global = sleep_interval_global
        self.security_pair_name = security_pair_name

    def set_endpoint(self, url):
        port = int(url.split(":")[2])
        setattr(self, "port", port)
        super().set_endpoint(url)

    @staticmethod
    def _check_nosecurity_combination(necessary_security_mode, necessary_security_policy):
        pair_necessary_security = (necessary_security_mode, necessary_security_policy)
        return True if pair_necessary_security in (
            (None, None), ('None', 'None'), ('None', 'Any'), ('Any', 'None')
        ) else False

    @staticmethod
    def _check_allowed_security_combination(necessary_security_mode, necessary_security_policy):
        assert necessary_security_mode is not None and \
               necessary_security_policy is not None and \
               necessary_security_mode != "None" and \
               necessary_security_policy != "None", \
               "Unacceptable combination of policies and mode"

    @staticmethod
    def _select_security_politics(names_politics, necessary_security_mode, necessary_security_policy):
        selected_security_politics = []
        for name, item in names_politics.iter():
            if necessary_security_mode == "Any" and necessary_security_policy == "Any":
                selected_security_politics.append(item)
            elif "_" in name:
                parts_name = name.split("_")
                if necessary_security_policy in (parts_name[0], 'Any') and \
                        necessary_security_mode in (parts_name[1], "Any"):
                    selected_security_politics.append(item)
        return selected_security_politics

    def set_security_policy(self, security_policy):
        names_politics = NamesPolitics()
        if security_policy is None:
            selected_security_politics = [names_politics.none]
        else:
            necessary_security_mode = security_policy.get("mode", None)
            necessary_security_policy = security_policy.get("policy", None)
            if self._check_nosecurity_combination(necessary_security_mode, necessary_security_policy):
                selected_security_politics = [names_politics.none]
            else:
                self._check_allowed_security_combination(necessary_security_mode, necessary_security_policy)
                selected_security_politics = self._select_security_politics(
                    names_politics, necessary_security_mode, necessary_security_policy)
        super().set_security_policy(selected_security_politics)

    def set_nodes_id(self, nodes):
        nodes_id = [None] * len(nodes)
        for i, node in enumerate(nodes):
            nodes_id[i] = node["nodeId"]
        setattr(self, "nodes_id", nodes_id)

    def set_folder(self, idx):
        objects = self.get_objects_node()
        setattr(self, "folder", objects.add_folder(idx, "Folder"))

    def remember_node_id_nodes(self, nodes):
        for node in nodes:
            s_node_id = node["nodeId"].split(";s=")[1]
            assert any(item in s_node_id for item in ["Boolean", "Int", "Long", "Double", "String"]), \
                "'nodeId' is not valid"
            self.node_id_settings.append(s_node_id)

    def apply_opc_settings_config(self):
        if self.logging_mode.mode:
            self.logging_mode.general.debug("start apply_opc_settings_config")
        self.set_endpoint(self.opc_settings_obj.get("url", "opc.tcp://0.0.0.0:4840"))
        self.load_certificate(self.name_source_dir + self.security_pair_name + ".crt")
        self.load_private_key(self.name_source_dir + self.security_pair_name + ".key")
        self.set_security_policy(self.opc_settings_obj.get("security", None))
        self.set_security_IDs(self.opc_settings_obj.get("userTokenPolicy", ["Anonymous", "Username"]))
        idx = self.register_namespace(self.opc_settings_obj.get("uri", ""))
        self.set_nodes_id(self.opc_settings_obj.get("nodes", []))
        self.set_folder(idx)
        self.remember_node_id_nodes(self.opc_settings_obj.get("nodes", []))
        if self.logging_mode.mode:
            self.logging_mode.general.debug("end apply_opc_settings_config")

    @staticmethod
    def cycle(iterable):
        saved = []
        for element in iterable:
            yield element
            saved.append(element)
        while saved:
            for element in saved:
                yield element

    def set_timestamps(self, timestamps, count_data_items):
        if callable(timestamps):
            timestamps = timestamps(count_data_items=count_data_items)
        timestamps = list(map(lambda t: datetime.strptime(t, "%Y-%m-%dT%H:%M:%S.%fZ"), timestamps))
        return self.cycle(timestamps)

    def set_values(self, typecast, values, data_type, count_data_items):
        if hasattr(values, '__self__'):
            values = values(data_type, count_data_items=count_data_items)
        values = list(map(lambda v: typecast(v), values))
        return self.cycle(values)

    def set_statuses(self, statuses, count_data_items):
        if callable(statuses):
            statuses = statuses(count_data_items=count_data_items)
        return self.cycle(statuses)

    def set_variable(self, data_name, id_, data_type):
        return self.folder.add_variable(
            self.nodes_id[id_],
            data_name,
            self.map_types[data_type].default,
            self.map_types[data_type].type
        )

    def apply_data_points_config(self):
        if self.logging_mode.mode:
            self.logging_mode.general.debug("start apply_data_points_config")
        if self.data_points_obj is None:
            self.data_points_obj = GeneratorDataPoints.gen_data_points(custom_count_types=self.gen_count_types)
        else:
            self.sleep_interval_global = self.data_points_obj.get("commonInterval", self.sleep_interval_global)
        data_points = []
        for id_, data_point in enumerate(self.data_points_obj["dataPoints"]):
            data_type = data_point["dataType"]
            timestamp_source = data_point.get("timestampSource", None)
            assert any(data_type in item for item in self.node_id_settings), "`node_id` after ';s=' does not match with data_type"
            data_items = data_point["dataItems"]
            set_items = []
            for data_item in data_items:
                set_items.append((
                    data_item.get("timestamp", None),
                    data_item.get("value", None),
                    data_item.get("status", None)
                ))
            timestamps, values, statuses = list(zip(*set_items))
            count_data_items = len(data_items)
            if data_type in self.map_types:
                if None in timestamps:
                    timestamps = GeneratorDataPoints.gen_timestamps
                timestamps = self.set_timestamps(timestamps, count_data_items)
                if None in values:
                    values = GeneratorDataPoints.gen_values
                values = self.set_values(self.map_types[data_type].typecast, values, data_type, count_data_items)
                if None in statuses:
                    statuses = GeneratorDataPoints.gen_statuses
                statuses = self.set_statuses(statuses, count_data_items)
            sleep_interval_local = data_point.get("sleepInterval", None)
            variable = self.set_variable(data_point["dataName"], id_, data_type)
            data_points.append([
                data_type,
                timestamp_source,
                timestamps,
                values,
                statuses,
                count_data_items,
                sleep_interval_local,
                variable
            ])
            if self.logging_general:
                name = "all_variables"
                log_file = "all_variables.log"
                log_line = "call: set_variable; timestamp_source: " + str(timestamp_source) + \
                           "; sleep_interval_local: " + str(sleep_interval_local) + "; name: " + str(data_type)
            else:
                name = data_type
                log_file = data_type + ".log"
                log_line = "call: set_variable; timestamp_source: " + str(timestamp_source) + \
                           "; sleep_interval_local: " + str(sleep_interval_local)
            log_item = self.setup_logging(name, log_file)
            if log_item:
                log_item.info(log_line)
        if self.logging_mode.mode:
            self.logging_mode.general.debug("end apply_data_points_config")
        return data_points

    @staticmethod
    def set_mode_timestamp(value, timestamp, timestamp_source):
        if timestamp_source == "source" or timestamp_source is None:
            value.SourceTimestamp = timestamp
        elif timestamp_source == "server":
            value.ServerTimestamp = timestamp
        elif timestamp_source != "client":
            raise ValueError("Value `timestamp_source` must `server` or `source`")
        return value

    def create_monitored_items(self, event, dispatcher):
        for idx in range(len(event.response_params)):
            if event.response_params[idx].StatusCode.is_good():
                node_id = event.request_params.ItemsToCreate[idx].ItemToMonitor.NodeId
                part_node_id = str(node_id).split(";s=")[1]
                data_name = part_node_id.split(")")[0]
                if self.logging_general:
                    data_type = "all_variables"
                    log_file = "all_variables.log"
                else:
                    for item in ["Boolean", "Int", "Long", "Double", "String"]:
                        if item in data_name:
                            data_type = item
                            break
                    else:
                        raise TypeError("Event params don't have valid type of dataItem")
                    log_file = data_type + ".log"
                log_line = "call: create_monitored_items; created: " + data_name
                log_item = self.setup_logging(data_type, log_file)
                if log_item:
                    log_item.info(log_line)

    def create_pool_setup_values(self, data_points):
        if self.logging_mode.mode:
            self.logging_mode.general.debug("start create_pool_setup_values")
        super().start()
        count_data_points = len(data_points)
        local_seconds_multiplier = 0
        while True:
            if self.sleep_interval_global:
                sleep(self.sleep_interval_global)
            i = 0
            while count_data_points > i:
                data_type, timestamp_source, timestamps, \
                values, statuses, count_data_items, \
                sleep_interval_local, variable = data_points[i]
                value = next(values)
                status = next(statuses)
                value_item = ua.DataValue(ua.Variant(value, self.map_types[data_type].type))
                timestamp = next(timestamps)
                if sleep_interval_local is not None:
                    timestamp = timestamp + timedelta(0, local_seconds_multiplier * sleep_interval_local)
                value_item = self.set_mode_timestamp(value_item, timestamp, timestamp_source)
                value_item.StatusCode = ua.StatusCode(status)
                variable.set_value(value_item)
                if self.logging_general:
                    name = "all_variables"
                    log_file = "all_variables.log"
                    log_line = "call: set_value; timestamp: " + str(timestamp) + "; value: " + str(value) + \
                               "; status: " + str(status) + "; name: " + str(data_type)
                else:
                    name = data_type
                    log_file = data_type + ".log"
                    log_line = "call: set_value; timestamp: " + str(timestamp) + "; value: " + str(value) + \
                               "; status: " + str(status)
                log_item = self.setup_logging(name, log_file)
                if log_item:
                    log_item.info(log_line)
                i += 1
            if self.gen_infinity:
                while 0 < i:
                    i -= 1
                    data_type = data_points[i][0]
                    data_points[i][2] = self.set_timestamps(GeneratorDataPoints.gen_timestamps, count_data_items)
                    data_points[i][3] = self.set_values(
                        self.map_types[data_type].typecast,
                        GeneratorDataPoints.gen_values,
                        data_type,
                        count_data_items
                    )
                    data_points[i][4] = self.set_statuses(GeneratorDataPoints.gen_statuses, count_data_items)
            local_seconds_multiplier += 1

    def setup_logging(self, name, log_file):
        if self.logging_mode.mode and name not in self.logging_mode.configured:
            formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
            handler = logging.FileHandler("logs/" + log_file, mode='w')
            handler.setFormatter(formatter)
            logger = logging.getLogger(name)
            logger.setLevel(self.logging_mode.log)
            logger.addHandler(handler)
            setattr(self.logging_mode, name, logger)
            self.logging_mode.configured.append(name)
        if self.logging_mode.mode:
            return getattr(self.logging_mode, name)
        return False

    def start(self):
        self.setup_logging("general", "general.log")
        self.apply_opc_settings_config()
        data_points = self.apply_data_points_config()
        self.subscribe_server_callback(CallbackType.ItemSubscriptionCreated, self.create_monitored_items)
        proc = Process(target=self.create_pool_setup_values, args=(data_points,))
        proc.start()
        setattr(self, "proc", proc)

    def stop(self):
        try:
            cmd = f"lsof -i :{self.port} | awk '{{print $2}}'"
            pid = subprocess.check_output(cmd, shell=True)
            # NOTE: 4 - length of 'PID\n' output after call check_output
            pid = pid.strip()[4:].decode("utf-8").split("\n", maxsplit=1)[0]
            cmd = f"kill -9 {pid}"
            subprocess.check_output(cmd, shell=True, stderr=None)
            self.proc.join()
            self.proc.close()
            log_msg = "kill create_pool_setup_values"
        except AttributeError:
            log_msg = "OPC UA Server don't stopped"
        if self.logging_mode.mode:
            self.logging_mode.general.debug(log_msg)
