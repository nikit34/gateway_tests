from .requests_wrapper import RequestsWrapper


class AssetsManager(object):
    def __init__(self, type_name=None, asset_id=None):
        if type_name is not None:
            self.type_name = "aprotech." + type_name
        self.asset_id = asset_id
        self.wrapper = RequestsWrapper(asset_id, asset=True)

    def get_asset_id_by_name(self, name):
        fltr = {'filter': "{\"name\":\"" + name + "\"}"}
        return self.wrapper.read_asset(fltr).json()["_embedded"]["assets"][0]["assetId"]

    def create_asset(self, parent_id, name):
        payload = {
            'name': name,
            'externalId': '',
            'description': 'SystemTestAsset',
            'typeId': self.type_name,
            'parentId': parent_id,
            'timezone': 'Europe/Berlin',
            'twinType': 'performance'}
        self.asset_id = self.wrapper.create_asset(payload).json()["assetId"]
        self.wrapper = RequestsWrapper(self.asset_id, asset=True)
        return self.asset_id

    def delete_asset(self):
        self.wrapper = RequestsWrapper(self.asset_id, asset=True)
        self.wrapper.delete_asset()

    def generate_onb(self, mcl_id):
        self.wrapper = RequestsWrapper(mcl_id, asset=True, onb=True)
        self.wrapper.offboard_mcl_asset()
        self.wrapper = RequestsWrapper(mcl_id, asset=True, onb=True, onboard=True)
        return self.wrapper.generate_config().json()
