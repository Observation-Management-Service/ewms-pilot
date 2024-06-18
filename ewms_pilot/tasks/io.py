"""Tools for controlling sub-processes' input/output."""


class FileExtension:
    """Really, this just strips the dot off the file extension string."""

    def __init__(self, extension: str):
        self.val = extension.lstrip(".").lower()

    def __str__(self) -> str:
        return self.val
