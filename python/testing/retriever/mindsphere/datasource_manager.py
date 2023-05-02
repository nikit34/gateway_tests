import json

from .requests_wrapper import RequestsWrapper


class DataSourceManager(object):
    def __init__(self, variables, asset_id=None):
        self.artifact_name = asset_id + "/dataSourceConfiguration"
        self.eTag = None
        self.asset_id = asset_id
        self.configuration_id = None
        self.wrapper = RequestsWrapper(self.artifact_name, asset=True, eTag=self.eTag, asset_id=self.asset_id)
        self.variables = self._create_ds_vars(variables)

    @staticmethod
    def _create_ds_vars(variables):
        ds_vars = []
        for variable in variables:
            item = {
                "id": variable["name"],
                "name": variable["name"],
                "description": "",
                "type": variable["dataType"].upper(),
                "unit": ""
            }
            ds_vars.append(item)
        return ds_vars

    def get_datasource_id_etag(self):
        result = self.wrapper.read_datasource().json()
        self.eTag = result["eTag"]
        self.configuration_id = result["configurationId"]
        self.wrapper = RequestsWrapper(self.artifact_name, asset=True, eTag=self.eTag, asset_id=self.asset_id)
        return self.configuration_id

    def delete_datasource(self):
        payload = {
            "configurationId": self.configuration_id,
            "dataSources": []
        }
        return self.wrapper.delete_datasource(payload)

    def create_datasource(self):
        payload = {"configurationId": "SystemTestConfig",
                   "dataSources": [
                       {
                           "name": "SystemTestDataSource",
                           "description": "Testing remote access",
                           "dataPoints": self.variables
                       }
                   ]
                   }
        result = self.wrapper.create_datasource(payload)
        self.eTag = result.json()["eTag"]
        self.wrapper = RequestsWrapper(self.artifact_name, asset=True, eTag=self.eTag, asset_id=self.asset_id)
