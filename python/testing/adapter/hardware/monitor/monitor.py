import logging
from multiprocessing import Process, Lock
import os
import re
import serial
import time

from python.testing.adapter.hardware.network.serial_address_identifier import get_serial_address


def listener(connection, logger, lock, debug):
    while True:
        try:
            lock.acquire()
            line = str(connection.readline(), errors="replace")
            line = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])').sub('', line)
            line = line.rstrip()
            if debug:
                print("# ", line)
            logger.info(line)
            lock.release()
            time.sleep(0.1)
        except (serial.serialutil.SerialException, serial.SerialException) as err:
            print(err)


class Monitor:
    def __init__(self, fixture_obj=None, loopback=False, debug=False, logging_file=False):
        if fixture_obj is None:
            fixture_obj = self.apply_default_configuration()
        self.fixture_obj = fixture_obj
        self.loopback = loopback
        self.device = fixture_obj["serialAddress"]
        self.timeout = fixture_obj["serialTimeout"]
        self.ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        self.debug = debug
        self.logging_file = logging_file
        self.connection = None
        self.handler = None
        self.logger = None
        self.listener_lock = None
        self.listener_ps = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    @staticmethod
    def apply_default_configuration():
        return {
            "serialAddress": get_serial_address(),
            "serialBaudrate": 115200,
            "serialTimeout": 1
        }

    def connect(self):
        if self.loopback:
            self.connection = serial.serial_for_url(self.device, timeout=self.timeout)
        else:
            self.connection = serial.Serial(
                port=self.device,
                baudrate=self.fixture_obj["serialBaudrate"],
                timeout=self.timeout
            )
        if self.logging_file:
            formatter = logging.Formatter('%(asctime)s %(message)s')
            if not os.path.exists("logs/"):
                os.makedirs("logs/")
            self.handler = logging.FileHandler("logs/" + str(self.logging_file), mode='w')
            self.handler.setFormatter(formatter)

            self.logger = logging.getLogger('monitor')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(self.handler)

            self.listener_lock = Lock()
            self.listener_ps = Process(
                target=listener,
                args=(self.connection, self.logger, self.listener_lock, self.debug)
            )
            self.listener_ps.start()
        return self

    def disconnect(self):
        if self.logging_file:
            self.listener_lock.acquire()
            while True:
                self.listener_ps.terminate()
                time.sleep(0.1)
                if not self.listener_ps.is_alive():
                    self.listener_ps.join(timeout=1.0)
                    break
            self.logger.removeHandler(self.handler)
            del self.logger, self.handler
        self.connection.close()

    def __read_line(self, raw_return=False):
        try:
            line = str(self.connection.readline(), errors="replace")
            if not raw_return:
                line = self.ansi_escape.sub('', line)
            line = line.rstrip()
            if self.debug:
                print("# ", line)
            if self.logging_file:
                self.logger.info(line)
            return line
        except (OSError, serial.serialutil.SerialException, serial.SerialException):
            err_msg = f"[ERROR] Check another active connections for {self.device}"
            print(err_msg)
            if self.logging_file:
                self.logger.info(err_msg)
            return []

    def __fill_buffer(self, current_line, lines):
        yield current_line
        for _ in range(lines - 1):
            yield self.__read_line().rstrip("\n")

    def write_data(self, data):
        if not self.connection:
            raise ConnectionError("No serial connection established. Use context manager or connect/disconnect method")
        try:
            return self.connection.write(data)
        except serial.SerialException:
            err_msg = f"[ERROR] Check another active connections for {self.device}"
            print(err_msg)
            if self.logging_file:
                self.listener_lock.acquire()
                self.logger.info(err_msg)
                self.listener_lock.release()
            raise

    def read_data(self, trigger=None, lines=1, time_out=60):
        if self.logging_file:
            self.listener_lock.acquire()
        if not self.connection:
            raise ConnectionError("No serial connection established. Use context manager or connect/disconnect method")
        elif lines < 1:
            raise ValueError("Lines count cannot be less than 1")
        timepoint = time.time() + time_out
        current_line = self.__read_line()
        if trigger is not None:
            if isinstance(trigger, list):
                while time.time() <= timepoint:
                    all_trig_present_line = True
                    for trig in trigger:
                        if not isinstance(trig, str):
                            raise TypeError("trig maybe only string type")
                        if trig not in current_line:
                            all_trig_present_line = False
                    if all_trig_present_line:
                        break
                    else:
                        current_line = self.__read_line()
            elif isinstance(trigger, str):
                while trigger not in current_line and time.time() <= timepoint:
                    current_line = self.__read_line()
            else:
                raise TypeError("trigger maybe only string or list type")
        res = list(self.__fill_buffer(current_line.rstrip("\n"), lines))
        if self.logging_file:
            self.listener_lock.release()
        return res

    def check_data(self, trigger):
        data = self.read_data(trigger=trigger)
        for item_data in data:
            if item_data != '':
                return True
        return False

    def find_data(self, trigger, time_out=120):
        if self.logging_file:
            self.listener_lock.acquire()
        time_point = time.time() + time_out
        found = True
        current_line = self.__read_line()
        while trigger not in current_line:
            current_line = self.__read_line()
            if time.time() > time_point:
                found = False
                break
        if self.logging_file:
            self.listener_lock.release()
        return found
