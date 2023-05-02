import fnmatch
import ntpath
import os

from pathlib import Path
from sh import cp, mkdir


class ImageManager(object):
    @staticmethod
    def check_grub(grub, kos):
        if Path(grub).is_file():
            with open(grub, "r+") as grub_file:
                grub_lines = grub_file.readlines()
        else:
            raise FileNotFoundError
        for line in grub_lines:
            if ntpath.basename(kos) in line:
                return True
        return False

    @staticmethod
    def update_grub(grub, kos, entry):
        with open(grub, "a") as grub_file:
            grub_file.write("\n")
            grub_file.write("menuentry --hotkey=f '" + entry + "' {\n")
            grub_file.write("    set background_color=black\n")
            grub_file.write("    multiboot (hd0,msdos1)/boot/images/" + ntpath.basename(kos) + "\n")
            grub_file.write("}\n")

    @staticmethod
    def grub_remove_entry(grub, entry):
        if Path(grub).is_file():
            with open(grub, "r+") as grub_file:
                grub_lines = grub_file.readlines()
            for i, line in enumerate(grub_lines):
                if entry in line:
                    grub_lines[i-1].rstrip("\n")
                    del grub_lines[i:i + 5]
                    break
            with open(grub, "w+") as grub_file:
                grub_file.truncate()
                grub_file.writelines(grub_lines)

    def add_image(self, kos, entry, mnt_directory):
        grub_file = mnt_directory + "/boot/grub/grub.cfg"
        # Create directory for images
        mkdir("-p", mnt_directory + "/boot/images")
        try:
            cp(kos, mnt_directory + "/boot/images")
        except FileNotFoundError:
            print("Wrong file or file path")
        if not self.check_grub(grub_file, kos):
            self.update_grub(grub_file, kos, entry)

    def delete_image(self, kos, entry, mnt_directory):
        grub_file = mnt_directory + "/boot/grub/grub.cfg"
        for rootDir, subdirs, filenames in os.walk(mnt_directory):
            for filename in fnmatch.filter(filenames, kos):
                try:
                    os.remove(os.path.join(rootDir, filename))
                except OSError:
                    return "Error while deleting file"
        if self.check_grub(grub_file, kos):
            self.grub_remove_entry(grub_file, entry)
