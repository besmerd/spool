import pytest

from spool.parser import MailSpec, SmimeSpec


@pytest.mark.parametrize('tags, mail_tags, expected', [
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
    (',b', ['a', 'b'], True),
    ('ab', ['a', 'b'], False),
    ('a,b', ['a', 'b'], True),
])
def test_matches_tags(tags, mail_tags, expected):
    mail = MailSpec(
        name='test',
        sender='sender@example.org',
        recipients='recipient@example.org',
        tags=mail_tags,
    )

    assert mail.matches_tags(tags) == expected


def test_smime_resolve_files_returns_copy(tmp_path):
    key_path = tmp_path / 'key.pem'
    key_path.write_text('private key')
    source = SmimeSpec(from_key_file=key_path.name)

    resolved = source.resolve_files(tmp_path)

    assert source.from_key_file == key_path.name
    assert source.from_key is None
    assert resolved.from_key_file is None
    assert resolved.from_key == 'private key'


def test_build_message_keeps_model_unchanged(tmp_path):
    mail = MailSpec(
        name='test',
        sender='sender@example.org',
        recipients='recipient@example.org',
        description='metadata',
        tags=['test'],
        attachments=['file.txt'],
    )

    message = mail.build_message(tmp_path)

    assert message.name == 'test'
    assert message.attachments == [tmp_path / 'file.txt']
    assert mail.description == 'metadata'
    assert mail.tags == ['test']
    assert mail.attachments == ['file.txt']
