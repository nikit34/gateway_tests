import argparse
import ast
from datetime import datetime
from scapy.contrib.mqtt import (
    MQTT,
    MQTTPublish,
    MQTTConnect,
    MQTTDisconnect,
    MQTTConnack,
    MQTTPuback,
    MQTTPubrec,
    MQTTPubrel,
    MQTTPubcomp,
    MQTTTopic,
    MQTTTopicQOS,
    MQTTSubscribe,
    MQTTSuback,
    MQTTUnsubscribe,
    MQTTUnsuback
)
from scapy.sendrecv import sniff


class MqttSniffer:
    def __init__(self, interface, debug=False, timeout=None):
        self.interface = interface
        self.debug = debug
        self.timeout = timeout
        self._lines = []
        names_columns = [
            "Time Stamp",
            "Name",
            "Topic",
            "Payload Status",
            "Payload Timestamp",
            "Payload TimestampSource",
            "Payload Value",
            "Dup",
            "Keep Alive",
            "Will Retain Flag",
            "Retain",
            "Will Qos Flag",
            "Qos",
            "Will Flag",
            "Will Topic",
            "Will Msg",
            "Username Flag",
            "Password Flag",
            "Username",
            "Password"
        ]
        self._init_history(names_columns)

    @staticmethod
    def _prepare_titles(names_columns):
        return {item: "" for item in names_columns}

    def _init_history(self, names_columns):
        self.columns = self._prepare_titles(names_columns)
        with open("logs/mqtt_sniffer_history.log", "w") as file:
            file.write(",".join(names_columns) + "\n")

    def _write_history(self, line_items):
        sep = ","
        self.columns.update(line_items)
        self.columns["Time Stamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = sep.join(map(str, self.columns.values()))
        self.columns.fromkeys(self.columns, "")
        with open("logs/mqtt_sniffer_history.log", "a") as file:
            file.write(line + "\n")

    def _handle_dhcp_packet(self, packet):
        if MQTT in packet:
            parse_packet = {
                "Name": packet[MQTT].name,
                "Dup": packet[MQTT].DUP,
                "Qos": packet[MQTT].QOS,
                "Retain": packet[MQTT].RETAIN,
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTPublish in packet:
            parse_payload = dict(ast.literal_eval(packet[MQTTPublish].value.decode("utf-8"))[0])
            status, timestamp, timestamp_source, value = parse_payload.values()
            parse_packet = {
                "Name": packet[MQTTPublish].name,
                "Topic": packet[MQTTPublish].topic.decode("utf-8"),
                "Payload Status": status,
                "Payload Timestamp": timestamp,
                "Payload TimestampSource": timestamp_source,
                "Payload Value": value
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTConnect in packet:
            parse_packet = {
                "Name": packet[MQTTConnect].name,
                "Username Flag": packet[MQTTConnect].usernameflag,
                "Password Flag": packet[MQTTConnect].passwordflag,
                "Will Retain Flag": packet[MQTTConnect].willretainflag,
                "Will Qos Flag": packet[MQTTConnect].willQOSflag,
                "Will Flag": packet[MQTTConnect].willflag,
                "Keep Alive": packet[MQTTConnect].klive,
                "Will Topic": packet[MQTTConnect].willtopic,
                "Will Msg": packet[MQTTConnect].willmsg,
                "Username": packet[MQTTConnect].username,
                "Password": packet[MQTTConnect].password,
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTDisconnect in packet:
            parse_packet = {
                "Name": packet[MQTTDisconnect].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTConnack in packet:
            parse_packet = {
                "Name": packet[MQTTConnack].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTPuback in packet:
            parse_packet = {
                "Name": packet[MQTTPuback].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTPubrec in packet:
            parse_packet = {
                "Name": packet[MQTTPubrec].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTPubrel in packet:
            parse_packet = {
                "Name": packet[MQTTPubrel].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTPubcomp in packet:
            parse_packet = {
                "Name": packet[MQTTPubcomp].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTTopic in packet:
            parse_packet = {
                "Name": packet[MQTTTopic].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTTopicQOS in packet:
            parse_packet = {
                "Name": packet[MQTTTopicQOS].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTSubscribe in packet:
            parse_packet = {
                "Name": packet[MQTTSubscribe].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTSuback in packet:
            parse_packet = {
                "Name": packet[MQTTSuback].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTUnsubscribe in packet:
            parse_packet = {
                "Name": packet[MQTTUnsubscribe].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)
        if MQTTUnsuback in packet:
            parse_packet = {
                "Name": packet[MQTTUnsuback].name
            }
            if self.debug:
                print("Packet: ", parse_packet)
            self._write_history(parse_packet)

    def start(self):
        kwargs_sniff = {
            "iface": self.interface,
            "filter": "tcp and dst port 1883",
            "prn": self._handle_dhcp_packet
        }
        if self.timeout is not None:
            kwargs_sniff["timeout"] = self.timeout
        sniff(**kwargs_sniff)


parser = argparse.ArgumentParser()
arguments = parser.add_argument_group()
arguments.add_argument("--interface", help="Bind MQTT sniffer with define interface")
arguments.add_argument("--debug", action="store_true", help="Run MQTT sniffer in debug mode")
arguments.add_argument("--timeout", default=None, help="Setup duration of MQTT sniffer")
args = parser.parse_args()

sniffer = MqttSniffer(
    interface=args.interface,
    debug=args.debug,
    timeout=int(args.timeout)
)
sniffer.start()
