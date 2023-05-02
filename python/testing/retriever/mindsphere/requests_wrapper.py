import base64

from .requests_manager import Request


def generate_auth_key():
    app_id = "aprotech-qateamapp-v1.0.0"
    app_token = "KZdCXo7N9NCk0s30I6899s7kCtjD3ZTkQfyy6UpYVrx"
    message = app_id + ":" + app_token
    message_bytes = message.encode("ascii")
    base64_bytes = base64.b64encode(message_bytes)
    return base64_bytes.decode("ascii")


base64_message = generate_auth_key()


class RequestsWrapper(object):
    def __init__(self, artifact_name=None, asset=False, eTag=None, asset_id=None, onb=False, onboard=False):
        self.host = "gateway.eu1.mindsphere.io"
        self.token = self._get_token({
            "appName": "qateamapp",
            "appVersion": "v1.0.0",
            "hostTenant": "aprotech",
            "userTenant": "aprotech"
        }).json()["access_token"]
        if artifact_name is not None:
            if not asset:
                self.artifact_name = "aprotech." + artifact_name
            else:
                self.artifact_name = artifact_name
        if eTag is not None and asset_id is not None:
            self.eTag = eTag
            self.asset_id = asset_id
        self.onb = onb
        self.onboard = onboard

    @Request(method="POST", path="api/technicaltokenmanager/v3/oauth/token",
             headers={"X-SPACE-AUTH-KEY": "Basic " + base64_message})
    def _get_token(self, data):
        return data

    @Request(method="GET", path="api/assetmanagement/v3/assets")
    def read_asset(self, fltr):
        return fltr

    @Request(method="PUT", path="api/assetmanagement/v3/aspecttypes")
    def create_aspect(self, payload):
        return payload

    @Request(method="DELETE", path="api/assetmanagement/v3/aspecttypes", headers={'If-Match': '0'})
    def delete_aspect(self):
        pass

    @Request(method="PUT", path="api/assetmanagement/v3/assettypes")
    def create_type(self, payload):
        return payload

    @Request(method="DELETE", path="api/assetmanagement/v3/assettypes", headers={'If-Match': '0'})
    def delete_type(self):
        pass

    @Request(method="POST", path="api/assetmanagement/v3/assets")
    def create_asset(self, payload):
        return payload

    @Request(method="DELETE", path="api/assetmanagement/v3/assets", headers={'If-Match': '0'})
    def delete_asset(self):
        pass

    @Request(method="GET", path="api/agentmanagement/v3/agents")
    def read_datasource(self):
        pass

    @Request(method="PUT", path="api/agentmanagement/v3/agents")
    def delete_datasource(self, payload):
        return payload

    @Request(method="PUT", path="api/agentmanagement/v3/agents")
    def create_datasource(self, payload):
        return payload

    @Request(method="POST", path="api/mindconnect/v3/dataPointMappings")
    def map_datapoints(self, payload):
        return payload

    @Request(method="DELETE", path="api/mindconnect/v3/dataPointMappings")
    def delete_map(self):
        pass

    @Request(method="POST", path="api/agentmanagement/v3/agents")
    def offboard_mcl_asset(self):
        pass

    @Request(method="GET", path="api/agentmanagement/v3/agents")
    def generate_config(self):
        pass

    @Request(method="GET", path="api/iottimeseries/v3/timeseries", headers={'Accept': 'application/json'})
    def get_timeseries(self, payload):
        return payload
