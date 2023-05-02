import json

from .requests_wrapper import RequestsWrapper


class TypesManager(object):
    def __init__(self, aspect_name=None, type_name=None):
        self.wrapper = RequestsWrapper(type_name)
        self.type_name = type_name
        self.aspect_name = aspect_name

    def create_type(self):
        payload = {
            "name": self.type_name,
            "description": "Test type for system test",
            "parentTypeId": "core.basicasset",
            "scope": "private",
            "aspects": [{
                "name": self.aspect_name,
                "aspectTypeId": "aprotech." + self.aspect_name
            }]
        }
        self.wrapper.create_type(payload)

    def delete_type(self):
        self.wrapper.delete_type()
