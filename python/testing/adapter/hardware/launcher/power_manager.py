from time import sleep

from .connection import Manager


class PowerManager(Manager):
    def __init__(self, fixture_obj):
        super().__init__(fixture_obj=fixture_obj)

    @Manager.check_connect(connecting=True, disconnecting=False)
    def turn_on(self):
        self.interfaces.set(id=self.eth[0]["id"], poe_out="forced-on")

    @Manager.check_connect(connecting=True, disconnecting=True)
    def turn_off(self):
        self.interfaces.set(id=self.eth[0]["id"], poe_out="off")

    @Manager.check_connect(connecting=False, disconnecting=False)
    def reset(self, manual_switching=False):
        self.interfaces.set(id=self.eth[0]["id"], poe_out="off")
        if manual_switching:
            input("[MANUAL] Switch power cable manually")
        sleep(self.connection.reset_interval)
        self.interfaces.set(id=self.eth[0]["id"], poe_out="forced-on")
