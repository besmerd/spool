import email
import pytest
import smtpd

from unittest import mock

from mailman import main


SIMPLE = '''\
---
mails:
  - name: simple
    description: A simple text message
    sender: sender@example.org
    recipients: recipient@example.org
    subject: Simple Text Message
    text_body: |
        Just a simple text message.
'''

WITH_VARS = '''\
---
default:
  sender: sender@example.org
  recipients: recipient@example.org

vars:
  subject: Simple Text Message

mails:
  - name: simple
    recipients: recipient@example.org
    subject: '{{ subject }}'
    text_body: |
        Just a simple text message.
'''


class MailSink(smtpd.SMTPServer):

    def __init__(self, host='localhost', port=0):

        super(MailSink, self).__init__((host, port), None)
        self.mailbox = []

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):

        message = email.message_from_bytes(data)
        self.outbox.append(message)


@pytest.fixture
def smtpd():
    return MailSink()


@mock.patch('sys.argv', ['mailman', '--help'])
def test_help_flag(smtpd):
    with pytest.raises(SystemExit) as error:
        main.cli()

    assert error.type == SystemExit
    assert error.value.code == 0


@mock.patch('sys.argv', ['mailman', ])
def test_fail_with_no_config(smtpd):
    with pytest.raises(SystemExit) as error:
        main.cli()

    assert error.type == SystemExit
    assert error.value.code == 2


def test_success_with_simple_config(smtpd, tmp_path):

    config_1 = tmp_path / 'simple.yml'
    config_1.write_text(SIMPLE)

    config_2 = tmp_path / 'with_vars.yml'
    config_2.write_text(WITH_VARS)

    with mock.patch('sys.argv', ['mailman', str(config_1), str(config_2)]):
        main.cli()
