"""Tools for controlling sub-processes' input/output."""

from pathlib import Path
from typing import Any

from mqclient.broker_client_interface import Message

from ..config import LOGGER


class FileExtension:
    """Really, this just strips the dot off the file extension string."""

    def __init__(self, extension: str):
        self.val = extension.lstrip(".").lower()

    def __str__(self) -> str:
        return self.val


class InFileInterface:
    """Support writing an infile from message data."""

    @classmethod
    def write(cls, in_msg: Message, fpath: Path) -> None:
        """Write `stuff` to `fpath` per `fpath.suffix`."""
        cls._write(in_msg, fpath)
        LOGGER.info(f"INFILE :: {fpath} ({fpath.stat().st_size} bytes)")

    @classmethod
    def _write(cls, in_msg: Message, fpath: Path) -> None:
        LOGGER.info(f"Writing to file: {fpath}")
        LOGGER.debug(in_msg)

        # PLAIN TEXT
        if isinstance(in_msg.data, str):  # ex: text, yaml string, json string
            with open(fpath, "w") as f:
                f.write(in_msg.data)
        # BYTES
        elif isinstance(in_msg.data, bytes):  # ex: pickled data, jpeg, gif, ...
            with open(fpath, "wb") as f:
                f.write(in_msg.data)
        # OBJECT
        else:
            raise TypeError(
                f"Message data must be a str or bytes, not {type(in_msg.data)}"
            )


class OutFileInterface:
    """Support reading an outfile for use in a message."""

    @classmethod
    def read(cls, fpath: Path) -> Any:
        """Read and return contents of `fpath` per `fpath.suffix`."""
        LOGGER.info(f"OUTFILE :: {fpath} ({fpath.stat().st_size} bytes)")
        data = cls._read(fpath)
        LOGGER.debug(data)
        return data

    @classmethod
    def _read(cls, fpath: Path) -> Any:
        LOGGER.info(f"Reading from file: {fpath}")

        # PLAIN TEXT
        try:
            with open(fpath, "r") as f:  # plain text
                return f.read()
        # BYTES
        except UnicodeDecodeError:
            with open(fpath, "rb") as f:  # bytes
                return f.read()
