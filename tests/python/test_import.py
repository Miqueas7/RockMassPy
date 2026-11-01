import rockmasspy as rm


def test_version():
    assert rm.__version__ == "0.1.0"


def test_verification_enum():
    assert len({rm.Verification.Primary, rm.Verification.PrimaryLaterAuthors,
                rm.Verification.Secondary}) == 3
