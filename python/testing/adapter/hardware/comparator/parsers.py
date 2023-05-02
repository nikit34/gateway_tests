import re


class ParserOpcUa:
    def __init__(self, regex_opcua):
        self.regex_opcua = regex_opcua

    def parse_opcua_timestamp(self, line_log_opcua):
        raw = re.search(self.regex_opcua["timestamp"], line_log_opcua)
        if raw is not None:
            return raw.group(1)[:-3]

    def parse_opcua_value(self, line_log_opcua):
        raw = re.search(self.regex_opcua["value"], line_log_opcua)
        if raw is not None:
            raw_group = raw.group(1)
            if raw_group in ["True", "False"]:
                return raw_group.lower()
            raw_double = re.search(r"(\d+)\.\d+", raw_group)
            if raw_double is not None:
                return raw_double.group(1)
            return raw_group

    def parse_opcua_status(self, line_log_opcua):
        raw = re.search(self.regex_opcua["status"], line_log_opcua)
        if raw is not None:
            return raw.group(1)


class ParserMonitor:
    def __init__(self, regex_monitor):
        self.regex_monitor = regex_monitor

    def parse_monitor_timestamp(self, line_log_monitor):
        raw = re.search(self.regex_monitor["dataItem"]["timestamp"], line_log_monitor)
        if raw is not None:
            return raw.group(1).replace("T", " ").replace("Z", "")

    def parse_monitor_value(self, line_log_monitor):
        raw = re.search(self.regex_monitor["dataItem"]["value"], line_log_monitor)
        if raw is not None:
            raw_group = raw.group(1)
            raw_double = re.search(r"(\d+)\.\d+", raw_group)
            if raw_double is not None:
                return raw_double.group(1)
            return raw.group(1)

    def parse_monitor_status(self, line_log_monitor):
        raw = re.search(self.regex_monitor["dataItem"]["status"], line_log_monitor)
        if raw is not None:
            return raw.group(1)[-1:]

    def parse_monitor_port_id(self, line_log_monitor):
        raw = re.search(self.regex_monitor["portId"], line_log_monitor)
        if raw is not None:
            return raw.group(1)


class ParserMS:
    @staticmethod
    def parse_ms_line(line_log_ms):
        ms_status, ms_value, row_ms_timestamp = line_log_ms.split(",")
        if ms_value in ["True", "False"]:
            ms_value = ms_value.lower()
        raw_ms_value = re.search(r"(\d+)\.\d+", ms_value)
        if raw_ms_value is not None:
            ms_value = raw_ms_value.group(1)
        ms_timestamp = row_ms_timestamp.replace("T", " ").replace("Z\n", "")
        return ms_status, ms_value, ms_timestamp
