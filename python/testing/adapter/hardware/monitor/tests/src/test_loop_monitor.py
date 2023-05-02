import json
from random import randint

from python.testing.adapter.hardware.monitor.monitor import Monitor


def get_fixture(pathname_fixture):
    with open(pathname_fixture, "r") as file:
        return json.load(file)


class TestMonitor:
    def test_write(self):
        data_to_write = "TestString"
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            mon.write_data(data_to_write.encode("utf-8"))
            assert mon.write_data(data_to_write.encode("utf-8")) == len(data_to_write.encode("utf-8"))

    def test_write_single_read(self):
        data_to_write = "TestString"
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            mon.write_data(data_to_write.encode("utf-8"))
            assert mon.read_data(trigger=data_to_write) == [data_to_write]

    def test_bulk_write_single_read(self):
        data_to_write = []
        count_data = 20
        for i in range(count_data):
            data_to_write.append("TestString" + str(i))
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            for item in data_to_write:
                mon.write_data((str(item) + "\n").encode("utf-8"))
            gen_read_data = mon.read_data(trigger=data_to_write[0], lines=count_data)
            assert len(gen_read_data) == count_data
            for line_data_read, line_data_to_write in zip(gen_read_data, data_to_write):
                assert line_data_read == line_data_to_write

    def test_readlines_from_stream(self):
        data_to_write = []
        for i in range(20):
            data_to_write.append("TestString" + str(i))
        trigger_line = 5
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            for item in data_to_write:
                mon.write_data((str(item) + "\n").encode("utf-8"))
            gen_read_data = mon.read_data(trigger="TestString0", lines=trigger_line)
            for line_data_read, line_data_to_write in zip(gen_read_data, data_to_write[:trigger_line]):
                assert line_data_read == line_data_to_write

    def test_read_single_line_from_stream(self):
        data_to_write = []
        for i in range(20):
            data_to_write.append("TestString" + str(i))
        trigger_line = 7
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            for item in data_to_write:
                mon.write_data((str(item) + "\n").encode("utf-8"))
            mon.read_data(trigger="TestString0", lines=trigger_line)
            single_read = mon.read_data()
            assert single_read == [data_to_write[trigger_line]]

    def test_more_trigger_write_single_read(self):
        data_to_write = "TestString and more bcgjkmpeq yjcjr trash gkj[jt ckjdj gkj[jt ckjdj ljkuj"
        test_data = ["TestString", "trash"]
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            mon.write_data(data_to_write.encode("utf-8"))
            assert mon.read_data(trigger=test_data) == [data_to_write]

    def test_more_trigger_bulk_write_single_read(self):
        data_to_write = []
        count_data = 20
        for i in range(count_data):
            data_to_write.append(
                "TestString" + str(i) + "and more bcgjkmpeq yjcjr trash gkj[jt ckjdj gkj[jt ckjdj ljkuj")
        with Monitor(fixture_obj=get_fixture("../fixtures/serial.json"), loopback=True) as mon:
            for item in data_to_write:
                mon.write_data((str(item) + "\n").encode("utf-8"))
            test_line = data_to_write[0].split()
            len_test_line = len(test_line)
            test_data = [test_line[randint(0, len_test_line - 1)] for _ in range(randint(1, len_test_line - 1))]
            test_data.append(test_line[0])
            gen_read_data = mon.read_data(trigger=test_data, lines=count_data)
            assert len(gen_read_data) == count_data
            for line_data_read, line_data_to_write in zip(gen_read_data, data_to_write):
                assert line_data_read == line_data_to_write
