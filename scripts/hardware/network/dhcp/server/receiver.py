import argparse
from datetime import datetime
import json
import os
import re
import socket
from struct import pack
import threading
import time


def get_globalhost_interface():
    output = os.popen('ip addr show').read()
    founds = re.findall(re.compile(
        r'inet (\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\/\d{1,2} '
        r'brd \b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b '
        r'scope global (?:dynamic noprefixroute |)([a-z0-9]+)'
    ), output)
    for ip, interface in founds:
        if ".65." in ip and len(interface) == 15:
            return interface
    raise OSError("Ambiguous definition of external interface")


class DhcpStructure:
    @staticmethod
    def _find_options(data, res):
        if data[res["gpoz"]] == 53:
            res["option53"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            if data[res["gpoz"] + 2] == 1:
                res["op"] = "DHCPDISCOVER"
            elif data[res["gpoz"] + 2] == 2:
                res["op"] = "DHCPOFFER"
            elif data[res["gpoz"] + 2] == 3:
                res["op"] = "DHCPREQUEST"
            elif data[res["gpoz"] + 2] == 4:
                res["op"] = "DHCPDECLINE"
            elif data[res["gpoz"] + 2] == 5:
                res["op"] = "DHCPACK"
            elif data[res["gpoz"] + 2] == 6:
                res["op"] = "DHCPNAK"
            elif data[res["gpoz"] + 2] == 7:
                res["op"] = "DHCPRELEASE"
            elif data[res["gpoz"] + 2] == 8:
                res["op"] = "DHCPINFORM"
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 61:
            res["option61"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            htype = data[res["gpoz"] + 2]
            if htype == 1:
                res["HType"] = "Ethernet"
            else:
                res["HType"] = "unknown"
            res["ClientMacAddress"] = data[
                                      res["gpoz"] + 3: res["gpoz"] + 2 + ln
                                      ].hex()
            res["ClientMacAddressByte"] = data[
                                          res["gpoz"] + 3: res["gpoz"] + 2 + ln
                                          ]
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 116:
            res["option116"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["DHCPAUTO"] = True
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 12:
            res["option12"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["HostName"] = data[res["gpoz"] + 2:res["gpoz"] + ln + 2]
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 60:
            res["option60"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["Vendor"] = data[res["gpoz"] + 2:res["gpoz"] + ln + 2]
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 55:
            res["option55"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            for preq in range(ln):
                if data[res["gpoz"] + 2 + preq] == 1:
                    res["ReqListSubnetMask"] = True
                elif data[res["gpoz"] + 2 + preq] == 15:
                    res["ReqListDomainName"] = True
                elif data[res["gpoz"] + 2 + preq] == 3:
                    res["ReqListRouter"] = True
                elif data[res["gpoz"] + 2 + preq] == 6:
                    res["ReqListDNS"] = True
                elif data[res["gpoz"] + 2 + preq] == 31:
                    res["ReqListPerfowmRouterDiscover"] = True
                elif data[res["gpoz"] + 2 + preq] == 33:
                    res["ReqListStaticRoute"] = True
                elif data[res["gpoz"] + 2 + preq] == 43:
                    res["ReqListVendorSpecInfo"] = 43
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 50:
            res["option50"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["RequestedIpAddress"] = socket.inet_ntoa(
                pack(
                    'BBBB',
                    data[res["gpoz"] + 2],
                    data[res["gpoz"] + 3],
                    data[res["gpoz"] + 4],
                    data[res["gpoz"] + 5]
                )
            )
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 54:
            res["option54"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["DHCPServerIP"] = socket.inet_ntoa(
                pack(
                    'BBBB',
                    data[res["gpoz"] + 2],
                    data[res["gpoz"] + 3],
                    data[res["gpoz"] + 4],
                    data[res["gpoz"] + 5]
                )
            )
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 51:
            res["option51"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["DHCPLeaseTime"] = data[res["gpoz"] + 2] * 256 * 256 * 256 * 256 \
                                   + data[res["gpoz"] + 3] * 256 * 256 \
                                   + data[res["gpoz"] + 4] * 256 \
                                   + data[res["gpoz"] + 5]
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 1:
            res["option1"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["SubnetMask"] = socket.inet_ntoa(
                pack(
                    'BBBB',
                    data[res["gpoz"] + 2],
                    data[res["gpoz"] + 3],
                    data[res["gpoz"] + 4],
                    data[res["gpoz"] + 5]
                )
            )
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 3:
            res["option3"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["Router"] = socket.inet_ntoa(
                pack(
                    'BBBB',
                    data[res["gpoz"] + 2],
                    data[res["gpoz"] + 3],
                    data[res["gpoz"] + 4],
                    data[res["gpoz"] + 5]
                )
            )
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 6:
            res["option6"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["DNS"] = socket.inet_ntoa(
                pack(
                    'BBBB',
                    data[res["gpoz"] + 2],
                    data[res["gpoz"] + 3],
                    data[res["gpoz"] + 4],
                    data[res["gpoz"] + 5]
                )
            )
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 42:
            res["option42"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["NTPS"] = socket.inet_ntoa(
                pack(
                    'BBBB',
                    data[res["gpoz"] + 2],
                    data[res["gpoz"] + 3],
                    data[res["gpoz"] + 4],
                    data[res["gpoz"] + 5]
                )
            )
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 82:
            res["option82"] = data[res["gpoz"]]
            ln = data[res["gpoz"] + 1]
            res["option_82_AgentCircuitId_len"] = data[res["gpoz"] + 3]
            res["option_82_AgentCircuitId_hex"] = data[
                                                  res["gpoz"] + 4:
                                                  res["gpoz"] + 4 + res["option_82_AgentCircuitId_len"]
                                                  ].hex()
            res["option_82_AgentCircuitId_port_hex"] = data[
                                                       res["gpoz"] + 3 + res["option_82_AgentCircuitId_len"]:
                                                       res["gpoz"] + 4 + res["option_82_AgentCircuitId_len"]
                                                       ].hex()
            res["option_82_AgentRemoteId_len"] = data[
                res["gpoz"] + 5 + res["option_82_AgentCircuitId_len"]
                ]
            res["option_82_AgentRemoteId_hex"] = data[
                                                 res["gpoz"] + 6 + res["option_82_AgentCircuitId_len"]:
                                                 res["gpoz"] + 6 + res["option_82_AgentCircuitId_len"] + res[
                                                     "option_82_AgentRemoteId_len"]
                                                 ].hex()
            res["option_82_len"] = ln
            res["option_82_byte"] = data[
                                    res["gpoz"] + 1: res["gpoz"] + 2 + ln
                                    ]
            res["option_82_hex"] = data[
                                   res["gpoz"] + 1: res["gpoz"] + 2 + ln
                                   ].hex()
            res["option_82_str"] = str(data[
                                       res["gpoz"] + 1: res["gpoz"] + 2 + ln
                                       ])
            res["gpoz"] = res["gpoz"] + ln + 2

        elif data[res["gpoz"]] == 255:
            res["gpoz"] = len(data) + 1

        else:
            opname = str(data[res["gpoz"]])
            ln = data[res["gpoz"] + 1]
            res["unknown_option_" + opname] = data[
                                              res["gpoz"] + 1:
                                              res["gpoz"] + 2 + ln
                                              ]
            res["unknown_option_" + opname + "_hex"] = data[
                                                       res["gpoz"] + 1:
                                                       res["gpoz"] + 2 + ln
                                                       ].hex()
            res["unknown_option_" + opname + "_str"] = str(data[
                                                           res["gpoz"] + 1:
                                                           res["gpoz"] + 2 + ln
                                                           ])
            res["unknown_option_" + opname + "_len"] = ln
            res["gpoz"] = res["gpoz"] + ln + 2
        return res

    def _parse_packet(self, data):
        res = {}
        if data[0] == 1:
            res["op"] = "DHCPDISCOVER/DHCPREQUEST"
        elif data[0] == 2:
            res["op"] = "DHCPOFFER/DHCPACK"
        if data[1] == 1:
            res["htype"] = "MAC"
        res["hlen"] = data[2]
        res["hops"] = data[3]
        res["xidhex"] = data[4:8].hex()
        res["xidbyte"] = data[4:8]
        res["secs"] = data[8] * 256 + data[9]
        res["flags"] = pack('BB', data[10], data[11])
        res["ciaddr"] = socket.inet_ntoa(pack('BBBB', data[12], data[13], data[14], data[15]))
        res["yiaddr"] = socket.inet_ntoa(pack('BBBB', data[16], data[17], data[18], data[19]))
        res["siaddr"] = socket.inet_ntoa(pack('BBBB', data[20], data[21], data[22], data[23]))
        res["giaddr"] = socket.inet_ntoa(pack('BBBB', data[24], data[25], data[26], data[27]))
        res["chaddr"] = data[28:34].hex()
        res["magic_cookie"] = data[236:240]
        res["HostName"] = "unknown"
        res["ClientMacAddress"] = res["chaddr"]
        res["ClientMacAddressByte"] = data[28:34]
        res["RequestedIpAddress"] = "0.0.0.0"
        res["option82"] = "none"
        if res["magic_cookie"] == b'c\x82Sc':
            res["gpoz"] = 240
            while res["gpoz"] < len(data):
                res = self._find_options(data, res)
        return res


class DhcpCreator:
    def __init__(self, ip_dhcp_server):
        self.ip_dhcp_server = ip_dhcp_server

    @staticmethod
    def _padding_zero(cnt):
        res = b''
        for _ in range(cnt):
            res += pack("B", 0)
        return res

    def create_dhcp_offer(self, packet, res_sql):
        res = pack("BBBB", 2, 1, 6, 0) \
              + pack(
            "BBBB",
            *packet["xidbyte"]
        ) \
              + pack("BBBB", 0, 0, 0, 0) \
              + pack("BBBB", 0, 0, 0, 0) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["ip"].decode('utf-8')
        ) \
              + socket.inet_pton(
            socket.AF_INET,
            "0.0.0.0"
        ) \
              + socket.inet_pton(
            socket.AF_INET,
            packet["giaddr"]
        ) \
              + pack(
            "BBBBBB",
            *packet["ClientMacAddressByte"]
        ) \
              + self._padding_zero(202) \
              + packet["magic_cookie"] \
              + pack("BBBBB", 53, 1, 2, 54, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            self.ip_dhcp_server
        ) \
              + pack("BB", 51, 4) \
              + pack(">I", 8600) \
              + pack("BB", 1, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["mask"].decode('utf-8')
        ) \
              + pack("BB", 3, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["router"].decode('utf-8')
        ) \
              + pack("BB", 6, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["DNS"].decode('utf-8')
        )
        if packet["option82"] != "none":
            res += pack("B", 82)
            for bb in packet["option_82_byte"]:
                res += pack("B", bb)
        res += pack("B", 255) \
               + self._padding_zero(28)
        return res

    def create_dhcp_ask(self, packet, res_sql):
        res = pack("BBBB", 2, 1, 6, 0) \
              + pack(
            "BBBB",
            *packet["xidbyte"]
        ) \
              + pack("BBBB", 0, 0, 0, 0) \
              + pack("BBBB", 0, 0, 0, 0) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["ip"].decode('utf-8')
        ) \
              + socket.inet_pton(
            socket.AF_INET,
            self.ip_dhcp_server
        ) \
              + socket.inet_pton(
            socket.AF_INET,
            packet["giaddr"]
        ) \
              + pack(
            "BBBBBB",
            *packet["ClientMacAddressByte"]
        ) \
              + self._padding_zero(202) \
              + packet["magic_cookie"] \
              + pack("BBBBB", 53, 1, 5, 54, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            self.ip_dhcp_server
        ) \
              + pack("BB", 51, 4) \
              + pack(">I", 8600) \
              + pack("BB", 1, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["mask"].decode('utf-8')
        ) \
              + pack("BB", 3, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["router"].decode('utf-8')
        ) \
              + pack("BB", 6, 4) \
              + socket.inet_pton(
            socket.AF_INET,
            res_sql["DNS"].decode('utf-8')
        )
        if packet["option82"] != "none":
            res += pack("B", 82)
            for bb in packet["option_82_byte"]:
                res += pack("B", bb)
        res += pack("B", 255) \
               + self._padding_zero(28)
        return res


class DhcpReceiver(DhcpStructure):
    def __init__(self, dhcp_settings_obj, debug=False, timeout=None):
        self.dhcp_settings_obj = dhcp_settings_obj
        self.dhcp_creator = DhcpCreator(dhcp_settings_obj["DHCPServer"])
        self.debug = debug
        self._init_socket(timeout)
        self.threads = []
        self.listen_ip = "0.0.0.0"
        self._init_history()

    def _init_socket(self, timeout):
        self.src_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        interface = (get_globalhost_interface() + "\0").encode("utf8")
        self.src_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, interface)
        if timeout is not None:
            self.src_socket.settimeout(timeout)

    @staticmethod
    def _init_history():
        names_columns = [
            "Time Stamp",
            "Boot Request"
        ]
        with open("logs/dhcp_receiver_history.log", "w") as file:
            file.write(",".join(names_columns) + "\n")

    @staticmethod
    def _write_history(*args):
        sep = ","
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = sep.join(map(str, args))
        with open("logs/dhcp_receiver_history.log", "a") as file:
            file.write(time_stamp + sep + line + "\n")

    def _setup_options(self, res):
        for option in self.dhcp_settings_obj["options"]:
            option_sp = option.split(":")
            if option_sp[0] in res:
                res[option_sp[1]] = res[option_sp[0]][int(option_sp[2]): int(option_sp[3])]
        return res

    def _read_saved_ip(self, packet):
        res = {
            "ip": "",
            "mask": self.dhcp_settings_obj["defaultMask"],
            "router": self.dhcp_settings_obj["defaultRouter"],
            "DNS": self.dhcp_settings_obj["defaultDNS"]
        }
        select_filters = [
            ("option_82_AgentRemoteId_hex", "option_82_AgentCircuitId_port_hex"),
            ("sw_mac", "sw_port2"),
            ("ClientMacAddress",),
        ]
        with open(__file__.split("receiver.py")[0] + "db/dhcp_receiver_clients.csv", "r") as file:
            for line in file.readlines():
                ip, mask, router, dns, mac = line.split(",")
                for select_filter in select_filters:
                    for item_filter in select_filter:
                        if item_filter in packet and packet[item_filter] == mac.rstrip("\n"):
                            res["ip"] = ip.encode("ascii")
                            res["mask"] = mask.encode("ascii")
                            res["router"] = router.encode("ascii")
                            res["DNS"] = dns.encode("ascii")
        return res

    def _worker(self, data, addr):
        packet_without_options = self._parse_packet(data)
        packet = self._setup_options(packet_without_options)
        if self.debug:
            print(packet["op"])
        self._write_history(packet["op"])
        if packet["op"] in ["DHCPDISCOVER", "DHCPREQUEST"]:
            res_sql = self._read_saved_ip(packet)
            if res_sql["ip"] != "":
                if packet["op"] == "DHCPDISCOVER":
                    packet_body = self.dhcp_creator.create_dhcp_offer(packet, res_sql)
                    packet_name = "DHCPOFFER"
                else:
                    packet_body = self.dhcp_creator.create_dhcp_ask(packet, res_sql)
                    packet_name = "DHCPACK"
                if self.debug:
                    print(packet_name)
                self._write_history(packet_name)
                self.src_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                self.src_socket.sendto(packet_body, (self.dhcp_settings_obj["broadcast"], 68))
                if packet["giaddr"] != "0.0.0.0":
                    self.src_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    self.src_socket.sendto(packet_body, addr)
            else:
                print("IP not found in DB")

    def start(self):
        self.src_socket.bind((self.listen_ip, 67))

        # TODO: create parent thread for control main child of childs
        try:
            while True:
                try:
                   data, addr = self.src_socket.recvfrom(1024)
                except socket.timeout:
                    return

                thread = threading.Thread(target=self._worker, args=(data, addr,))
                thread.start()
                self.threads.append(thread)
                while threading.active_count() > self.dhcp_settings_obj["ThreadLimit"]:
                    time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.src_socket.close()
        for thread in self.threads:
            if thread.is_alive():
                thread.join()
        print("DHCP Server is terminating")


def get_fixture(configs_path, name_fixture):
    with open(configs_path + name_fixture, "r") as file:
        return json.load(file)


parser = argparse.ArgumentParser()
arguments = parser.add_argument_group()
arguments.add_argument("--debug", action="store_true", help="Run DHCP server in debug mode")
arguments.add_argument("--timeout", default=None, help="Setup duration of DHCP server")
args = parser.parse_args()

receiver = DhcpReceiver(
    dhcp_settings_obj=get_fixture(__file__.split("receiver.py")[0], "config.json"),
    debug=args.debug,
    timeout=int(args.timeout),
)

receiver.start()
receiver.stop()
