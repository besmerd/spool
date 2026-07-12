import logging
import socket
from collections import namedtuple

import pytest
from aiosmtpd.controller import Controller

from aiosmtpd.controller import Controller


def get_free_port():
    """Reserve an available local TCP port for the test server."""

    with socket.socket() as sock:
        sock.bind(('localhost', 0))
        return sock.getsockname()[1]


class MessageHandler:

    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(RecordedMessage(
            peer=session.peer,
            mailfrom=envelope.mail_from,
            rcpttos=envelope.rcpt_tos,
            data=envelope.content,
        ))
        return '250 Message accepted for delivery'


class MailServer:

    def __init__(self, host='localhost', port=None):
        self.host = host
        self.port = port or get_free_port()
        self.handler = MessageHandler()
        self.controller = Controller(
            self.handler,
            hostname=self.host,
            port=self.port,
            decode_data=True,
        )

    @property
    def messages(self):
        return self.handler.messages

    def __enter__(self):
        self._log_level = logging.getLogger('mail.log').level
        logging.getLogger('mail.log').setLevel(logging.WARNING)
        self.controller.start()
        return self

    def __exit__(self, *exc):
        self.controller.stop()
        logging.getLogger('mail.log').setLevel(self._log_level)

    def __repr__(self):
        return f'<smtp.Server {self.host}:{self.port}>'


class SimpleMessageHandler:

    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope.content.decode('utf8'))
        return '250 OK'


@pytest.fixture(scope='function')
def smtp_server():
    with SMTPServer() as server:
        yield server
