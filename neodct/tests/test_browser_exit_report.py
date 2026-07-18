# The Browser app reports how netsurf-fb exited on the serial console
# so crashes (segfault, OOM kill) are visible without a debugger.
from System.apps.Browser.main import _describe_exit


def test_clean_exit():
    assert _describe_exit(0) == "neodct-browser: exited normally"


def test_error_exit_code():
    assert _describe_exit(1) == "neodct-browser: exited with code 1"


def test_signal_exits_name_known_signals():
    # subprocess returncode is -signum for signal deaths
    assert _describe_exit(-11) == \
        "neodct-browser: KILLED by signal 11 (SIGSEGV)"
    assert _describe_exit(-9) == \
        "neodct-browser: KILLED by signal 9 (SIGKILL, possible OOM)"
    assert _describe_exit(-6) == \
        "neodct-browser: KILLED by signal 6 (SIGABRT)"


def test_signal_exit_unknown_signal():
    assert _describe_exit(-31) == "neodct-browser: KILLED by signal 31"
