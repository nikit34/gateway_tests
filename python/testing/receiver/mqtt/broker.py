import subprocess


class Broker:
    def __init__(self, config="/etc/mosquitto/mosquitto.conf"):
        self.subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
        self.template_broker_run = [
            "sudo",
            "-S",
            "mosquitto",
            "-c",
            config
        ]
        self.proc = None

    def start(self):
        self.proc = subprocess.Popen(
            self.template_broker_run,
            stdin=self.subprocess_superuser.stdout
        )
        if self.proc.poll() is not None:
            raise subprocess.SubprocessError("Mosquitto broker is not running")

    def _run_ps_aux(self):
        return subprocess.Popen(
            ["ps", "aux"],
            stdin=self.subprocess_superuser.stdout,
            stdout=subprocess.PIPE
        )

    @staticmethod
    def _get_awk_out(proc_ps_aux, index_print):
        raw_awk_out = subprocess.Popen(
            ["awk", "/mosquitto/ {print $" + str(index_print) + "}"],
            stdin=proc_ps_aux.stdout,
            stdout=subprocess.PIPE
        ).stdout.readlines()
        return raw_awk_out

    @staticmethod
    def _clean_out(outs):
        return [out.decode().rstrip() for out in outs]

    @staticmethod
    def _select_broker_pid(awk_pids_out, awk_names_out):
        try:
            select_broker_index = awk_names_out.index("mosquitto")
        except ValueError:
            print("Processes of MQTT broker not found")
            raise
        return awk_pids_out[select_broker_index]

    def stop(self):
        raw_awk_pids_out = self._get_awk_out(self._run_ps_aux(), 2)
        raw_awk_names_out = self._get_awk_out(self._run_ps_aux(), 11)
        awk_pids_out = self._clean_out(raw_awk_pids_out)
        awk_names_out = self._clean_out(raw_awk_names_out)
        broker_pid = self._select_broker_pid(awk_pids_out, awk_names_out)
        broker_stop = [
            "sudo",
            "-S",
            "kill",
            "-9",
            broker_pid
        ]
        proc = subprocess.Popen(
            broker_stop,
            stdin=self.subprocess_superuser.stdout
        )
        if proc.poll() is not None:
            raise subprocess.SubprocessError("Mosquitto broker is not killed")
