import subprocess


def get_serial_address():
    last_output = output = None
    for i in range(10):
        try:
            output = subprocess.check_output(["ls", "/dev/ttyUSB" + str(i)])
        except subprocess.CalledProcessError:
            if last_output == output:
                continue
        if last_output is not None:
            raise ConnectionError("Multiple connected devices found")
        last_output = output
    if last_output is None:
        raise ConnectionError("No connected device found")
    return last_output.decode("ascii").rstrip("\n")
