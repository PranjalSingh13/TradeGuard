from tradeguard.validation.iso6346 import is_valid_container, iso6346_check_digit


def test_known_valid_container():
    assert is_valid_container("CSQU3054383")
    assert iso6346_check_digit("CSQU305438") == 3


def test_wrong_check_digit_is_invalid():
    assert not is_valid_container("CSQU3054384")


def test_bad_format_is_invalid():
    assert not is_valid_container("CSQU305438")      # too short
    assert not is_valid_container("CSQX3054383")     # category letter must be U, J or Z
    assert not is_valid_container("12QU3054383")     # owner code must be letters


def test_spaces_and_case_are_tolerated():
    assert is_valid_container("csqu 3054383")
