import os
import sys
from pathlib import Path


def ci_cd_configurations_path(file=__file__):
    # NOTE: Check script format - bundle version or not. If bundle - use path from sys._MEIPASS variable.
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = scripts_path(file) + "/ci-cd"
    return base_path + "/config"


def scripts_path(file=__file__):
    return repository_path(file) + "/scripts"


def modules_path(file=__file__):
    return repository_path(file) + "/python"


def build_path(file=__file__):
    return str(Path(repository_path(file)).parent.absolute()) + "/build"


def deploy_path(file=__file__):
    # NOTE: Check script format - bundle version or not. If bundle - use current folder instead.
    if getattr(sys, "frozen", False):
        return os.path.abspath(os.getcwd()) + "/deploy/kisg-app-l1"
    else:
        return str(Path(repository_path(file)).parent.absolute()) + "/deploy/kisg-app-l1"


def resources_path(file=None):
    if not file:
        return repository_path(__file__) + "/resources"
    else:
        return os.path.dirname(os.path.abspath(file)) + "/resources"


def repository_path(file=__file__):
    return os.popen("git -C " + os.path.dirname(os.path.abspath(file)) +
                    " rev-parse --show-toplevel 2>/dev/null").read().rstrip()
