from .requests_wrapper import RequestsWrapper


class AspectsManager(object):
    def __init__(self, fixture_obj, aspect_name=None):
        self.wrapper = RequestsWrapper(aspect_name)
        self.aspect_name = aspect_name
        self.variables = self.fill_aspect_variables(fixture_obj)

    @staticmethod
    def fill_aspect_variables(fixture_obj):
        variables = []
        for data_point in fixture_obj["dataPoints"]:
            aspect_variable = {
                "name": data_point["dataName"],
                "dataType": data_point["dataType"].upper(),
                "unit": "",
                "searchable": "True",
                "qualityCode": "True"
            }
            if data_point["dataType"] == "String":
                aspect_variable["length"] = data_point["maxLength"]
            variables.append(aspect_variable)
        return variables

    def create_aspect(self):
        payload = {
            "name": self.aspect_name,
            "category": "dynamic",
            "scope": "private",
            "description": "SystemTesting",
            "variables": self.variables
        }
        self.wrapper.create_aspect(payload)

    def delete_aspect(self):
        self.wrapper.delete_aspect()
