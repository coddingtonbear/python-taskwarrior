# Taskwarrior bindings for Python

Interact with your local taskwarrior task list from Python.

This is heavily inspired by [@ralphbean](https://github.com/ralphbean)'s [taskw library](https://github.com/ralphbean/taskw) (that I'm also a contributor to), but breaks with many past decisions so as to have a cleaner internal API, a saner method of interacting with Taskwarrior itself, type annotations, and much improved maintainability.

# Installation

```
pip install taskwarrior
```

You can also install the in-development version with:

```

pip install https://github.com/coddingtonbear/python-taskwarrior/archive/master.zip

```

# Quickstart

```python
>>> from taskwarrior import Client
>>> client = Client()
>>> tasks = client.filter(status='pending')
[Task(annotations=None, depends=None, description='Wake up', due=None, end=None, entry=datetime.datetime(2022, 1, 24, 4, 28, 11, tzinfo=tzutc()), id=1, imask=None, mask=None, modified=datetime.datetime(2022, 1, 24, 4, 28, 51, tzinfo=tzutc()), parent=None, project=None, recur=None, scheduled=None, start=None, status='pending', tags=['alarm'], until=None, urgency=0.8, uuid=UUID('a39ea0fa-682a-4815-9556-8b6785ee301c'), wait=None)]
>>>
```

# Examples

## Finding Tasks

The `filter` method is used for finding tasks:

```python
>>> from taskwarrior import Client
>>> client = Client()
>>> client.filter(status='pending')
[Task(annotations=None, depends=None, description='Wake up', due=None, end=None, entry=datetime.datetime(2023, 1, 24, 4, 28, 11, tzinfo=tzutc()), id=1, imask=None, mask=None, modified=datetime.datetime(2022, 1, 24, 4, 28, 51, tzinfo=tzutc()), parent=None, project=None, recur=None, scheduled=None, start=None, status='pending', tags=['alarm'], until=None, urgency=0.8, uuid=UUID('a39ea0fa-682a-4815-9556-8b6785ee301c'), wait=None)]
```

It accepts as parameters any of the following:

- Any number of keyword arguments:
  - Example of filter keyword arguments include:
    - `status='pending'`
    - `description__contains='Some string'`
    - `due__after='yesterday'`
  - Double-underscores are transformed into a `.` when sending the filter to Taskwarrior so as to allow you to use filters like `description.contains` or `due.after`.
- Any number of filter dictionaries:
  - These work much the same way as keyword arguments described above, but allow you to specify these as raw dictionaries instead.
- Any number of raw strings:
  - E.g. for filtering to tasks having only a certain tag, you can provide as a value `+mytag`.
- Any number of `Q` objects:
  - You can use `Q` objects to perform complex `or` and `and` queries using exactly the same keyword arguments, filter dictionaries, or string values descrribed above.
  - See "Using Q Objects" below for more information.

Each of these parameters are `and`-ed together should more than one parameter be provided.  If you need to use `or` expressions, see "Using Q Objects" below.

If you are expecting to retrieve just a single task, you can use the `.get` method, too:

```python
>>> from taskwarrior import Client
>>> client = Client()
>>> client.get(uuid="a39ea0fa-682a-4815-9556-8b6785ee301c")
Task(annotations=None, depends=None, description='Wake up', due=None, end=None, entry=datetime.datetime(2023, 1, 24, 4, 28, 11, tzinfo=tzutc()), id=1, imask=None, mask=None, modified=datetime.datetime(2022, 1, 24, 4, 28, 51, tzinfo=tzutc()), parent=None, project=None, recur=None, scheduled=None, start=None, status='pending', tags=['alarm'], until=None, urgency=0.8, uuid=UUID('a39ea0fa-682a-4815-9556-8b6785ee301c'), wait=None)
```

if either zero or more than one task is returned from your query, an exception will be raised.

## Retrieving tasks

```python
>>> from taskwarrior import Client
>>> client = Client()
>>> client.get(uuid="a39ea0fa-682a-4815-9556-8b6785ee301c")
Task(annotations=None, depends=None, description='Wake up', due=None, end=None, entry=datetime.datetime(2023, 1, 24, 4, 28, 11, tzinfo=tzutc()), id=1, imask=None, mask=None, modified=datetime.datetime(2022, 1, 24, 4, 28, 51, tzinfo=tzutc()), parent=None, project=None, recur=None, scheduled=None, start=None, status='pending', tags=['alarm'], until=None, urgency=0.8, uuid=UUID('a39ea0fa-682a-4815-9556-8b6785ee301c'), wait=None)
```

See "Finding Tasks" for more details -- this allows all of the functionality described there, except that it asserts that only a single task be returned.  Note that you can use any combination of fields you might like for retrieving your single task, but `uuid` and `id` are the ones most likely to be of use to you.

## Counting tasks

```python
>>> from taskwarrior import Client
>>> client = Client()
>>> client.count(status='pending')
1
```

This allows all of the same filtering logic that you can find described in "Finding tasks" above; see that section for more details.

## Adding Tasks

```python
>>> from taskwarrior import Client, Task
>>> client = Client()
>>> task = Task(description="my new task")
>>> client.add(task)
>>> task.uuid
UUID('29d06231-525f-4a62-9e9f-dd0f680aaaff')'
```

## Changing tasks

```python
>>> from taskwarrior import Client
>>> import pytz
>>> client = Client()
>>> task = client.get(uuid="a39ea0fa-682a-4815-9556-8b6785ee301c")
>>> task.due = datetime.datetime(2029, 1, 1, 10, 0, tzinfo=pytz.timezone('America/Los_Angeles'))
>>> client.modify(task)
```

Just alter the fields on the object directly using native python datatypes and pass your altered object to `modify` and your task will be updated immediately.


## Being Flexible

```python
>>> from taskwarrior import Client
>>> client = Client(
        config_filename="/path/to/my/taskrc",
        config_overrides={
            "some": {
                "config": "values",
            }
        },
        task_bin="/path/to/bin/task",
    )
```

You can provide the following parameters when instantiating your client:

- `config_filename`: (Default: `~/.taskrc`) The path of the `taskrc` file to use.
- `config_overrides`: A dictionary object representing configuration overrides to use when interacting with Taskwarrior.  Nested dictionaries will be encoded into dotted configuration paths using the key name in their parent dictionary.
- `task_bin`: The path to the `task` binary to use.

# Using Q Objects

Q objects (inspired by [Django's objects of the same name](https://docs.djangoproject.com/en/4.0/topics/db/queries/#s-complex-lookups-with-q-objects) can be used for building complex logical queries for filtering your tasks.

Q objects accept all of the same parameter types described in "Finding tasks" above, but can also be `or` or `and`-ed together using `|` or `&`:

```python
>>> from taskwarrior import Client, Q
>>> import pytz
>>> client = Client()
>>> client.filter(
        Q(status='pending') | Q(
            status='waiting',
            due__before=pytz.timezone('America/Los_Angeles').localize(
                datetime.datetime.utcnow() + datetime.timedelta(days=7)
            )
        )
    )
```

# How does this differ from [taskw](https://github.com/ralphbean/taskw)?

- This is a much younger library and may still have bugs.
- This interacts with Taskwarrior over its `export` and `import` ("plumbing") interfaces instead of interacting with its "porcelain" interfaces like `modify`.  This makes this library internally a lot simpler and less likely to break as Taskwarrior's command-line API is changed in the future.
- This has far fewer options and controls.  Mostly: those options and controls are of limited value and high maintenance cost anyway, so it's likely you won't even notice.
- This has much more sophisticated filtering capabilities.
- This uses a slightly simpler API for retrieving tasks -- rather than handing you a 2-tuple of values `(id, {data})` this just hands you a data object (or list of them).
- This uses a third-party library ([Pydantic](https://pydantic-docs.helpmanual.io/)) for data serialization/deserialization so as to remove those responsibilities from the library itself (and hopefully make it somewhat easier to maintain).
- This supports only modern versions of Taskwarrior.  Specifically: only versions of Taskwarrior newer than 2.5.1 are supported.
- This supports only currently supported versions of Python.  Specifically: only versions of Python currently receiving security updates are supported -- that means Python 3.7+ at the moment.
