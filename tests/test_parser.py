import pytest
from pydantic import ValidationError as PydanticValidationError

from spool.parser import ConfigError, load_mails


def test_empty_config():
    load_mails({})


def test_no_mails():
    assert load_mails({'mails': []}) == ()


def test_minimal_config():
    mails = load_mails({
        'mails': [{
            'sender': '<sender@example.com>',
            'recipients': '<recipient@example.com>',
            'subject': 'Test email'
        }]
    })

    assert len(mails) == 1
    mail = mails[0]
    assert mail.envelope_from == '<sender@example.com>'
    assert mail.envelope_recipients == '<recipient@example.com>'
    assert mail.subject == 'Test email'


def test_yaml_header_names_are_normalized():
    mails = load_mails({
        'mails': [{
            'name': 'spoofed sender',
            'sender': 'bounce@attacker.example',
            'recipients': 'gateway@example.org',
            'from': 'CEO <ceo@company.example>',
            'to': 'Employee <employee@company.example>',
            'tags': 'spoofing, headers',
        }]
    })

    mail = mails[0]
    assert mail.from_addr == 'CEO <ceo@company.example>'
    assert mail.to_addrs == 'Employee <employee@company.example>'
    assert mail.tags == ['spoofing', 'headers']


def test_loading_does_not_mutate_input():
    source = {
        'defaults': {'sender': 'sender@example.org'},
        'mails': [{
            'name': 'test',
            'recipients': 'recipient@example.org',
        }],
    }

    load_mails(source)

    assert 'sender' not in source['mails'][0]


def test_mails_are_frozen_models():
    mails = load_mails({
        'mails': [{
            'sender': 'sender@example.org',
            'recipients': 'recipient@example.org',
            'smime': {
                'from_key_file': 'key.pem',
                'from_crt_file': 'certificate.pem',
            },
        }]
    })

    with pytest.raises(PydanticValidationError):
        mails[0].envelope_from = 'changed@example.org'


def test_fail_missing_senders_or_to():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'recipients': '<recipient@texample.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.'
            }]
        })


def test_fail_missing_recipients_or_to():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.'
            }]
        })


def test_fail_eml_and_text_body_given():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.',
                'eml': 'mail.eml'
            }]
        })


def test_fail_eml_and_html_body_given():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'subject': 'Test email',
                'html_body': 'This is a test email.',
                'eml': 'mail.eml'
            }]
        })


def test_fail_unknown_mail_property():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'recipients': '<recipient@test.com>',
                'unknown': 'value',
            }]
        })


def test_fail_smime_inline_and_file_value():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'recipients': '<recipient@test.com>',
                'smime': {
                    'from_key': 'inline key',
                    'from_key_file': 'key.pem',
                },
            }]
        })


def test_fail_incomplete_dkim_config():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'recipients': '<recipient@test.com>',
                'dkim': {'domain': 'example.org'},
            }]
        })


def test_fail_incomplete_smime_signing_config():
    with pytest.raises(ConfigError):
        load_mails({
            'mails': [{
                'sender': '<sender@test.com>',
                'recipients': '<recipient@test.com>',
                'smime': {'from_key_file': 'key.pem'},
            }]
        })
