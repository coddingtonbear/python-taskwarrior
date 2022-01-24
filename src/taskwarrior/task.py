import datetime
from typing import List, Optional, Literal
from uuid import UUID

import dateutil.parser
import pytz

from pydantic import BaseModel, Extra, validator


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


class Task(TaskwarriorJsonModel, extra=Extra.allow):
    annotations: Optional[List[Annotation]]
    depends: Optional[str]
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

    def get_depends(self) -> List[UUID]:
        if self.depends:
            return [UUID(dep) for dep in self.depends.split(",") if dep]

        return []

    def add_to_depends(self, dep: UUID):
        uuids = self.get_depends()

        if dep in uuids:
            raise ValueError(f"task already depends on {dep}")

        uuids.append(dep)

        self.depends = ",".join([str(dep) for dep in uuids])

    def remove_from_depends(self, dep: UUID):
        uuids = self.get_depends()

        if dep not in uuids:
            raise ValueError(f"task does not depend upon {dep}")

        uuids.remove(dep)

        self.depends = ",".join([str(dep) for dep in uuids])
