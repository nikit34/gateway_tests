from datetime import datetime, timedelta
from random import randint, choice, uniform, shuffle
import string


class GeneratorDataPoints:
    def __init__(self, custom_count_types=None):
        if custom_count_types is None:
            self.count_types = {"Boolean": 1, "Int": 1, "Long": 1, "Double": 1, "String": 1}
        else:
            self.count_types = custom_count_types

    @staticmethod
    def _random_string(string_length=None):
        if string_length is None:
            string_length = randint(1, 256)
        return ''.join(choice(string.ascii_letters + string.digits) for i in range(string_length))

    @staticmethod
    def _gen_boolean(count_data_items, *args):
        return [choice([True, False]) for _ in range(count_data_items)]

    @staticmethod
    def _gen_int(count_data_items, *args):
        return [str(randint(-32768, 32767)) for _ in range(count_data_items)]

    @staticmethod
    def _gen_long(count_data_items, *args):
        return [str(randint(-2147483648, 2147483647)) for _ in range(count_data_items)]

    @staticmethod
    def _gen_double(count_data_items, *args):
        return [str(uniform(-32768., 32767.)) for _ in range(count_data_items)]

    def _gen_string(self, count_data_items, length_str):
        return [self._random_string(length_str) for _ in range(count_data_items)]

    @classmethod
    def gen_values(cls, typecast, count_data_items=5, length_str=None):
        self = cls()
        charged_gen_points = {
            "Boolean": self._gen_boolean,
            "Int": self._gen_int,
            "Long": self._gen_long,
            "Double": self._gen_double,
            "String": self._gen_string
        }
        return charged_gen_points[typecast](count_data_items, length_str)

    @classmethod
    def gen_timestamps(cls, median_sec_step=60, count_data_items=5):
        timestamps = []
        for i in range(count_data_items, 0, -1):
            random_sec_step = randint((i - 1) * median_sec_step, i * median_sec_step)
            random_datetime = (datetime.now() - timedelta(seconds=random_sec_step))
            random_zulu_datetime = random_datetime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            timestamps.append(random_zulu_datetime)
        return timestamps

    @classmethod
    def gen_statuses(cls, count_data_items=5):
        random_count_zero = randint(0, count_data_items)
        mask = [0] * random_count_zero + [1] * (count_data_items - random_count_zero)
        shuffle(mask)
        return mask

    @classmethod
    def gen_data_points(cls, custom_count_types=None, random_sec_interval=300, count_data_items=5, length_str=None):
        self = cls(custom_count_types=custom_count_types)
        median_sec_step = int(random_sec_interval / count_data_items)
        data_points_config = {"commonInterval": randint(0, 5), "dataPoints": []}
        global_count = 0
        for typecast, count in self.count_types.items():
            if typecast not in ["Boolean", "Int", "Long", "Double", "String"]:
                raise ValueError("Set value of type is invalid")
            data_point = {"dataType": typecast}
            for num in range(count):
                data_point["dataName"] = typecast + str(num)
                data_point["id"] = global_count
                data_point["dataItems"] = []
                timestamps = self.gen_timestamps(median_sec_step=median_sec_step, count_data_items=count_data_items)
                values = self.gen_values(typecast=typecast, count_data_items=count_data_items, length_str=length_str)
                statuses = self.gen_statuses(count_data_items=count_data_items)
                for timestamp, value, status in zip(timestamps, values, statuses):
                    data_point["dataItems"].append({
                        "timestamp": timestamp,
                        "value": value,
                        "status": status,
                    })
                data_point["sleepInterval"] = randint(0, 5)
                data_points_config["dataPoints"].append(data_point.copy())
                global_count += 1
        return data_points_config
