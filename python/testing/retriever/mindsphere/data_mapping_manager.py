from .requests_wrapper import RequestsWrapper


class DataMappingManager(object):
    def __init__(self, variables, asset_id=None):
        self.asset_id = asset_id
        self.wrapper = RequestsWrapper(artifact_name=None, asset=None, eTag=None, asset_id=None)
        self.variables = variables
        self.dp_map = []

    def map_datapoints(self, target_asset_id, target_asset_name):
        for var in self.variables:
            payload = {
                "agentId": self.asset_id,
                "dataPointId": var["id"],
                "entityId": target_asset_id,
                "propertySetName": target_asset_name,
                "propertyName": var["name"],
                "keepMapping": "true"
            }
            self.dp_map.append(self.wrapper.map_datapoints(payload).json()["id"])

    def delete_datamappings(self):
        for map_id in self.dp_map:
            self.wrapper = RequestsWrapper(map_id, asset=True)
            self.wrapper.delete_map()
