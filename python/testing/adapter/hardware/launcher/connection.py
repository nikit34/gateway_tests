from routeros_api import RouterOsApiPool


class Creator(RouterOsApiPool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.interface = None
        self.resource = None
        self.reset_interval = 0.1
        self.api = None

    def get_resource_api(self):
        self.api = self.get_api()
        return self.api.get_resource(self.resource)

    def get_interface(self, interfaces):
        return interfaces.get(name=self.interface)


class Manager:
    def __init__(self, fixture_obj):
        self.fixture_obj = fixture_obj
        self.connection = None
        self.interfaces = None
        self.eth = None

    def apply_configuration(self):
        connection = Creator(
            self.fixture_obj["ip_address"],
            username=self.fixture_obj["username"], password=self.fixture_obj["password"],
            plaintext_login=self.fixture_obj["plaintext_login"],
            use_ssl=self.fixture_obj["use_ssl"], ssl_verify=self.fixture_obj["ssl_verify"],
            ssl_verify_hostname=self.fixture_obj["ssl_verify_hostname"]
        )
        connection.resource = self.fixture_obj["resource"]
        connection.reset_interval = self.fixture_obj["reset_interval"]
        connection.interface = self.fixture_obj["interface"]
        return connection

    def set_connection(self, connecting):
        self.connection = self.apply_configuration()
        if connecting:
            self.interfaces = self.connection.get_resource_api()
            self.eth = self.connection.get_interface(self.interfaces)

    @staticmethod
    def check_connect(connecting, disconnecting):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                self.set_connection(connecting)
                res_func = func(self, *args, **kwargs)
                if disconnecting:
                    self.connection.disconnect()
                return res_func
            return wrapper
        return decorator

    @staticmethod
    def lazy_check_connect(connecting, disconnecting):
        def decorator(func):
            def wrapper(self, *args, **kwargs):
                self.set_connection(connecting)
                yield from func(self, *args, **kwargs)
                if disconnecting:
                    self.connection.disconnect()
            return wrapper
        return decorator
