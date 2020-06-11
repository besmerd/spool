import logging
import smtplib
import ssl

from email.utils import formataddr

from .exceptions import SpoolError


LOG = logging.getLogger(__name__)


MAIL_OUT_PREFIX = '---------- MESSAGE FOLLOWS ----------'
MAIL_OUT_SUFFIX = '------------ END MESSAGE ------------'


class MailerError(SpoolError):
    """Base class for all errors related to the mailer."""


class Mailer:
    """
    Represents an SMTP connection.
    """

    def __init__(self, host='localhost', port=1025, helo=None, timeout=5,
                 reuse_connection=False, starttls=False, debug=False):

        self.host = host
        self.port = port
        self.helo = helo
        self.timeout = timeout
        self.starttls = starttls
        self.debug = debug
        self.reuse_connection = reuse_connection
        self._server = None

    def __enter__(self):
        if self.reuse_connection:
            self._server = self._connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._server:
            self._server.quit()

    def send(self, msg, print_only=True):
        """
        Send a message.
        """
        if print_only:
            self._print(msg)
        else:
            self._send(msg)

    def _connect(self):
        LOG.debug('Connecting to server. [host=%s, port=%s, helo=%s]',
                  self.host, self.port, self.helo)
        server = smtplib.SMTP(self.host, self.port, local_hostname=self.helo,
                              timeout=self.timeout)

        if self.debug:
            server.set_debuglevel(2)

        if self.starttls:
            context = ssl.create_default_context()
            server.starttls(context=context)

        return server

    @staticmethod
    def _print(msg):
        print(MAIL_OUT_PREFIX, msg.as_string(), MAIL_OUT_SUFFIX, sep='\n')

    def _send(self, msg):

        if not self._server:
            server = self._connect()
        else:
            server = self._server

        try:
            sender = formataddr(msg.sender)

            recipients = msg.recipients + msg.cc_addrs + msg.bcc_addrs
            recipients = [formataddr(r) for r in recipients]

            server.sendmail(sender, recipients, msg.as_string())

        except smtplib.SMTPException as ex:
            raise MailerError(ex) from ex
