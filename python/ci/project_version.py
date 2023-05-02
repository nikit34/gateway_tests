import datetime
import os
import re
import subprocess

from typing import Any, Dict, List, Optional, Tuple, Union


class Version:
    # TODO: Remove strong coupling with git tool and env variables via DI for unit tests.
    __GIT_GET_COMMIT = "git rev-parse HEAD"
    __GIT_DESCRIBE_COMMIT = "git describe --dirty --tags --long --match=*v*.* --first-parent"

    def __init__(self):
        # TODO: Check whether both git tool and git folder are available. Handle situation when there are no suitable
        # git tags were found. Expected output: "<tag>-<ahead>-g<sha>[-dirty]".
        description = Version.__run_cmd(Version.__GIT_DESCRIBE_COMMIT.split())

        self.__number = Version.__parse_number(description)
        self.__pre_release = Version.__parse_pre_release(description)
        self.__is_next = Version.__parse_next_mark(description)
        self.__is_dirty = Version.__parse_dirty_mark(description)
        self.__build_date = datetime.datetime.today()
        self.__git_sha = Version.__run_cmd(Version.__GIT_GET_COMMIT.split())
        self.__git_short_sha = Version.__parse_short_sha(description)
        self.__build_id = Version.__validate_env(os.getenv("BUILD_BUILDID"), to_type=int)
        self.__label = Version.__validate_env(os.getenv("BUILD_LABEL"))

        assert type(self.__number) is tuple and len(self.__number) == 3
        assert type(self.__number[0]) is int and \
               type(self.__number[1]) is int and \
               type(self.__number[2]) is int
        assert type(self.__pre_release) is str or (self.__pre_release is None)
        assert type(self.__is_next) is bool
        assert type(self.__is_dirty) is bool
        assert type(self.__build_date) is datetime.datetime
        assert type(self.__git_sha) is str or (self.__git_sha is None)
        assert type(self.__git_short_sha) is str or (self.__git_short_sha is None)
        assert type(self.__build_id) is int or (self.__build_id is None)
        assert type(self.__label) is str or (self.__label is None)

        self.__full = Version.__define_full_version(
            number=self.__number,
            pre_release=self.__pre_release,
            is_next=self.__is_next,
            is_dirty=self.__is_dirty,
            build_date=self.__build_date,
            git_short_sha=self.__git_short_sha,
            build_id=self.__build_id,
            label=self.__label)

        assert type(self.__full) is str and len(self.__full.strip()) > 0

    def __str__(self) -> str:
        return self.full

    @staticmethod
    def __run_cmd(what: List[str]) -> str:
        return subprocess.check_output(what).strip().decode()

    @staticmethod
    def __validate_env(value: Optional[str],
                       to_type: Union[int, str] = str) -> Optional[Union[int, str]]:
        stripped = value and value.strip()
        return to_type(stripped) if stripped else None

    # FIXME: Construct single regex to minimize amount of calls to "re" module.

    @staticmethod
    def __parse_number(description: str) -> Tuple[int, int, int]:
        major, minor, patch = (0, 0, 0)
        found = re.search("v(\\d+)\\.(\\d+)(\\.(\\d+))?", description)
        if found:
            major, minor, patch = found.group(1, 2, 4)
        return (int(major),
                int(minor),
                int(patch) if patch else 0)

    @staticmethod
    def __parse_pre_release(description: str) -> Optional[str]:
        found = re.search("-([0-9A-Za-z\\-\\.]+)-\\d+-g", description)
        return found and found.group(1)

    @staticmethod
    def __parse_next_mark(description: str) -> bool:
        found = re.search("-(\\d+)-g", description)
        return bool(found and int(found.group(1)) > 0)

    @staticmethod
    def __parse_dirty_mark(description: str) -> bool:
        found = re.search("-dirty", description)
        return bool(found)

    @staticmethod
    def __parse_short_sha(description: str) -> Optional[str]:
        found = re.search("-\\d+-g([0-9a-f]+)", description)
        return found and found.group(1)

    @staticmethod
    def __define_full_version(**parts: Dict[str, Optional[Any]]) -> str:
        version = ".".join([str(itm) for itm in parts["number"]])
        if parts["pre_release"]:
            version += "-" + parts["pre_release"]
        version += "+"
        metadata = (
            "next" if parts["is_next"] else None,
            "dirty" if parts["is_dirty"] else None,
            f"date-{parts['build_date'].strftime('%Y%m%d')}",
            f"git-{parts['git_short_sha'] if parts['git_short_sha'] else 'unknown'}",
            f"id-{parts['build_id'] if parts['build_id'] else 0}",
            parts["label"])
        version += ".".join(filter(None, metadata))
        return version

    @property
    def major(self) -> int:
        return self.__number[0]

    @property
    def minor(self) -> int:
        return self.__number[1]

    @property
    def patch(self) -> int:
        return self.__number[2]

    @property
    def number(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def pre_release(self) -> Optional[str]:
        return self.__pre_release

    @property
    def is_next(self) -> bool:
        return self.__is_next

    @property
    def build_date(self) -> datetime.datetime:
        return self.__build_date

    @property
    def git_sha(self) -> str:
        return self.__git_sha

    @property
    def git_short_sha(self) -> str:
        return self.__git_short_sha

    @property
    def build_id(self) -> Optional[int]:
        return self.__build_id

    @property
    def label(self) -> Optional[str]:
        return self.__label

    @property
    def is_dirty(self) -> bool:
        return self.__is_dirty

    @property
    def full(self) -> str:
        return self.__full
