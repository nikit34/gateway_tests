import ci.resource_manager
import os
import re

from sh import chown, cp, mkdir, tar, unzip


class ContentManager(object):
    @staticmethod
    def unpack_files(files, tmp_dir):
        if re.search(".zip$", files):
            unzip(files, "-d", tmp_dir)
        else:
            cp("-r", files, tmp_dir)

    @staticmethod
    def change_owner(owner, tmp_dir):
        try:
            chown("-R", owner + ":" + owner, tmp_dir + "/")
        except Exception:
            pass

    @staticmethod
    def copy_files(source, target):
        cp("-r", source, target)

    @staticmethod
    def deploy_grub(grub, files, mnt_dir):
        with ci.resource_manager.TemporaryDirectory() as grub_tmp_inst:
            grub_files = grub_tmp_inst.temporary_directory
            mkdir("-p", grub_files + "/grub_feed")
            tar("-xf", grub, "-C", grub_files + "/grub_feed")
            try:
                os.system("cd " + grub_files + "/grub_feed/sbin/ && ./grub-install --force --boot-directory="
                          + mnt_dir + "/boot --directory=" + grub_files +
                          "/grub_feed/lib/grub/i386-efi/ --efi-directory=" + mnt_dir +
                          " --target=i386-efi --removable " + mnt_dir)
            except Exception:
                raise RuntimeError("Failed to install grub to target")
            # Move grub.cfg to destination
            cp(files + "/partitions/BOOT/grub/grub.cfg", mnt_dir + "/boot/grub/")

    @staticmethod
    def configure_logger(mode, location):
        with open(location + "/.log", "r+") as logfile:
            logfile.seek(0)
            logfile.truncate()
            if mode == "hw":
                logfile.write("LogFileSizeLimit=50000000\n")
                logfile.write("DirectorySizeLimit=1750000000\n")
            else:
                logfile.write("LogFileSizeLimit=1000000\n")
                logfile.write("DirectorySizeLimit=50000000\n")
