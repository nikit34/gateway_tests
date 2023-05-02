import subprocess
from threading import Thread

from scripts.hardware.ftp_client import FTPClient


class FTPClientMultiThreaded(FTPClient):
    threads = []

    def __init__(self, count_threads=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.count_threads = count_threads
        self._check_threads_count_support()
        self.args = args
        self.kwargs = kwargs

    def __enter__(self):
        return self

    @staticmethod
    def get_limit_threads_max():
        output = subprocess.check_output(["cat", "/proc/sys/kernel/threads-max"])
        return int(output.decode(encoding="utf-8"))

    def _check_threads_count_support(self):
        if 0 < self.count_threads < self.get_limit_threads_max():
            self.threads = [FTPClientThread] * self.count_threads
        else:
            raise SystemError("Number of threads requested to be created is beyond OS support")

    def _create_more_threads(self, args):
        for i in range(self.count_threads):
            self.threads[i] = self.threads[i](FTPClient, args[i], self.args, self.kwargs)
            if not self.threads[i].is_alive():
                self.threads[i].start()

    def write_on_server_more(self, client_names, server_names):
        count_files_per_thread, count_files_add_thread = divmod(len(client_names), self.count_threads)
        if count_files_per_thread:
            args = [(None, None)] * self.count_threads
            for i in range(self.count_threads):
                first_index = i * count_files_per_thread
                second_index = first_index + count_files_per_thread
                send_client_names = client_names[first_index: second_index]
                send_server_names = server_names[first_index: second_index]
                args[i] = send_client_names, send_server_names
                self.threads[i].name_callback = "write_on_server_more"
            if count_files_add_thread:
                for i in range(self.count_threads):
                    args[i] = args[i][0] + [client_names[-count_files_add_thread]], \
                              args[i][1] + [server_names[-count_files_add_thread]]
                    count_files_add_thread -= 1
        elif count_files_add_thread:
            print("Number of threads created exceeds number files sent")
            args = [(None, None)] * count_files_add_thread
            for i in range(self.count_threads):
                if i < count_files_add_thread:
                    args[i] = [client_names[i]], [server_names[i]]
                    self.threads[i].name_callback = "write_on_server_more"
                else:
                    del self.threads[count_files_add_thread]
            self.count_threads = count_files_add_thread
        else:
            raise ValueError("No files to send")
        self._create_more_threads(args)

    def stop(self):
        for i in range(len(self.threads)):
            if self.threads[i].is_alive():
                self.threads[i].join()

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()


class FTPClientThread(Thread):
    def __init__(self, ftp, arg_callback, args, kwargs):
        Thread.__init__(self)
        self.ftp = ftp(*args, **kwargs)
        self.arg_callback = arg_callback

    def run(self):
        callback = getattr(self.ftp, self.name_callback)
        callback(*self.arg_callback)

