from .connection import Manager


class CommunicationManager(Manager):
    def __init__(self, fixture_obj):
        super().__init__(fixture_obj=fixture_obj)

    @Manager.check_connect(connecting=True, disconnecting=False)
    def get_all_elements(self, **kwargs):
        return self.interfaces.get(**kwargs)

    @Manager.lazy_check_connect(connecting=True, disconnecting=False)
    def call_root_command(self, command: str, params: dict):
        bin_api = self.connection.api.get_binary_resource("/")
        params_converted = {k: bytes(v, "utf8") for k, v in params.items()}
        yield from bin_api.call(command, params_converted)

    @Manager.check_connect(connecting=True, disconnecting=False)
    def check_poe_status(self):
        row_answer = self.get_all_elements(name=self.connection.get_interface(self.interfaces)[0]["name"])
        if len(row_answer) > 1:
            raise ValueError("Multiple network interfaces found by name")
        elif row_answer[0]["poe-out"] == "forced-on":
            return True
        elif row_answer[0]["poe-out"] == "off":
            return False
