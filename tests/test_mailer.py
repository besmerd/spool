import smtplib
import logging
from unittest.mock import patch, MagicMock
import dns
import pytest

from spool.message import Message
from spool.mailer import MAIL_OUT_PREFIX, MAIL_OUT_SUFFIX, Mailer


@pytest.fixture()
def message():
    return Message(
        name='test', sender='sender@example.org',
        recipients='recipient@example.org, noreply@example.org',
        # Set Message-Id header to None to prevent a dns lookup
        headers={'Message-ID': None},
    )


@pytest.fixture()
def mailer(smtp_server):

    # Use relay to prevent dns lookup
    return Mailer(
        relay=smtp_server.host, port=smtp_server.port, helo='mail.example.com')



@patch.object(smtplib.SMTP, 'sendmail')
def test_message_sent(mock_send, mailer, message, caplog):

    caplog.set_level(logging.INFO)
    mailer.send(message)

    assert len(caplog.record_tuples) == 2
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.INFO
    assert 'Connecting to remote server.' in msg

    _, severity, msg = caplog.record_tuples[1]
    assert severity == logging.INFO
    assert 'Message sent.' in msg


@patch.object(smtplib.SMTP, 'sendmail')
def test_remote_refused_sender(mock_send, mailer, message, caplog):
    mock_send.side_effect = smtplib.SMTPSenderRefused(
        550, b'5.1.0 Address rejected.', 'recipient@example.org')
    mailer.send(message)

    assert len(caplog.record_tuples) == 1
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.ERROR
    assert 'Failed to send message: Sender rejected.' in msg



@patch.object(smtplib.SMTP, 'sendmail')
def test_remote_refused_recipient(mock_send, mailer, message, caplog):

    err_code, err_msg = 550, b'5.1.0 Address rejected.'
    mock_send.return_value = {message.recipients[1][1]: (err_code, err_msg)}
    mailer.send(message)

    assert len(caplog.record_tuples) == 1
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.WARNING
    assert f'Remote refused recipient: {message.recipients[1][1]}' in msg


@patch.object(smtplib.SMTP, 'sendmail')
def test_remote_refused_all_recipients(mock_send, mailer, message, caplog):

    recipients = [rcpt[1] for rcpt in message.recipients]
    mock_send.side_effect = smtplib.SMTPRecipientsRefused(recipients)
    mailer.send(message)

    assert len(caplog.record_tuples) == 1
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.ERROR
    assert 'Failed to send message: Remote refused all recipients.' in msg



@patch.object(smtplib.SMTP, 'sendmail')
def test_remote_dropped_connection(mock_send, mailer, message, caplog):

    mock_send.side_effect = smtplib.SMTPServerDisconnected()
    mailer.send(message)

    assert len(caplog.record_tuples) == 1
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.ERROR
    assert 'Failed to send message: Connection closed by remote host.' in msg


@pytest.mark.parametrize('error', [
    (554, b'5.7.1 Spam message rejected', 'permanent'),
    (451, b'4.7.1 Try again later', 'temporary'),
], ids=lambda error: error[2])
@patch.object(smtplib.SMTP, 'sendmail')
def test_remote_response_error(mock_send, error, mailer, message, caplog):

    mock_send.side_effect = smtplib.SMTPResponseException(error[0], error[1])
    mailer.send(message)

    assert len(caplog.record_tuples) == 1
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.ERROR
    assert f'Error while sending message: {error[0]} - {error[1].decode()}' in msg


class MockResourceRecord:

    class DNSName:

        def __init__(self, name):
            self.name = name

        def to_text(self):
            return str(self.name)

    def __init__(self, name, preference):
        self.exchange = self.DNSName(name)
        self.preference = preference


dns_data = [
    {
        'domain': 'example.org',
        'response': [
            MockResourceRecord('.', 0)
        ],
        'expected': '.',
        'case': 'is-root-server',
    },
    {
        'domain': 'example.org',
        'response': [
            MockResourceRecord('mail.example.org.', 0)
        ],
        'expected': 'mail.example.org',
        'case': 'is-non-root-server',
    },
    {
        'domain': 'example.org',
        'response': [
            MockResourceRecord('mail1.example.org.', 10),
            MockResourceRecord('mail2.example.org.', 10),
        ],
        'expected': 'mail1.example.org',
        'case': 'ordered-equal-priority',
    },
    {
        'domain': 'example.org',
        'response': [
            MockResourceRecord('mail1.example.org.', 20),
            MockResourceRecord('mail2.example.org.', 10),
        ],
        'expected': 'mail2.example.org',
        'case': 'has-priority'
    },
]


@pytest.mark.parametrize('data', dns_data, ids=lambda data: data['case'])
def test_get_remote(mailer, data):
    with patch.object(dns.resolver.Resolver, 'query',
                      return_value=data['response']) as mock_query:
        assert mailer.get_remote(data['domain']) == data['expected']


@patch.object(smtplib.SMTP, 'sendmail')
def test_dump_to_console(mock_send, mailer, message, capsys):

    mailer.send(message, print_only=True)
    out, err = capsys.readouterr()

    assert err == ''

    assert out.startswith(MAIL_OUT_PREFIX)
    assert message.as_string() in out
    assert out.endswith(MAIL_OUT_SUFFIX + '\n')

    mock_send.assert_not_called()
