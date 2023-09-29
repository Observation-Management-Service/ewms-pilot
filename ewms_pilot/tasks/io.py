"""Tools for controlling sub-processes' input/output."""


import enum
import json
import pickle
from pathlib import Path
from typing import Any

from ..config import LOGGER


class FileType(enum.Enum):
    """Various file types/extensions."""

    PKL = ".pkl"
    TXT = ".txt"
    JSON = ".json"


class UniversalFileInterface:
    """Support reading and writing for any `FileType` file extension."""

    @classmethod
    def write(cls, in_msg: Any, fpath: Path) -> None:
        """Write `stuff` to `fpath` per `fpath.suffix`."""
        cls._write(in_msg, fpath)
        LOGGER.info(f"File Written :: {fpath} ({fpath.stat().st_size} bytes)")

    @classmethod
    def _write(cls, in_msg: Any, fpath: Path) -> None:
        LOGGER.info(f"Writing to file: {fpath}")
        LOGGER.debug(in_msg)

        # PKL
        if fpath.suffix == FileType.PKL.value:
            with open(fpath, "wb") as f:
                pickle.dump(in_msg, f)
        # TXT
        elif fpath.suffix == FileType.TXT.value:
            with open(fpath, "w") as f:
                f.write(in_msg)
        # JSON
        elif fpath.suffix == FileType.JSON.value:
            with open(fpath, "w") as f:
                json.dump(in_msg, f)
        # ???
        else:
            raise ValueError(f"Unsupported file type: {fpath.suffix} ({fpath})")

    @classmethod
    def read(cls, fpath: Path) -> Any:
        """Read and return contents of `fpath` per `fpath.suffix`."""
        msg = cls._read(fpath)
        LOGGER.info(f"File Read :: {fpath} ({fpath.stat().st_size} bytes)")
        LOGGER.debug(msg)
        return msg

    @classmethod
    def _read(cls, fpath: Path) -> Any:
        LOGGER.info(f"Reading from file: {fpath}")

        # PKL
        if fpath.suffix == FileType.PKL.value:
            with open(fpath, "rb") as f:
                return pickle.load(f)
        # TXT
        elif fpath.suffix == FileType.TXT.value:
            with open(fpath, "r") as f:
                return f.read()
        # JSON
        elif fpath.suffix == FileType.JSON.value:
            with open(fpath, "r") as f:
                return json.load(f)
        # ???
        else:
            raise ValueError(f"Unsupported file type: {fpath.suffix} ({fpath})")
