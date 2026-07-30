from framework_cli.version import RELEASE_SOURCE, __version__


def test_version():
    assert __version__ == "0.1.0"
    assert RELEASE_SOURCE.endswith(__version__)
