import docker
import fileinput
import fnmatch
import glob
import ntpath
import os
import shutil
import sys

from pathlib import Path
from sh import cp, mv


class BuildTasks(object):
    def __init__(self, repo_dir, build_dir, deploy_dir, mode=""):
        self.mode = mode
        self.repository_dir = repo_dir
        self.build_dir = build_dir
        self.deploy_dir = deploy_dir
        # NOTE: For usage on agent, we suggest, that USER_HOME dir for docker is parent of repository dir
        self.repo_parent_dir = str(Path(self.repository_dir).parent.absolute())

    @staticmethod
    def _purge(directory, pattern):
        for path in Path(directory).rglob(pattern):
            os.remove(path)

    @staticmethod
    def _separate_ftp_partition(deploy_content_dir):
        os.system("cd " + deploy_content_dir + "/partitions/DEV && zip -r " +
                  deploy_content_dir + "/DEV.zip .")

    def _set_docker_variables(self):
        if os.environ.get("BUILD_ENV") is not None:
            os.system("echo " + os.environ["DOCKER_HUB_PASSWD"] + " | \
                        docker login --username " + os.environ["DOCKER_HUB_LOGIN"] + " --password-stdin")
        file = open(self.repository_dir + "/dev-ops/iks_gateway_work/.env", "w+")
        # NOTE: Here is suggestion, that USER_HOME directory is located in repository parent directory
        file.write("USER_HOME=" + self.repo_parent_dir + "/")
        file.close()

    def _grub_deploy(self):
        sdk_source = os.environ.get("SDK_SOURCE")
        if sdk_source != "repository" and sdk_source is not None:
            template_path = os.environ["ARTIFACTS_DIR"] + "/*APT*/*"
        else:
            template_path = self.repository_dir + "/dev-ops/iks_gateway_common/shell/*"
        for file in glob.glob(template_path):
            if fnmatch.fnmatch(file, "*grub*"):
                deploy_grub_dir = self.deploy_dir + "/grub"
                os.makedirs(deploy_grub_dir, exist_ok=True)
                shutil.copy(file, deploy_grub_dir + "/grub.tar.bz2")

    def _replace_sdk(self):
        new_name = ""
        for file in glob.glob(os.environ["ARTIFACTS_DIR"] + "/*APT*/*"):
            if fnmatch.fnmatch(file, "*.deb"):
                try:
                    new_name = file.replace("-001_", "-001-")
                    os.rename(file, new_name)
                    new_name = new_name.replace("amd64-release", "amd64")
                    os.rename(file, new_name)
                except (ValueError, Exception):
                    pass
        for file in glob.glob(self.repository_dir + "/dev-ops/iks_gateway_common/sdk/*"):
            if fnmatch.fnmatch(file, "*.deb"):
                os.remove(file)
                shutil.copy(new_name, self.repository_dir + "/dev-ops/iks_gateway_common/sdk/")
                dockerfile_path = self.repository_dir + "/dev-ops/iks_gateway_common/sdk/Dockerfile"
                with open(dockerfile_path) as search:
                    for line in search:
                        line = line.rstrip()
                        if "ENV KOS_SDK_NAME" in line:
                            old_name = line.split("ENV KOS_SDK_NAME=")[1]
                            new_name = ntpath.basename(new_name).removesuffix("_amd64.deb")
                self._replace_line(dockerfile_path, old_name, new_name)

    def _move_artifacts(self, pipeline):
        artifacts_dir = self.build_dir + "/iks-gateway/" + pipeline + "/products"
        target_dir = self.deploy_dir + "/kos-images/"
        os.makedirs(target_dir, exist_ok=True)
        if self.mode == "hw":
            shutil.copy(artifacts_dir + "/IKS_1000GP/install/kos.img", target_dir)
            shutil.copy(artifacts_dir + "/IKS_1000GP/install/kos-ftp.img", target_dir)
        elif self.mode == "qemu":
            shutil.copy(artifacts_dir + "/IKS_1000GP/build/images/tgw/kos-qemu-image", target_dir + "kos-qemu.img")
            shutil.copy(artifacts_dir + "/IKS_1000GP/build/images/ftp/kos-ftp-qemu-image", target_dir + "kos-qemu-ftp.img")

    @staticmethod
    def run_cmd_container(cmd, output=False, working_dir=""):
        client = docker.from_env()
        for container in client.containers.list(all=True):
            if "iks_gateway_work" in container.name:
                name = container.name
                break
            else:
                raise ValueError("No iks_gateway_work container found!")
        container = client.containers.get(name)
        if output:
            log = container.exec_run(cmd, stream=True, workdir=working_dir)
            for line in log.output:
                print(line.decode("utf-8").rstrip())
            return log
        else:
            container.exec_run(cmd, workdir=working_dir)

    def prepare_venv_container(self):
        repo_prefix = os.path.basename(self.repository_dir)
        if os.environ.get("PIP_EXTRA_INDEX_URL") is not None:
            install_cmd = "pipenv sync --pypi-mirror " + \
                          os.environ.get("PIP_EXTRA_INDEX_URL")
        else:
            install_cmd = "pipenv sync"
        self.run_cmd_container(install_cmd, output=True, working_dir="/home/user/" + repo_prefix)

    @staticmethod
    def _replace_line(file, search_exp, replace_exp):
        for line in fileinput.input(file, inplace=1):
            if search_exp in line:
                line = line.replace(search_exp, replace_exp)
            sys.stdout.write(line)

    def _build_pipeline(self, pipeline):
        repo_prefix_default = "iks-gateway-demo"
        repo_prefix = os.path.basename(self.repository_dir)
        pipeline_dir = "/home/user/" + repo_prefix + "/scripts/pipelines/" + pipeline
        self._replace_line(
            self.repository_dir + "/scripts/pipelines/" + pipeline + "/init-env.example",
            repo_prefix_default, repo_prefix)
        self.run_cmd_container("cp init-env.example init-env", output=True, working_dir=pipeline_dir)
        self.run_cmd_container("bash prepare.sh", output=True, working_dir=pipeline_dir)
        self.run_cmd_container("bash build.sh", output=True, working_dir=pipeline_dir)

    def set_platform(self, interactive_inst):
        if os.environ.get("BUILD_MODE") is None:
            self._set_env_vars_interactive(interactive_inst)
        if os.environ["BUILD_MODE"] == "linux":
            platform = os.environ["BUILD_MODE"]
        else:
            platform = "kos-" + self.mode
        if os.environ["BUILD_MODE"] in ["default", "linux"]:
            pipeline = platform
        else:
            pipeline = platform + "-" + os.environ["BUILD_MODE"]
        return pipeline

    def _set_env_vars_interactive(self, interactive_inst):
        if self.mode != "linux":
            interactive_inst.build_mode()
        else:
            os.environ["BUILD_MODE"] = self.mode

    def prepare(self):
        if os.environ.get("BUILD_ENV") is not None:
            if os.environ["SDK_SOURCE"] != "repository":
                self._replace_sdk()
        self._grub_deploy()
        self._set_docker_variables()
        deploy_content_dir = self.deploy_dir + "/content"
        os.makedirs(deploy_content_dir, exist_ok=True)
        cp("-r", self.repository_dir + "/examples/partitions",
           deploy_content_dir + "/partitions")
        self._purge(deploy_content_dir + "/partitions", ".gitkeep")
        self._separate_ftp_partition(deploy_content_dir)
        os.system("cd " + deploy_content_dir + "/ && zip -r " +
                  deploy_content_dir + "/partitions.zip partitions/ -x 'partitions/DEV/*'")

    def build(self, interactive_inst):
        if os.environ.get("BUILD_ENV") is None:
            self._set_env_vars_interactive(interactive_inst)
        else:
            self.run_cmd_container("pip3 config set global.trusted-host extrndtfs.kaspersky.com")
        pipeline = self.set_platform(interactive_inst)
        self._build_pipeline(pipeline)
        self.prepare_venv_container()
        if self.mode != "linux":
            self._move_artifacts(pipeline)

    def clean(self):
        # Cleaning environment locally is dangerous
        if os.environ.get("BUILD_ENV") is None:
            print("Cleaning environment is dangerous on local machine, aborting")
            return
        os.system("docker system prune -a -f")
        if Path(os.environ.get("ARTIFACTS_DIR")).exists():
            shutil.rmtree(os.environ.get("ARTIFACTS_DIR"))
        if self.mode == "final":
            shutil.rmtree(self.repository_dir)
        if Path(self.build_dir).exists():
            shutil.rmtree(self.build_dir)
        if Path(self.deploy_dir).exists():
            shutil.rmtree(self.deploy_dir)
        os.system("df -h; du -h / | sort -h | tail -n 30")
        os.system("journalctl --disk-usage")
