from app.core.admin import parse_admin_ids


def test_parse_admin_ids():
    assert parse_admin_ids("1,2 3") == [1, 2, 3]
    assert parse_admin_ids(7) == [7]
    assert parse_admin_ids(["8", "bad", 9]) == [8, 9]
    assert parse_admin_ids(None) == []
