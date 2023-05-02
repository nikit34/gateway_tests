from functools import reduce
import json
import operator


class EditorConfig:
    def __init__(self, fixtures_path, name_edit):
        self.fixtures_path = fixtures_path
        self.name_edit = name_edit

    @staticmethod
    def delete_field(data, check_fields):
        value_field = reduce(operator.getitem, check_fields, data)
        if len(check_fields) == 1:
            del data[check_fields[0]]
        else:
            del reduce(operator.getitem, check_fields[:-1], data)[check_fields[-1]]
        return data, value_field

    def _find_item(self, data, check_fields):
        if check_fields in data:
            return data[check_fields]
        for k, v in data.items():
            if isinstance(v, dict):
                item = self._find_item(v, check_fields)
                if item is not None:
                    return item

    def setup_field(self, data, check_fields, value_field):
        old_field = self._find_item(data, check_fields[-1])
        if len(check_fields) == 1:
            data[check_fields[0]] = value_field
        else:
            reduce(operator.getitem, check_fields[:-1], data)[check_fields[-1]] = value_field
        return data, old_field

    def edit_config(self, name_callback, *args):
        map_callback = {
            "setup_field": self.setup_field,
            "delete_field": self.delete_field
        }
        with open(self.fixtures_path + self.name_edit, "r+") as file:
            data = json.load(file)
            data, out = map_callback[name_callback](data, *args)
            file.seek(0)
            json.dump(data, file, indent=4)
            file.truncate()
        return out


