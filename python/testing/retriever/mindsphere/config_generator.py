class ConfigGenerator(object):
    def __init__(self, data_points, onb, datasource_id, cfg_path):
        self.data_points = data_points
        self.onb = onb
        self.datasource_id = datasource_id
        self.cfg_path = cfg_path

    def generate_ms_agent_config(self):
        dps = []
        for i, dp in enumerate(self.data_points):
            dps.append({
                "id": i,
                "name": dp["name"],
                "dataPointId": dp["id"]
            })
        ms_config = {
            "id": 0,
            "name": "Gateway_Automation (Peteris)",
            "description": "Gateway_Automation (Peteris)",
            "boardingConfiguration": self.onb,
            "configurationId": self.datasource_id,
            "limits": {
                "maxStorageSize": 90000,
                "itemGroupTimeout": 5,
                "maxTimeseriesSize": 64,
                "maxHttpPayloadSize": 16384
            },
            "dataPoints": dps
        }
        return ms_config

    def generate_transfer_config(self):
        dps = []
        for i in range(len(self.data_points)):
            dps.append({
                "sourcePortId": i,
                "targetPortId": i
            })
        guide_cfg = {
            "id": 0,
            "receivingHubId": 0,
            "receivingHubType": "OPC UA Client",
            "sendingHubId": 0,
            "sendingHubType": "MindSphere Agent",
            "roadmap": dps
        }
        return guide_cfg
