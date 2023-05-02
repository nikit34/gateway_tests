import sys
import os


class Interactive(object):

    @staticmethod
    def query_yes_no(question, default="yes"):
        valid = {"yes": True, "y": True, "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)
        while True:
            sys.stdout.write(question + prompt)
            choice = input().lower()
            if default is not None and choice == "":
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

    @staticmethod
    def build_mode():
        build_mode = input("BUILD_MODE environment variable not set, choose one of [default/production]: ")
        while build_mode not in ["default", "production"]:
            build_mode = input("BUILD_MODE environment variable not set, choose one of [default/production]: ")
        os.environ["BUILD_MODE"] = build_mode
