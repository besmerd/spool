import pytest

from spool.main import tags_matches_mail


@pytest.mark.parametrize('tags, mail, expected', [
    (None, [], True),
    (None, ['a'], True),
    (None, ['a', 'b'], True),
    ('', [], True),
    ('', ['a'], True),
    ('', ['a', 'b'], True),
    ('None', [], False),
    ('a,', [], False),
    ('a', ['a'], True),
    ('a,', ['a', 'b'], True),
    ('a,', ['a', 'b'], True),
    (',b', ['a', 'b'], True),
    ('ab', ['a', 'b'], False),
    ('a,b', ['a', 'b'], True),
])
def test_tags_matches_mail(tags, mail, expected):
    assert tags_matches_mail(tags, mail) == expected
