from __future__ import annotations

import datetime
from typing import Dict
from typing import List
from typing import Optional
from typing import Type
from uuid import UUID

import dateutil.parser
import pytz
from pydantic import BaseModel
from pydantic import Extra
from pydantic import Field
from pydantic import FieldInfo
from pydantic import create_model
from pydantic import validator
from typing_extensions import Literal

DATETIME_FORMAT = "%Y%m%dT%H%M%SZ"


class TaskwarriorJsonModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime.datetime: lambda v: pytz.utc.normalize(v).strftime(
                DATETIME_FORMAT
            ),
        }


class Annotation(TaskwarriorJsonModel):
    entry: Optional[datetime.datetime]
    description: Optional[str]

    @validator(
        "entry",
        pre=True,
    )
    @classmethod
    def datetime_validator(cls, v) -> datetime.datetime:
        return dateutil.parser.parse(v)


class Task(TaskwarriorJsonModel, extra=Extra.allow):  # type: ignore[call-arg]
    annotations: Optional[List[Annotation]]
    depends: Optional[List[UUID]]
    description: str
    due: Optional[datetime.datetime]
    end: Optional[datetime.datetime]
    entry: Optional[datetime.datetime]
    id: Optional[int]
    imask: Optional[float]
    mask: Optional[str]
    modified: Optional[datetime.datetime]
    parent: Optional[UUID]
    project: Optional[str]
    recur: Optional[str]
    scheduled: Optional[datetime.datetime]
    start: Optional[datetime.datetime]
    status: Optional[Literal["pending", "completed", "deleted", "waiting", "recurring"]]
    tags: Optional[List[str]]
    until: Optional[datetime.datetime]
    urgency: Optional[float]
    uuid: Optional[UUID]
    wait: Optional[datetime.datetime]

    @validator(
        "due",
        "end",
        "entry",
        "modified",
        "scheduled",
        "start",
        "until",
        "wait",
        pre=True,
    )
    @classmethod
    def datetime_validator(cls, v) -> datetime.datetime:
        return dateutil.parser.parse(v)

    def add_annotation(self, description: str, entry: datetime.datetime = None):
        annotation = Annotation()
        annotation.entry = entry or pytz.utc.localize(datetime.datetime.utcnow())
        annotation.description = description

        self.annotations = self.annotations or []
        self.annotations.append(annotation)

    @classmethod
    def with_udas(cls, *uda_definitions: UdaConfig) -> Type[Task]:
        fields: Dict[str, FieldInfo] = {}

        for uda in uda_definitions:
            pass

        return create_model("TaskWithUdas", __base__=cls, **fields)


class UdaConfig(BaseModel):
    field_type: Literal["numeric", "date", "duration", "string"] = Field(alias="type")
    label: str
    values: Optional[List[str]]

    @validator("values", pre=True)
    @classmethod
    def values_validator(cls, v) -> List[str]:
        return v.split(",")
