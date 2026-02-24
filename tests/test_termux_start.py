from puterui.termux_start import is_termux_environment


def test_is_termux_environment_true_with_prefix() -> None:
    assert is_termux_environment({"PREFIX": "/data/data/com.termux/files/usr"})


def test_is_termux_environment_true_with_termux_version() -> None:
    assert is_termux_environment({"TERMUX_VERSION": "0.118"})


def test_is_termux_environment_false() -> None:
    assert not is_termux_environment({"PREFIX": "/usr/local"})
