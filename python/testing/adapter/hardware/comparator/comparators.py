from .parsers import ParserOpcUa, ParserMonitor, ParserMS


class OpcUaMonitor:
    def __init__(self, regex_monitor, gen_log_monitor, regex_opcua, gen_log_general=None, gen_log_variable=None):
        if not (bool(gen_log_general) ^ bool(gen_log_variable)):
            raise AttributeError("Second argument must be isn't None")
        self.gen_log_monitor = gen_log_monitor
        self.gen_log_opcua = gen_log_general if gen_log_general is not None else gen_log_variable
        self.parser_monitor = ParserMonitor(regex_monitor=regex_monitor)
        self.parser_opcua = ParserOpcUa(regex_opcua=regex_opcua)
        self.number_coincidences = 0
        self.number_opcua_dataitems = 0

    def __call__(self):
        gen_log_monitor_item = list(self.gen_log_monitor)
        opcua_value = None
        min_i = 0
        for line_log_opcua in self.gen_log_opcua:
            opcua_timestamp = self.parser_opcua.parse_opcua_timestamp(line_log_opcua)
            prev_value_opcua = opcua_value
            opcua_value = self.parser_opcua.parse_opcua_value(line_log_opcua)
            opcua_status = self.parser_opcua.parse_opcua_status(line_log_opcua)
            if None not in [opcua_timestamp, opcua_value, opcua_status]:
                for i, line_log_monitor in enumerate(gen_log_monitor_item[min_i:]):
                    monitor_timestamp = self.parser_monitor.parse_monitor_timestamp(line_log_monitor)
                    monitor_value = self.parser_monitor.parse_monitor_value(line_log_monitor)
                    monitor_status = self.parser_monitor.parse_monitor_status(line_log_monitor)
                    if monitor_timestamp == opcua_timestamp and \
                            monitor_value == opcua_value and \
                            monitor_status == opcua_status:
                        self.number_coincidences += 1
                        if min_i == 0 or min_i < i - 20:
                            min_i = i - 20
                        break
                if prev_value_opcua != opcua_value:
                    self.number_opcua_dataitems += 1
        return self.number_opcua_dataitems, self.number_coincidences


class MonitorMS:
    def __init__(self, regex_monitor, gen_log_monitor, gen_log_variable_ms):
        self.parser_monitor = ParserMonitor(regex_monitor=regex_monitor)
        self.gen_log_monitor = gen_log_monitor
        self.gen_log_variable_ms = gen_log_variable_ms
        self.number_coincidences = 0
        self.number_ms_dataitems = 0

    def __call__(self):
        gen_log_monitor_item = list(self.gen_log_monitor)
        for line_log_ms in self.gen_log_variable_ms:
            ms_status, ms_value, ms_timestamp = ParserMS.parse_ms_line(line_log_ms)
            if None not in [ms_timestamp, ms_value, ms_status]:
                for line_log_monitor in gen_log_monitor_item:
                    monitor_timestamp = self.parser_monitor.parse_monitor_timestamp(line_log_monitor)
                    monitor_value = self.parser_monitor.parse_monitor_value(line_log_monitor)
                    monitor_status = self.parser_monitor.parse_monitor_status(line_log_monitor)
                    if monitor_timestamp == ms_timestamp and \
                            monitor_value == ms_value and \
                            monitor_status == ms_status:
                        self.number_coincidences += 1
                        break
                self.number_ms_dataitems += 1
        return self.number_ms_dataitems, self.number_coincidences


class OpcUaMS:
    def __init__(self, regex_opcua, gen_log_variable, gen_log_variable_ms):
        self.parser_opcua = ParserOpcUa(regex_opcua=regex_opcua)
        self.gen_log_variable = gen_log_variable
        self.gen_log_variable_ms = gen_log_variable_ms
        self.number_coincidences = 0
        self.number_opcua_dataitems = 0

    def __call__(self):
        gen_log_variable_ms_item = list(self.gen_log_variable_ms)
        opcua_value = None
        for line_log_opcua in self.gen_log_variable:
            opcua_status = self.parser_opcua.parse_opcua_status(line_log_opcua)
            prev_value_opcua = opcua_value
            opcua_value = self.parser_opcua.parse_opcua_value(line_log_opcua)
            opcua_timestamp = self.parser_opcua.parse_opcua_timestamp(line_log_opcua)
            if None not in [opcua_timestamp, opcua_value, opcua_status]:
                for line_log_ms in gen_log_variable_ms_item:
                    ms_status, ms_value, ms_timestamp = ParserMS.parse_ms_line(line_log_ms)
                    if ms_timestamp == opcua_timestamp and \
                            ms_value == opcua_value and \
                            ms_status == opcua_status:
                        self.number_coincidences += 1
                        break
                if prev_value_opcua != opcua_value:
                    self.number_opcua_dataitems += 1
        return self.number_opcua_dataitems, self.number_coincidences
