from .requests_wrapper import RequestsWrapper


class TimeseriesManager(object):
    def __init__(self, aspects_variables, asset_id, aspect_name):
        self.aspects_variables = aspects_variables
        self.asset_id = asset_id
        self.aspect_name = aspect_name
        self.wrapper = RequestsWrapper(self.asset_id + "/" + self.aspect_name, asset=True)

    def get_values(self, var, start_time, end_time):
        payload = {
            "select": var + \
                "&from=" + start_time.strftime("%Y-%m-%dT%H:%M:%SZ") + \
                "&to=" + end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        return self.wrapper.get_timeseries(payload).json()

    def save_values(self, start_time, end_time):
        data_types = set()
        for var in self.aspects_variables:
            ms_values = self.get_values(var["name"], start_time, end_time)
            for ms_value in ms_values:
                timestamp = ""
                status = ""
                value = ""
                f_name = ""
                f_mode = ""
                for k, v in ms_value.items():
                    if "_time" in k:
                        timestamp = v
                    elif "_qc" in k:
                        status = v
                    else:
                        value = v
                        if k in data_types:
                            f_mode = "a"
                        else:
                            f_mode = "w"
                            data_types.add(k)
                        f_name = k
                with open(f"logs/{f_name}_ms.log", f_mode) as f:
                    f.write(str(status) + "," + str(value) + "," + str(timestamp) + "\n")
