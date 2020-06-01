import pytest
from mailman.parser import Config, ConfigError


def test_empty_config():
    Config.load({})


def test_no_mails():
    config = Config.load({'mails': []})
    assert len(config.mails) == 0


def test_minimal_config():
    config = Config.load({
        'mails': [{
            'sender': '<sender@example.com>',
            'recipients': '<recipient@example.com>',
            'subject': 'Test email'
        }]
    })

    assert len(config.mails) == 1
    mail = config.mails[0]
    assert mail['sender'] == '<sender@example.com>'
    assert mail['recipients'] == '<recipient@example.com>'
    assert mail['subject'] == 'Test email'


def test_fail_missing_senders_or_to():
    with pytest.raises(ConfigError):
        Config.load({
            'mails': [{
                'recipients': '<recipient@texample.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.'
            }]
        })


def test_fail_missing_recipients_or_to():
    with pytest.raises(ConfigError):
        Config.load({
            'mails': [{
                'sender': '<sender@test.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.'
            }]
        })


def test_fail_eml_and_text_body_given():
    with pytest.raises(ConfigError):
        Config.load({
            'mails': [{
                'sender': '<sender@test.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.',
                'eml': 'mail.eml'
            }]
        })


def test_fail_eml_and_html_body_given():
    with pytest.raises(ConfigError):
        Config.load({
            'mails': [{
                'sender': '<sender@test.com>',
                'subject': 'Test email',
                'html_body': 'This is a test email.',
                'eml': 'mail.eml'
            }]
        })
