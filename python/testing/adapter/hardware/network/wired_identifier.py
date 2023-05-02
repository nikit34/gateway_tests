import json
import os
import re
import subprocess
from time import time


def get_globalhost_ip(select_filter=".65."):
    output = os.popen('ip addr show').read()
    founds = re.findall(re.compile(
        r'inet (\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\/\d{1,2} '
        r'(?:brd \b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b |)'
        r'scope global'
    ), output)
    for found in founds:
        if select_filter in found:
            return found
    raise OSError("Ambiguous definition of external IP address\n"
                  f"Found addresses: {founds}")


def get_globalhost_interface(select_filter=".65."):
    output = os.popen('ip addr show').read()
    founds = re.findall(re.compile(
        r'inet (\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b)\/\d{1,2} '
        r'(?:brd \b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b |)'
        r'scope global ([a-z0-9]+)'
    ), output)
    for ip, interface in founds:
        if select_filter in ip and len(interface) == 15:
            return interface
    raise OSError("Ambiguous definition of external interface")


def set_ip_config(key_ip, path_file, prefix_url, suffix_url, select_filter=".65."):
    global_ip = get_globalhost_ip(select_filter=select_filter)
    with open(path_file, "r") as file:
        fixture_obj = json.load(file)
    fixture_obj[key_ip] = prefix_url + global_ip + suffix_url
    with open(path_file, "w") as file:
        json.dump(fixture_obj, file, indent=4)


def set_globalhost_ip(interface, ip_address):
    subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
    full_ip_address = ip_address + "/24"
    proc = subprocess.Popen(
        ["sudo", "-S", "ip", "addr", "add", full_ip_address, "dev", interface],
        stdin=subprocess_superuser.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, err = proc.communicate()
    if output != b"" or (
        err != b"" and
        b"password" not in err and
        b"RTNETLINK" not in err
    ):
        raise ValueError(f"Set ip address raising failed - output: {output}, err: {err}")
    start_time = time()
    while time() - start_time < 5:
        try:
            if get_globalhost_ip(ip_address[7:11]) == ip_address:
                break
        except OSError:
            print("Second address set")
    else:
        raise ValueError("IP address setting failed")


def get_ip_ftp_client(path_file):
    with open(path_file, "r") as file:
        for line in file.readlines():
            if "static ip_address=" in line:
                return line.split("=")[1].split("/")[0]
    raise FileExistsError("Required field is not in file")


def up_interface(interface):
    subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
    proc = subprocess.Popen(
        ["sudo", "-S", "ip", "link", "set", "dev", interface, "up"],
        stdin=subprocess_superuser.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    output, err = proc.communicate()
    if output != b"" or (err != b"" and b"[sudo] password" not in err):
        raise ValueError(f"Interface up raising failed - output: {output}, err: {err}")
