import os
import re
import subprocess
import time

from sh import parted, umount


class PartitionManager(object):
    @staticmethod
    def _get_device_suffix(target):
        if target is None or not re.fullmatch("/dev/sd[a-z]", target):
            return "p"
        else:
            return ""

    @staticmethod
    def get_disk_size(target):
        disk_size = int(parted(target,
                               "unit s print").split("Disk " + target + ": ")[1].split("s\nSector size")[0])
        return disk_size

    @staticmethod
    def startup_umount(device):
        # Check if disk partitions mounted
        if os.popen("cat /proc/self/mounts | grep " + device).read() != "":
            try:
                os.system("ls " + device + "?* | xargs -n1 umount -l")
            except Exception:
                raise RuntimeError("Unable to unmount some partitions on " + device)

    def umount_partition(self, device, label):
        # Check if partition is mounted
        partition = self.search_partition_by_label(device, label)
        if os.popen("cat /proc/self/mounts | grep " + partition).read() != "":
            try:
                umount(partition)
            except Exception:
                raise RuntimeError("Unable to unmount partition " + partition)

    def partition_table(self, label, device):
        self.startup_umount(device)
        # Erase disk
        if re.fullmatch("/dev/sd[a-z]", device):
            try:
                os.system("wipefs -a " + device + " 2>&1")
            except Exception:
                raise RuntimeError("Unable to erase partition table on " + device)
        try:
            parted("-s", device, "mklabel", label)
        except Exception:
            raise RuntimeError("Unable to create partition table on " + device)

    def add_partition(self, device, part_num, mk_type, p_type, first, last, label):
        dev_name = device + self._get_device_suffix(device) + part_num
        try:
            parted("-s", device, "mkpart", mk_type, first, last)
            # FIXME: For stable partition setting, we shound use timeout
            time.sleep(0.1)
            if mk_type != "extended":
                if p_type == "ext3":
                    os.system("yes 2>&1 | mkfs.ext3 -L " + label + " " + dev_name)
                elif p_type == "fat":
                    os.system("mkfs.fat -F 32 -n " + label + " " + dev_name)
        except Exception:
            raise RuntimeError("Unable to create partition on " + dev_name)

    def search_partition_by_label(self, device, label):
        suffix = self._get_device_suffix(device)
        for i in range(1, self.get_last_partition_number(device) + 1):
            if self._check_label(i, device, suffix) == label:
                return device + suffix + str(i)

    @staticmethod
    def _check_label(i, device, suffix):
        disk_label = ""
        try:
            disk_label = subprocess.check_output(["blkid", "-o", "value", "-s", "LABEL",
                                                  device + suffix + str(i)]).decode().rstrip()
        except:
            pass
        return disk_label

    def get_last_available_sector(self, device, extended=False):
        disk = os.path.basename(os.path.normpath(device))
        suffix = self._get_device_suffix(device)
        last_partition = self.get_last_partition_number(device)
        dev_addr = "cat /sys/block/" + disk + "/" + disk + suffix + str(last_partition)
        start = int(os.popen(dev_addr + "/start").read())
        size = int(os.popen(dev_addr + "/size").read())
        last_available_sector = start + size
        # NOTE: For creation partitions inside extended using increment is nessesary
        if extended:
            last_available_sector += 1
        return last_available_sector

    def get_last_partition_number(self, device):
        suffix = self._get_device_suffix(device)
        disk = os.path.basename(os.path.normpath(device))
        cmd = ["grep", disk, "/proc/partitions"]
        try:
            last_part_num = subprocess.check_output(cmd).decode().rstrip().split("\n")[-1].split(disk)[1]
        except subprocess.CalledProcessError as e:
            raise RuntimeError("command '{}' return with error (code {}): {}".format(e.cmd, e.returncode, e.output))
        if suffix != "":
            return int(last_part_num.replace(suffix, ""))
        return int(last_part_num)

    def delete_partition(self, device, label, number):
        self.umount_partition(device, label)
        os.system("echo rm " + str(number) + " | parted " + device)
