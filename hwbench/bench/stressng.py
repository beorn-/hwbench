import abc
import pathlib

from ..utils.external import External
from .bench import Bench


class StressNG(External, Bench):
    @abc.abstractmethod
    def __init__(self, out_dir: pathlib.Path, timeout: int, workers: int):
        External.__init__(self, out_dir)
        Bench.__init__(self)
        self.stressor_name = "undefined"
        self.timeout = timeout
        self.workers = workers

    @property
    def name(self) -> str:
        return "stress-ng-" + self.stressor_name

    def run_cmd_version(self) -> list[str]:
        return [
            "stress-ng",
            "--version",
        ]

    def run_cmd(self) -> list[str]:
        args = [
            "stress-ng",
            "--timeout",
            str(self.timeout),
            "--metrics-brief",
        ]
        if self.version_major() >= 16:
            args.insert(1, "--quiet")
        return args

    def parse_version(self, stdout: bytes, _stderr: bytes) -> bytes:
        self.version = stdout.split()[2]
        return self.version

    def version_major(self) -> int:
        if self.version:
            return int(self.version.split(b".")[1])
        return 0

    def parse_cmd(self, stdout: bytes, stderr: bytes):
        inp = stderr
        bogo_idx = 8
        line = -1
        if self.version_major() == 15:
            line = -2
        if self.version_major() >= 16:
            inp = stdout
            line = 2

        # TODO: better parsing than this
        score = float(inp.splitlines()[line].split()[bogo_idx])
        return {
            f"{self.name} bogo ops/s": score,
            "timeout": self.timeout,
            "workers": self.workers,
        }


class StressNGQsort(StressNG):
    def __init__(self, out_dir: pathlib.Path, timeout: int, workers: int):
        super().__init__(out_dir, timeout, workers)
        self.stressor_name = "qsort"

    def run_cmd(self) -> list[str]:
        return super().run_cmd() + [
            "--qsort",
            str(self.workers),
        ]


class StressNGCpu(StressNG):
    def __init__(self, out_dir: pathlib.Path, timeout: int, workers: int, method: str):
        super().__init__(out_dir, timeout, workers)
        self.method = method
        self.stressor_name = "cpu-" + method

    def run_cmd(self) -> list[str]:
        return super().run_cmd() + [
            "--cpu",
            str(self.workers),
            "--cpu-method",
            self.method,
        ]
