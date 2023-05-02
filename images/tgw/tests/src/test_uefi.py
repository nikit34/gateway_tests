#!/usr/bin/env pipenv-shebang
from datetime import datetime, timedelta

import pytest

from conftest import fixtures_path
from python.testing.adapter.hardware.network.pc_env_preparer import prepare


@pytest.mark.usefixtures('power_manager', 'monitor')
class TestDate:
    '''
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14869
    '''

    @classmethod
    def setup_class(cls):
        prepare(components={"interface_mikrotik": True}, fixtures_path=fixtures_path)

    def test_display(self, monitor, right_date=datetime.now().strftime("%m/%d/%Y")):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/11620
        '''
        if monitor.check_data(trigger="No SD card found"):
            monitor.write_data(b"\r\n")
        else:
            raise ConnectionError("Monitor don't capture line")
        if monitor.check_data(trigger="Shell>"):
            monitor.write_data(b"date")
            monitor.write_data(b"\r\n")
        else:
            raise ConnectionError("Monitor don't capture line")
        if monitor.check_data(trigger="date"):
            line = monitor.read_data()[0]
            assert right_date in line, "Date set does not match current"
        else:
            raise ConnectionError("Monitor don't capture line")

    def test_display_reset(self, power_manager, monitor):
        power_manager.reset()
        self.test_display(monitor)


@pytest.mark.usefixtures('power_manager', 'monitor')
class TestTime:
    '''
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14812
    '''

    @classmethod
    def setup_class(cls):
        prepare(components={"interface_mikrotik": True}, fixtures_path=fixtures_path)

    def test_display(self, monitor):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/9491
        '''
        if monitor.check_data(trigger="No SD card found"):
            monitor.write_data(b"\r\n")
        else:
            raise ConnectionError("Monitor don't capture line")
        if monitor.check_data(trigger="Shell>"):
            monitor.write_data(b"time")
            monitor.write_data(b"\r\n")
        else:
            raise ConnectionError("Monitor don't capture line")
        if monitor.check_data(trigger="time"):
            line = monitor.read_data()[0]
            current_parts = line.split(" ", maxsplit=1)
            current_time = datetime.strptime(current_parts[0], "%H:%M:%S").time()
            right_datetime = datetime.now() - timedelta(hours=3)
            right_time_left = (right_datetime - timedelta(seconds=2)).time()
            right_time_right = right_datetime.time()
            assert right_time_left <= current_time <= right_time_right, \
                f"Time is set incorrectly: {right_time_left} <= {current_time} <= {right_time_right}"
            current_timezone = current_parts[1]
            right_timezone = "(GMT+03:00)"
            assert current_timezone == right_timezone, "Timezone is set incorrectly"
        else:
            raise ConnectionError("Monitor don't capture line")

    def test_display_reset(self, power_manager, monitor):
        power_manager.reset()
        self.test_display(monitor)


@pytest.mark.usefixtures('power_manager', 'monitor')
class TestTimezone:
    '''
    https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_testPlans/execute?planId=14791&suiteId=14811
    '''

    @classmethod
    def setup_class(cls):
        prepare(components={"interface_mikrotik": True}, fixtures_path=fixtures_path)

    def test_display(self, monitor, right_timezone="GMT+03:00"):
        '''
        https://extrndtfs.kaspersky.com/DefaultCollection/APROTECH/_workitems/edit/9488
        '''
        if monitor.check_data(trigger="No SD card found"):
            monitor.write_data(b"\r\n")
        else:
            raise ConnectionError("Monitor don't capture line")
        if monitor.check_data(trigger="Shell>"):
            monitor.write_data(b"timezone")
            monitor.write_data(b"\r\n")
        else:
            raise ConnectionError("Monitor don't capture line")
        if monitor.check_data(trigger="timezone"):
            line = monitor.read_data()[0]
            assert right_timezone == line, "Timezone set does not match current"
        else:
            raise ConnectionError("Monitor don't capture line")

    def test_display_reset(self, power_manager, monitor):
        power_manager.reset()
        self.test_display(monitor)
