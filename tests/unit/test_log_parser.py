"""Test the LogParser class."""

import textwrap
from pathlib import Path

import pytest

from ewms_pilot.utils.utils import LogParser


def prep_multiline(lines: str) -> str:
    lines = textwrap.dedent(lines)  # fixes """-indentation
    while lines.startswith("\n"):  # removes leading empties
        lines = lines[1:]
    while lines.endswith("\n\n"):  # removes trailing empties
        lines = lines[:-1]  # don't remove final newline
    return lines


@pytest.mark.parametrize("parser_type", ["apptainer", "non-apptainer"])
def test_000__generic__stacktrace(tmp_path: Path, parser_type: str):
    """Test."""
    temp_file = tmp_path / "test.log"

    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
        """
        ...
        foo
        bar
        baz
        ...
        Traceback (most recent call last):
            not this one
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
            return _run_code(code, main_globals, None,
          ...blah...
          File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/recos/millipede_wilks.py", line 73, in setup_reco
            self.cascade_service = photonics_service.I3PhotoSplineService(
        RuntimeError: Error reading table coefficients
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert (
        {
            "non-apptainer": log_parser.generic_extract_error,
            "apptainer": log_parser.apptainer_extract_error,
        }[parser_type]()
        == prep_multiline(
            """
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
            return _run_code(code, main_globals, None,
          ...blah...
          File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/recos/millipede_wilks.py", line 73, in setup_reco
            self.cascade_service = photonics_service.I3PhotoSplineService(
        RuntimeError: Error reading table coefficients
        """
        ).rstrip("\n")
    )


@pytest.mark.parametrize("parser_type", ["apptainer", "non-apptainer"])
def test_001__generic__stacktrace(tmp_path: Path, parser_type: str):
    """Test."""
    temp_file = tmp_path / "test.log"

    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
        """
        ...
        foo
        bar
        baz
        ...
        Traceback (most recent call last):
            not this one
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
          File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
          File "<frozen importlib._bootstrap_external>", line 1016, in get_code
          File "<frozen importlib._bootstrap_external>", line 1073, in get_data
        OSError: [Errno 107] Transport endpoint is not connected: '/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/array.py'
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert (
        {
            "non-apptainer": log_parser.generic_extract_error,
            "apptainer": log_parser.apptainer_extract_error,
        }[parser_type]()
        == prep_multiline(
            """
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
          File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
          File "<frozen importlib._bootstrap_external>", line 1016, in get_code
          File "<frozen importlib._bootstrap_external>", line 1073, in get_data
        OSError: [Errno 107] Transport endpoint is not connected: '/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/array.py'
        """
        ).rstrip("\n")
    )


@pytest.mark.parametrize("parser_type", ["apptainer", "non-apptainer"])
def test_010__generic__one_line_error(tmp_path: Path, parser_type: str):
    """Test."""
    temp_file = tmp_path / "test.log"

    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
        """
        ...
        foo
        bar
        baz
        ...
        curl: (22) The requested URL returned error: 404
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert {
        "non-apptainer": log_parser.generic_extract_error,
        "apptainer": log_parser.apptainer_extract_error,
    }[parser_type]() == "curl: (22) The requested URL returned error: 404"


def test_100__apptainer__stacktrace(tmp_path: Path):
    """Test."""
    temp_file = tmp_path / "test.log"

    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
        """
        ...
        foo
        bar
        baz
        ...
        Traceback (most recent call last):
            not this one
        ...
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
            return _run_code(code, main_globals, None,
          File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
            exec(code, run_globals)
          File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/reco_icetray.py", line 151, in reco_pixel
            reco.setup_reco()
          File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/recos/millipede_wilks.py", line 73, in setup_reco
            self.cascade_service = photonics_service.I3PhotoSplineService(
        RuntimeError: Error reading table coefficients
        DEBUG   [U=59925,P=95]     CleanupContainer()            Cleanup container
        DEBUG   [U=59925,P=95]     umount()                      Umount /var/lib/apptainer/mnt/session/final
        DEBUG   [U=59925,P=95]     umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
        DEBUG   [U=59925,P=95]     Master()                      Child exited with exit status 1
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert (
        log_parser._get_last_non_apptainer_logline_index()
        == len(test_content.splitlines()) - 1 - 4
    )
    assert (
        log_parser.apptainer_extract_error()
        == prep_multiline(
            """
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
            return _run_code(code, main_globals, None,
          File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
            exec(code, run_globals)
          File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/client/reco_icetray.py", line 151, in reco_pixel
            reco.setup_reco()
          File "/usr/local/lib/python3.10/dist-packages/skymap_scanner/recos/millipede_wilks.py", line 73, in setup_reco
            self.cascade_service = photonics_service.I3PhotoSplineService(
        RuntimeError: Error reading table coefficients
        """
        ).rstrip("\n")
    )


def test_101__apptainer__stacktrace(tmp_path: Path):
    """Test."""
    temp_file = tmp_path / "test.log"

    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
        """
        ...
        foo
        bar
        baz
        ...
        Traceback (most recent call last):
            not this one
        ...
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
          File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
          File "<frozen importlib._bootstrap_external>", line 1016, in get_code
          File "<frozen importlib._bootstrap_external>", line 1073, in get_data
        OSError: [Errno 107] Transport endpoint is not connected: '/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/array.py'
        DEBUG   [U=59925,P=94]     CleanupContainer()            Cleanup container
        DEBUG   [U=59925,P=94]     umount()                      Umount /var/lib/apptainer/mnt/session/final
        DEBUG   [U=59925,P=94]     umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
        DEBUG   [U=59925,P=94]     Master()                      Child exited with exit status 1
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert (
        log_parser._get_last_non_apptainer_logline_index()
        == len(test_content.splitlines()) - 1 - 4
    )
    assert (
        log_parser.apptainer_extract_error()
        == prep_multiline(
            """
        Traceback (most recent call last):
          File "/usr/lib/python3.10/runpy.py", line 196, in _run_module_as_main
          File "/usr/lib/python3.10/runpy.py", line 86, in _run_code
          File "<frozen importlib._bootstrap_external>", line 1016, in get_code
          File "<frozen importlib._bootstrap_external>", line 1073, in get_data
        OSError: [Errno 107] Transport endpoint is not connected: '/usr/lib/python3/dist-packages/pandas/core/arrays/sparse/array.py'"""
        ).rstrip("\n")
    )


def test_110__apptainer__one_line_error(tmp_path: Path):
    """Test."""
    temp_file = tmp_path / "test.log"

    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
        """
        ...
        foo
        bar
        baz
        ...
        curl: (22) The requested URL returned error: 404
        DEBUG   [U=30101,P=1]      StartProcess()                Received signal child exited
        DEBUG   [U=30101,P=49]     CleanupContainer()            Cleanup container
        DEBUG   [U=30101,P=49]     umount()                      Umount /var/lib/apptainer/mnt/session/final
        DEBUG   [U=30101,P=49]     umount()                      Umount /var/lib/apptainer/mnt/session/rootfs
        DEBUG   [U=30101,P=49]     Master()                      Child exited with exit status 22
        """
    )
    temp_file.write_text(test_content, encoding="utf-8")

    log_parser = LogParser(temp_file)
    assert (
        log_parser._get_last_non_apptainer_logline_index()
        == len(test_content.splitlines()) - 1 - 5
    )
    assert (
        log_parser.apptainer_extract_error()
        == "curl: (22) The requested URL returned error: 404"
    )


def test_120__apptainer__all_apptainer_logs(tmp_path: Path):
    """Test."""
    temp_file = tmp_path / "test.log"
    test_content = prep_multiline(  # fixes """-indentation & removes leading/trailing empties
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
    assert log_parser._get_last_non_apptainer_logline_index() is None
    assert (
        log_parser.apptainer_extract_error()
        == "Apptainer-Error: Child exited with exit status 255"
    )
