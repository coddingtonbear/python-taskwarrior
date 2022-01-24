from typing import List


class ClientError(Exception):
    pass


class CommandError(ClientError):
    command: List[str]
    stderr: str
    stdout: str
    return_code: int

    def __init__(self, command: List[str], stderr: str, stdout: str, return_code: int):
        super().__init__(stderr)
        self.command = command
        self.stderr = stderr
        self.stdout = stdout
        self.return_code = return_code


class ClientUsageError(ClientError, ValueError):
    pass


class FilterError(ClientError):
    pass


class NotFound(FilterError):
    pass


class MultipleObjectsFound(FilterError):
    pass
