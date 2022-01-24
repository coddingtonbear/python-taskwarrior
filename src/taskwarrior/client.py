from __future__ import annotations

import datetime
import os
import subprocess
import uuid
from typing import Any
from typing import Dict
from typing import Iterable
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union
from typing import cast

from pydantic import parse_raw_as
from typing_extensions import Literal

from .exceptions import ClientError
from .exceptions import ClientUsageError
from .exceptions import CommandError
from .exceptions import MultipleObjectsFound
from .exceptions import NotFound
from .task import Task
from .types import DictFilterSpec
from .types import FilterSpec
from .types import StdoutStderr
from .utils import convert_dict_to_override_args


class Client:
    _task_bin: str
    _config_filename: str
    _config_overrides: Dict[str, Any] = {
        "verbose": "nothing",
        "json": {"array": "TRUE", "depends": {"array": "on"}},
        "confirmation": "no",
        "dependency": {
            "confirmation": "no",
        },
        "recurrence": {"confirmation": "no"},
    }

    def __init__(
        self,
        config_filename: Optional[str] = None,
        config_overrides: Optional[Dict[str, Any]] = None,
        task_bin: str = "task",
    ):
        self._task_bin = task_bin
        self._config_filename = (
            config_filename
            or os.getenv("TASKRC", os.path.expanduser("~/.taskrc"))
            or ""
        )
        self._config_overrides.update(config_overrides or {})

        super().__init__()

    def _execute(self, *args: str, stdin: str = "") -> StdoutStderr:
        command = [
            self._task_bin,
            *convert_dict_to_override_args(self._config_overrides),
            *[str(arg) for arg in args if arg],
        ]

        env = os.environ.copy()
        env["TASKRC"] = self._config_filename

        try:
            proc = subprocess.Popen(
                command,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            raw_stdout, raw_stderr = proc.communicate(stdin.encode("utf-8"))
        except FileNotFoundError:
            raise ClientError(
                f"Taskwarrior client at '{self._task_bin}' could not be found."
            )

        stdout = raw_stdout.decode("utf-8", "replace")
        stderr = raw_stderr.decode("utf-8", "replace")

        if proc.returncode != 0:
            raise CommandError(
                command,
                stderr,
                stdout,
                proc.returncode,
            )

        return stdout, stderr

    def import_(self, task: Task) -> StdoutStderr:
        return self._execute("import", stdin=task.json(exclude_unset=True))

    def add(self, task: Task) -> StdoutStderr:
        if task.uuid:
            raise ClientUsageError(
                "Task already has a UUID set.  You may want to use `add` instead."
            )

        task.uuid = uuid.uuid4()

        return self.import_(task)

    def modify(self, task: Task) -> StdoutStderr:
        if not task.uuid:
            raise ClientUsageError(
                "Task has no UUID set.  You may want to use `add` instead."
            )

        return self.import_(task)

    def delete(self, task: Task) -> StdoutStderr:
        if not task.uuid:
            raise ClientUsageError("Task has no UUID set.")

        return self._execute(str(task.uuid), "delete")

    def filter(
        self, *params: Sequence[Union[FilterSpec, Q]], **dictparams: DictFilterSpec
    ) -> List[Task]:
        q = Q(*params, **dictparams)

        stdout, _ = self._execute(q.serialize(), "export")

        return parse_raw_as(List[Task], stdout)

    def count(
        self, *params: Sequence[Union[FilterSpec, Q]], **dictparams: DictFilterSpec
    ) -> int:
        q = Q(*params, **dictparams)

        stdout, _ = self._execute(q.serialize(), "count")

        return int(stdout)

    def get(
        self, *params: Sequence[Union[FilterSpec, Q]], **dictparams: DictFilterSpec
    ) -> Task:
        result = self.filter(*params, **dictparams)

        if len(result) == 1:
            return result[0]
        else:
            q = Q(*params, **dictparams)
            if len(result) == 0:
                raise NotFound(q.serialize())
            else:
                raise MultipleObjectsFound(q.serialize())

    def __repr__(self):
        return f"Client({self._config_filename})"


class Groupable:
    _logical_operator: Optional[Literal["and", "or"]] = None
    _logical_operands: Tuple[Groupable, Groupable]

    def __init__(
        self, operator: Literal["and", "or"], left: Groupable, right: Groupable
    ):
        self._logical_operator = operator
        self._logical_operands = (left, right)

    def __and__(self, other: Groupable) -> Groupable:
        return Groupable("and", self, other)

    def __or__(self, other: Groupable) -> Groupable:
        return Groupable("or", self, other)

    def serialize(self) -> str:
        return (
            f"({self._logical_operands[0].serialize()} "
            f"{self._logical_operator} "
            f"{self._logical_operands[1].serialize()})"
        )

    def __str__(self):
        return self.serialize()

    def __repr__(self):
        return f"Q({self})"


class Q(Groupable):
    _params: List[Union[FilterSpec, Q]]

    def __init__(
        self, *params: Iterable[Union[FilterSpec, Q]], **dictparams: DictFilterSpec
    ):
        self._params = cast(List[Union[FilterSpec, Q]], list(params)) + [dictparams]

    def serialize(self):
        parts: List[str] = []

        for param in self._params:
            if hasattr(param, "serialize"):
                parts.append(param.serialize())
            elif isinstance(param, str):
                parts.append(param)
            elif isinstance(param, dict):
                parts.append(dictfilterspec_to_string(param))
            else:
                raise ValueError(f"Unexpected parameter type: {param}")

        parts = [part for part in parts if part]

        if len(parts) == 0:
            return ""

        return f"({' '.join(parts)})"


def dictfilterspec_to_string(spec: DictFilterSpec) -> str:
    parts: List[str] = []

    for k, v in spec.items():
        parts.append(f"{k.replace('__', '.')}:{dictfilterspec_value_to_string(v)}")

    parts = [part for part in parts if part]

    if len(parts) == 0:
        return ""

    return f"({' '.join(parts)})"


def dictfilterspec_value_to_string(value: Any) -> str:
    if isinstance(value, str):
        return value
    elif isinstance(value, float):
        return str(value)
    elif isinstance(value, datetime.date):
        return value.strftime("%Y-%m-%d")
    elif isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%S")
    else:
        return str(value)
