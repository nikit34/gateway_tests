import os
import re
from sh import losetup, mktemp, mount, truncate, umount


class TemporaryDirectory(object):
    def __enter__(self):
        self.temporary_directory = str(mktemp("-d")).rstrip()
        return self

    def __exit__(self, *exc_details):
        os.system("find " + self.temporary_directory + " -delete")


class MountPoint(object):
    def __init__(self, dest_dev, directory):
        self.destination = dest_dev
        self.directory = directory

    def __enter__(self):
        mount(self.destination, self.directory)
        return self

    def __exit__(self, *exc_details):
        umount(self.directory)


class ImageGenerator(object):
    def __init__(self, tmp_dir, size, name):
        self.directory = tmp_dir
        self.size = size
        self.name = name

    def __enter__(self):
        self.target = self.directory + "/" + self.name
        truncate("-s", self.size, self.target)
        return self

    def __exit__(self, *exc_details):
        os.system("rm " + self.target)


class LoopDevice(object):
    def __init__(self, target):
        self.target = target

    def __enter__(self):
        self.device = losetup("-f", "--show", self.target).strip()
        return self

    def __exit__(self, *exc_details):
        losetup("-d", self.device)
        print("Device " + self.device + " successfully unmounted")
