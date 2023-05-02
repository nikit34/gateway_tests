import socket
from ftplib import FTP, error_perm, error_temp
from os import path
from time import sleep, time


class FTPClient(FTP):
    def __init__(self, host="192.168.177.77", port=5000, configs_path="", timeout=120, *args, **kwargs):
        super().__init__(timeout=timeout, *args, **kwargs)
        self.connect_timeout(host=host, port=port, timeout=timeout)
        self.configs_path = configs_path
        self.timeout = timeout

    def connect_timeout(self, host, port, timeout):
        t1 = time() + timeout
        while t1 > time():
            try:
                self.connect(host=host, port=port, timeout=timeout / 6)
                return
            except socket.timeout:
                sleep(2)
                print("Reconnecting FTP...")
        raise socket.timeout

    def _write_on_server_file(self, client_name, server_name):
        created_path = ""
        if "/" in server_name:
            server_name_list = server_name.split("/")
            dirs = server_name_list[:-1]
            for dir_item in dirs:
                t1 = time() + self.timeout
                while t1 > time():
                    try:
                        self.mkd(created_path + dir_item)
                        break
                    except socket.timeout:
                        sleep(1)
                        print("Reconnecting FTP...")
                else:
                    raise socket.timeout
                created_path += dir_item + "/"
        t1 = time() + self.timeout
        while t1 > time():
            try:
                if server_name in self.nlst(created_path):
                    self.delete(filename=server_name)
                break
            except socket.timeout:
                sleep(1)
                print("Reconnecting FTP...")
        else:
            raise socket.timeout
        with open(self.configs_path + client_name, "rb") as file:
            cmd = "STOR " + server_name
            try:
                self.storbinary(cmd=cmd, fp=file)
            except error_temp:
                print("[ERROR] File cannot be written")
                raise

    def write_on_server(self, client_name, server_name=None):
        if server_name is None:
            server_name = client_name
        if path.isfile(self.configs_path + client_name):
            self._write_on_server_file(client_name, server_name)
        elif path.isdir(self.configs_path + client_name):
            self.mkd(server_name)
        else:
            raise FileNotFoundError("[ERROR] File or directory don't exist")
        sleep(0.2)

    def write_on_server_more(self, client_names, server_names):
        for client_name, server_name in zip(client_names, server_names):
            self.write_on_server(client_name, server_name)

    def read_on_server(self, server_name, client_name=None):
        if client_name is None:
            client_name = server_name
        try:
            cmd = "RETR " + server_name
            try:
                with open(client_name, "wb") as file:
                    self.retrbinary(cmd, file.write)
            except FileNotFoundError:
                print("[ERROR] Folder struct invalid on client")
                raise
        except error_temp:
            print("[ERROR] File for read has not found")
            raise

    def delete_on_server(self, name):
        try:
            self.delete(filename=name)
        except error_perm:
            print("[ERROR] File for delete has not found")

    def list_on_server(self, path_ls):
        t1 = time() + self.timeout
        while t1 > time():
            try:
                return self.nlst(path_ls)
            except error_perm:
                print("[ERROR] No such directory")
                raise
            except socket.timeout:
                sleep(1)
                print("Reconnecting FTP...")
        raise socket.timeout
