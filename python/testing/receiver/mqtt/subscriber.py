import ast
import subprocess


class Subscriber:
    def __init__(self, host, topic="#"):
        self.subprocess_superuser = subprocess.Popen(['echo', '1'], stdout=subprocess.PIPE)
        self.template_subscriber_run = ["sudo", "-S", "mosquitto_sub", "-h", host, "-t", topic]
        self.proc = None
        self.output = None

    def start(self):
        self.proc = subprocess.Popen(
            self.template_subscriber_run,
            stdin=self.subprocess_superuser.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if self.proc.poll() is not None:
            raise subprocess.SubprocessError("Mosquitto subscriber is not running")

    def save_accepted(self):
        output = self.get_accepted()
        raw_lines = output.split("\n")
        lines = [dict(ast.literal_eval(line)[0]) for line in raw_lines[:-1]]
        with open("logs/mqtt.log", "w") as file:
            file.write(",".join(lines[0].keys()) + "\n")
            for line in lines:
                write_line = ",".join(line.values())
                file.write(write_line + "\n")

    def get_accepted(self):
        if self.output is None:
            self.output, err = self.proc.communicate()
            if self.output == b"" or (err != b"" and b"[sudo] password" not in err):
                self.stop()
                raise ValueError(f"Output was not received - output: {self.output}, err: {err}")
        return self.output.decode("utf-8")

    def _run_ps_aux(self):
        return subprocess.Popen(
            ["sudo", "-S", "ps", "aux"],
            stdin=self.subprocess_superuser.stdout,
            stdout=subprocess.PIPE
        )

    @staticmethod
    def _get_awk_out(proc_ps_aux, index_print):
        raw_awk_out = subprocess.Popen(
            ["awk", "/mosquitto_sub/ {print $" + str(index_print) + "}"],
            stdin=proc_ps_aux.stdout,
            stdout=subprocess.PIPE
        ).stdout.readlines()
        return raw_awk_out

    @staticmethod
    def _clean_out(outs):
        return [out.decode().rstrip() for out in outs]

    def _select_broker_pid(self, awk_pids_out, awk_names_out):
        try:
            select_broker_index = awk_names_out.index("mosquitto_sub")
        except ValueError:
            self.stop()
            raise ValueError("Processes of MQTT subscriber not found")
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
            raise subprocess.SubprocessError("Mosquitto subscriber is not killed")

