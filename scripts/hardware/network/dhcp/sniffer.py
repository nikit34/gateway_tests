import argparse
from datetime import datetime
from scapy.layers.l2 import Ether
from scapy.layers.dhcp import DHCP, BOOTP, IP
from scapy.sendrecv import sniff


class DhcpSniffer:
    def __init__(self, debug=False, timeout=None):
        self.debug = debug
        self.timeout = timeout
        self._init_history()

    @staticmethod
    def _init_history():
        names_columns = [
            "Time Stamp",
            "Boot Request"
        ]
        with open("logs/dhcp_sniffer_history.log", "w") as file:
            file.write(",".join(names_columns) + "\n")

    @staticmethod
    def _get_option(dhcp_options, key):
        must_decode_options = [
            "hostname",
            "domain",
            "vendor_class_id"
        ]
        for dhcp_option in dhcp_options:
            if dhcp_option[0] == "name_server" and len(dhcp_option) > 2:
                return ",".join(dhcp_option[1:])
            elif dhcp_option[0] == key and dhcp_option[0] in must_decode_options:
                return dhcp_option[1].decode()
            elif dhcp_option[0] == key:
                return dhcp_option[1]
        return ""

    @staticmethod
    def _write_history(*args):
        sep = ","
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = sep.join(map(str, args))
        with open("logs/dhcp_sniffer_history.log", "a") as file:
            file.write(time_stamp + sep + line + "\n")

    def _handle_dhcp_packet(self, packet):
        if DHCP in packet:
            type_packet = packet[DHCP].options[0][1]
            if type_packet == 1:
                hostname = self._get_option(packet[DHCP].options, "hostname")

                self._write_history("DHCPDISCOVER", hostname)

                if self.debug:
                    print("DHCPDISCOVER")
                    print(f"Host {hostname} ({packet[Ether].src}) asked for an IP")

            elif type_packet == 2:
                subnet_mask = self._get_option(packet[DHCP].options, "subnet_mask")
                lease_time = self._get_option(packet[DHCP].options, "lease_time")
                router = self._get_option(packet[DHCP].options, "router")
                name_server = self._get_option(packet[DHCP].options, "name_server")
                domain = self._get_option(packet[DHCP].options, "domain")

                self._write_history("DHCPOFFER", subnet_mask, lease_time, router, name_server, domain)

                if self.debug:
                    print("DHCPOFFER")
                    print(f"DHCP Server {packet[IP].src} ({packet[Ether].src}) "
                          f"offered {packet[BOOTP].yiaddr}")
                    print(f"DHCP Options: subnet_mask: {subnet_mask}, lease_time: "
                          f"{lease_time}, router: {router}, name_server: {name_server}, "
                          f"domain: {domain}")

            elif type_packet == 3:
                requested_addr = self._get_option(packet[DHCP].options, "requested_addr")
                hostname = self._get_option(packet[DHCP].options, "hostname")

                self._write_history("DHCPREQUEST", hostname, requested_addr)

                if self.debug:
                    print("DHCPREQUEST")
                    print(f"Host {hostname} ({packet[Ether].src}) requested {requested_addr}")

            elif type_packet == 5:
                subnet_mask = self._get_option(packet[DHCP].options, "subnet_mask")
                lease_time = self._get_option(packet[DHCP].options, "lease_time")
                router = self._get_option(packet[DHCP].options, "router")
                name_server = self._get_option(packet[DHCP].options, "name_server")

                self._write_history("DHCPACK", subnet_mask, lease_time, router, name_server)

                if self.debug:
                    print("DHCPACK")
                    print(f"DHCP Server {packet[IP].src} ({packet[Ether].src}) "
                          f"acked {packet[BOOTP].yiaddr}")
                    print(f"DHCP Options: subnet_mask: {subnet_mask}, lease_time: "
                          f"{lease_time}, router: {router}, name_server: {name_server}")

            elif type_packet == 8:
                hostname = self._get_option(packet[DHCP].options, "hostname")
                vendor_class_id = self._get_option(packet[DHCP].options, "vendor_class_id")

                self._write_history("DHCPINFORM", hostname, vendor_class_id)

                if self.debug:
                    print("DHCPINFORM")
                    print(f"DHCP Inform from {packet[IP].src} ({packet[Ether].src}) "
                          f"hostname: {hostname}, vendor_class_id: {vendor_class_id}")

            else:
                self._write_history("[DHCPDECLINE, DHCPNAK, DHCPRELEASE]", packet.summary())
                if self.debug:
                    print("DHCPDECLINE or DHCPNAK or DHCPRELEASE")
                    print(packet.summary())

    def start(self):
        kwargs_sniff = {
            "filter": "udp and (port 67 or 68)",
            "prn": self._handle_dhcp_packet
        }
        if self.timeout is not None:
            kwargs_sniff["timeout"] = self.timeout
        sniff(**kwargs_sniff)


parser = argparse.ArgumentParser()
arguments = parser.add_argument_group()
arguments.add_argument("--debug", action="store_true", help="Run DHCP sniffer in debug mode")
arguments.add_argument("--timeout", default=None, help="Setup duration of DHCP sniffer")
args = parser.parse_args()

sniffer = DhcpSniffer(
    debug=args.debug,
    timeout=int(args.timeout)
)
sniffer.start()
