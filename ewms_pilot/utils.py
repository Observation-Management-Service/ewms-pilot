"""Common utilities."""


from typing import List


def all_task_errors_string(task_errors: List[BaseException]) -> str:
    """Make a string from the multiple task exceptions."""
    return (
        f"{len(task_errors)} TASK(S) FAILED: "
        f"{', '.join(repr(e) for e in task_errors)}"
    )
