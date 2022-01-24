import datetime
import os
import shutil
import tempfile
import uuid
from unittest import TestCase

import pytest
import pytz

from ..client import Client
from ..client import Q
from ..exceptions import ClientUsageError
from ..exceptions import MultipleObjectsFound
from ..exceptions import NotFound
from ..task import Task


class TestClient(TestCase):
    TASK_UUID_WAKE_UP = uuid.UUID("a39ea0fa-682a-4815-9556-8b6785ee301c")
    TASK_UUID_SLEEP = uuid.UUID("0189becf-a28b-497e-bd67-d04fa1ee3fa8")

    task_data: str
    taskrc_path: str
    client: Client

    def setUp(self):
        self.task_data = tempfile.mkdtemp()
        self.taskrc_path = os.path.join(self.task_data, "taskrc")

        with open(self.taskrc_path, "w") as outf:
            outf.write(
                f"""
                data.location = {self.task_data}
                """
            )

        shutil.copy(
            os.path.join(os.path.dirname(__file__), "fixtures/pending.data"),
            self.task_data,
        )

        self.client = Client(config_filename=self.taskrc_path)

        super().setUp()

    def tearDown(self):
        shutil.rmtree(self.task_data)

        super().tearDown()


class TestFilter(TestClient):
    def test_sanity(self):
        results = self.client.filter()

        assert len(results) == 2

    def test_with_tag(self):
        results = self.client.filter("+alarm")

        assert len(results) == 1

        assert results[0].uuid == self.TASK_UUID_WAKE_UP

    def test_without_tag(self):
        results = self.client.filter("-alarm")

        assert len(results) == 1

        assert results[0].uuid == self.TASK_UUID_SLEEP

    def test_dict_filter(self):
        results = self.client.filter({"description": "Wake"})

        assert len(results) == 1

        assert results[0].uuid == self.TASK_UUID_WAKE_UP

    def test_kwargs_filter(self):
        results = self.client.filter(description="Wake")

        assert len(results) == 1

        assert results[0].uuid == self.TASK_UUID_WAKE_UP

    def test_q_or_filter(self):
        results = self.client.filter(
            Q(description__contains="Wake") | Q(description__contains="sleep")
        )

        assert len(results) == 2

        assert set([results[0].uuid, results[1].uuid]) == set(
            [
                self.TASK_UUID_SLEEP,
                self.TASK_UUID_WAKE_UP,
            ]
        )


class TestGet(TestClient):
    def test_get_single(self):
        assert self.client.get(description__contains="Wake")

    def test_not_found(self):
        with pytest.raises(NotFound):
            self.client.get(description="This doesn't exist")

    def test_get_multiple(self):
        with pytest.raises(MultipleObjectsFound):
            self.client.get()


class TestImport(TestClient):
    def test_update_due_date(self):
        new_due_date = datetime.datetime(2029, 3, 2, 6, 0, tzinfo=pytz.utc)

        wake_up = self.client.get(uuid=self.TASK_UUID_WAKE_UP)
        wake_up.due = new_due_date

        self.client.import_(wake_up)

        changed_wake_up = self.client.get(uuid=self.TASK_UUID_WAKE_UP)

        assert self.client.count() == 2

        assert changed_wake_up.due == new_due_date


class TestCount(TestClient):
    def test_count(self):
        assert self.client.count() == 2


class TestAdd(TestClient):
    def test_add_new(self):
        new = Task(description="New Task")

        self.client.add(new)

        assert self.client.count() == 3

        retrieved = self.client.get(uuid=new.uuid)

        assert retrieved.description == new.description

    def test_add_existing(self):
        existing = self.client.get(uuid=self.TASK_UUID_SLEEP)

        with pytest.raises(ClientUsageError):
            self.client.add(existing)


class TestDelete(TestClient):
    def test_delete_existing(self):
        existing = self.client.get(uuid=self.TASK_UUID_SLEEP)

        self.client.delete(existing)

        deleted = self.client.get(uuid=existing.uuid)
        assert deleted.status == "deleted"

    def test_delete_new(self):
        new = Task(description="New Task")

        with pytest.raises(ClientUsageError):
            self.client.delete(new)


class TestModify(TestClient):
    def test_modify_new(self):
        new = Task(description="New Task")

        with pytest.raises(ClientUsageError):
            self.client.modify(new)

    def test_modify_existing(self):
        existing = self.client.get(uuid=self.TASK_UUID_SLEEP)

        existing.due = datetime.datetime(2030, 3, 2, 6, 0, tzinfo=pytz.utc)

        self.client.modify(existing)

        retrieved = self.client.get(uuid=self.TASK_UUID_SLEEP)

        assert retrieved.due == existing.due

    def test_add_annotation_unspecified_entry(self):
        arbitrary_annotation = "Test"

        existing = self.client.get(uuid=self.TASK_UUID_SLEEP)

        existing.add_annotation(arbitrary_annotation)

        self.client.modify(existing)

        retrieved = self.client.get(uuid=self.TASK_UUID_SLEEP)

        assert len(retrieved.annotations) == 1
        assert retrieved.annotations[0].description == arbitrary_annotation
        assert retrieved.annotations[0].entry < pytz.utc.localize(
            datetime.datetime.utcnow()
        )

    def test_add_dependency(self):
        depends = self.client.get(uuid=self.TASK_UUID_WAKE_UP)

        existing = self.client.get(uuid=self.TASK_UUID_SLEEP)
        existing.depends = [depends.uuid]

        self.client.modify(existing)

        retrieved = self.client.get(uuid=self.TASK_UUID_SLEEP)

        assert len(retrieved.depends) == 1
        assert retrieved.depends[0] == self.TASK_UUID_WAKE_UP

    def test_remove_dependency(self):
        depends = self.client.get(uuid=self.TASK_UUID_WAKE_UP)

        existing = self.client.get(uuid=self.TASK_UUID_SLEEP)
        existing.depends = [depends.uuid]
        self.client.modify(existing)

        retrieved = self.client.get(uuid=self.TASK_UUID_SLEEP)
        retrieved.depends = []

        self.client.modify(retrieved)

        retrieved_again = self.client.get(uuid=self.TASK_UUID_SLEEP)

        assert not retrieved_again.depends

    def test_unexpected_uda(self):
        task_with_orphaned_uda = self.client.get(uuid=self.TASK_UUID_WAKE_UP)

        task_with_orphaned_uda.orphaned = "orphaned data"

        self.client.modify(task_with_orphaned_uda)

        retrieved = self.client.get(uuid=self.TASK_UUID_WAKE_UP)
        assert retrieved.orphaned == task_with_orphaned_uda.orphaned
