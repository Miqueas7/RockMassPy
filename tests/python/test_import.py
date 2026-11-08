from importlib.metadata import version

import rockmasspy as rm


def test_version():
    assert rm.__version__ == "0.2.0"
    assert version("rockmasspy") == rm.__version__  # pyproject.toml y __init__.py no se desfasan


def test_verification_enum():
    assert len({rm.Verification.Primary, rm.Verification.PrimaryLaterAuthors,
                rm.Verification.Secondary}) == 3
