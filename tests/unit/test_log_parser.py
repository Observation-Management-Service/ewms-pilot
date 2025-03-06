"""Test the LogParser class."""

import textwrap
from pathlib import Path

from ewms_pilot.utils.utils import LogParser


def test_110__all_apptainer_logs(tmp_path: Path):
    """Creates a temp file and writes a string into it."""
    temp_file = tmp_path / "test.log"
    test_content = textwrap.dedent(  # fixes """-indentation
        """
        DEBUG   [U=613,P=1]        sylogBuiltin()                Running action command run
        FATAL   [U=613,P=1]        StageTwo()                    exec /bin/bash failed: fork/exec /bin/bash: input/output error
        DEBUG   [U=613,P=47]       startContainer()              stage 2 process reported an error, waiting status
        DEBUG   [U=613,P=47]       CleanupContainer()            Cleanup container
        DEBUG   [U=613,P=47]       umount()                      Umount /var/lib/apptainer/mnt/session/final
        DEBUG   [U=613,P=47]       umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
        DEBUG   [U=613,P=47]       Master()                      Child exited with exit status 255
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert log_parser.apptainer_extract_error() == "Child exited with exit status 255"
