import smtplib
import logging
from unittest.mock import patch
import pytest

from spool.message import Message
from spool.mailer import Mailer


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


@pytest.mark.parametrize('err_code, err_msg', [
    (554, b'5.7.1 Spam message rejected'),#, 'permanent'),
    (451, b'4.7.1 Try again later'),#, 'temporary'),
])
@patch.object(smtplib.SMTP, 'sendmail')
def test_remote_response_error(
        mock_send, err_code, err_msg, mailer, message, caplog):

    mock_send.side_effect = smtplib.SMTPResponseException(err_code, err_msg)
    mailer.send(message)

    assert len(caplog.record_tuples) == 1
    _, severity, msg = caplog.record_tuples[0]
    assert severity == logging.ERROR
    assert f'Error while sending message: {err_code} - {err_msg.decode()}' in msg
