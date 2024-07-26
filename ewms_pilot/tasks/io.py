"""Tools for controlling sub-processes' input/output."""

import json
import logging
from pathlib import Path
from typing import Any

from mqclient.broker_client_interface import Message

LOGGER = logging.getLogger(__name__)


class InvalidDataForInfileException(Exception):
    """Raised when a message contains data that cannot be transformed into a file."""

    def __init__(self, reason: str, fpath: Path) -> None:
        super().__init__(f"{reason} for infile ({fpath.name})")


class InvalidDataFromOutfileException(Exception):
    """Raised when a file contains data that cannot be transformed into a message."""

    def __init__(self, reason: str, fpath: Path) -> None:
        super().__init__(f"{reason} for outfile ({fpath.name})")


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
        """Write `in_msg` to `fpath`."""
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
        # OBJECT -> json infile
        elif fpath.suffix == ".json":
            try:
                with open(fpath, "w") as f:
                    json.dump(in_msg.data, f)
            except TypeError as e:
                raise InvalidDataForInfileException(str(e), fpath)
        # OBJECT -> *NOT* json infile
        else:
            raise InvalidDataForInfileException(
                (
                    f"Message data must be json-serializable (with a '.json' infile), "
                    f"str, or bytes; not {type(in_msg.data)})"
                ),
                fpath,
            )


class OutFileInterface:
    """Support reading an outfile for use in a message."""

    @classmethod
    def read(cls, fpath: Path) -> Any:
        """Read and return contents of `fpath`."""
        if not fpath.exists():
            raise FileNotFoundError(f"Outfile was not found: {fpath}")

        LOGGER.info(f"OUTFILE :: {fpath} ({fpath.stat().st_size} bytes)")
        data = cls._read(fpath)
        LOGGER.debug(data)
        return data

    @classmethod
    def _read(cls, fpath: Path) -> Any:
        LOGGER.info(f"Reading from file: {fpath}")

        # json outfile -> OBJECT
        if fpath.suffix == ".json":
            with open(fpath, "r") as f:  # plain text
                try:
                    return json.load(f)
                except TypeError as e:
                    raise InvalidDataFromOutfileException(str(e), fpath)
        # non-json outfile...
        else:
            # PLAIN TEXT
            try:
                with open(fpath, "r") as f:  # plain text
                    return f.read()
            # BYTES
            except UnicodeDecodeError:
                with open(fpath, "rb") as f:  # bytes
                    return f.read()
