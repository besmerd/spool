import asyncore
import smtpd
import threading
from collections import namedtuple

import pytest

RecordedMessage = namedtuple(
    'RecordedMessage',
    'peer mailfrom rcpttos data',
)


class MailServer(smtpd.SMTPServer, threading.Thread):

    def __init__(self, host='localhost', port=0):

        smtpd.SMTPServer.__init__(self, (host, port), None, decode_data=True)

        self.host, self.port = self.socket.getsockname()[0:2]

        self.messages = []

        # initialise thread
        self._stopevent = threading.Event()
        self.threadName = self.__class__.__name__
        threading.Thread.__init__(self, name=self.threadName)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):

        self.stop()

    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):

        recorded = RecordedMessage(
            peer=peer, mailfrom=mailfrom, rcpttos=rcpttos, data=data
        )

        self.messages.append(recorded)

    def run(self):

        while not self._stopevent.is_set():
            asyncore.loop(timeout=0.001, count=1)

    def stop(self, timeout=None):

        self._stopevent.set()
        threading.Thread.join(self, timeout)
        self.close()

    def __del__(self):

        self.stop()

    def __repr__(self):

        return '<smtp.Server %s:%s>' % self.addr


@pytest.fixture
def smtp_server():
    with MailServer() as server:
        yield server
