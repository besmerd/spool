from email.message import EmailMessage

import asyncio
import pytest

from aiosmtpd.controller import Controller


class MessageHandler:
    def __init__(self):
        self.messages = []

    async def handle_DATA(self, server, session, envelope):
        self.messages.append(envelope.content.decode('utf8'))
        return '250 OK'


class SMTPServer:

    def __init__(self, hostname='127.0.0.1', port=2525):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.handler = MessageHandler()
        self.controller = Controller(self.handler, hostname=hostname, port=port)

    def __enter__(self):
        self.controller.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.controller.stop()
        self.loop.close()

    @property
    def messages(self):
        return self.handler.messages

    @property
    def host(self):
        return self.controller.hostname

    @property
    def port(self):
        return self.controller.port


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
