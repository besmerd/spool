import itertools
import logging
import re
import smtplib
import socket
import ssl
from email.utils import formataddr

from dns.resolver import NXDOMAIN, Resolver

from .exceptions import SpoolError

LOG = logging.getLogger(__name__)


MAIL_OUT_PREFIX = '---------- MESSAGE FOLLOWS ----------'
MAIL_OUT_SUFFIX = '------------ END MESSAGE ------------'

DOMAIN_LITERAL = re.compile(r'\[(?P<ip_address>(\d{1,3}\.){3}\d{1,3})\]')


class MailerError(SpoolError):
    """Base class for all errors related to the mailer."""


class RemoteNotFoundError(MailerError):
    """Remote server could not be evaluated."""


class Mailer:
    """Represents an SMTP connection."""

    def __init__(self, relay=None, port=25, helo=None, timeout=5,
                 starttls=False, nameservers=None, debug=False):

        self.port = port
        self.relay = relay

        if helo is None:
            self.helo = self.get_helo_name()
        else:
            self.helo = helo

        self.timeout = timeout
        self.starttls = starttls
        self.nameservers = nameservers
        self.debug = debug

        # TODO: Add option to parser
        self.reorder_recipients = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def send(self, msg, print_only=True):
        """Send a message.

        Args:
            msg: The message to send (or print to console)
            print_only (:obj: `bool`, optional): Whether to print the
                message to console instead of sending to remote.
        """

        if print_only:
            self.dump(msg)

        sender = formataddr(msg.sender)

        recipients = msg.recipients + msg.cc_addrs + msg.bcc_addrs
        recipients = [formataddr(r) for r in recipients]

        if self.relay:
            self._send_message(self.relay, sender, recipients, msg)

        else:
            def domain(address):
                return address.split('@', 1)[-1]

            if self.reorder_recipients:
                recipients = sorted(recipients, key=domain)

            for domain, recipients in itertools.groupby(recipients, domain):

                try:
                    host = self._get_remote(domain, self.nameservers)

                except RemoteNotFoundError as err:
                    LOG.error(
                        'Failed to send message: %s [name=%s]', err, msg.name)
                    continue

                self._send_message(host, sender, list(recipients), msg)

    @staticmethod
    def get_helo_name():
        """Retrive the helo/ehlo name based on the hostname."""

        fqdn = socket.getfqdn()
        if '.' in fqdn:
            return fqdn

        # Use a domain literal for the EHLO/HELO verb, as specified in RFC 2821
        address = '127.0.0.1'
        try:
            address = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            pass

        return f'[{address}]'

    @staticmethod
    def _get_remote(domain, nameservers=None):

        match = DOMAIN_LITERAL.fullmatch(domain)
        if match:
            return match.group('ip_address')

        if nameservers:
            resolver = Resolver(configure=False)
            resolver.nameservers = [n.strip() for n in nameservers.split(',')]

        else:
            resolver = Resolver()

        try:
            answers = resolver.query(domain, 'MX')
            peer = min(answers, key=lambda rdata: rdata.preference).exchange
            return peer.to_text().rstrip('.')

        except NXDOMAIN:
            raise RemoteNotFoundError(
                f'No mx record found for domain: {domain}')

    def _connect(self, host, port):

        LOG.info('Connecting to remote server. [host=%s, port=%s, helo=%s]',
                 host, port, self.helo)

        server = smtplib.SMTP(host, port, timeout=self.timeout,
                              local_hostname=self.helo)

        if self.debug:
            server.set_debuglevel(2)

        if self.starttls:
            context = ssl.create_default_context()
            try:
                server.starttls(context=context)
            except smtplib.SMTPNotSupportedError:
                LOG.warning(
                    ('No support for STARTTLS command by remote server. '
                     '[host=%s, port=%s]'), host, port
                )

        return server

    def _send_message(self, host, sender, recipients, msg):
        """Send a message to a single remote mail server"""

        try:
            connection = self._connect(host, self.port)
            refused = connection.sendmail(sender, recipients, msg.as_string())

        except smtplib.SMTPResponseException as err:
            LOG.error(('Error while sending message: %s - %s '
                       '[name=%s, host=%s, port=%s]'), err.smtp_code,
                      err.smtp_error.decode(), msg.name, host, self.port)

        except smtplib.SMTPException as err:
            LOG.error('Failed to send message: %s [name=%s, host=%s, port=%s]',
                      err, msg.name, host, self.port)

        else:
            for recipient, (code, response) in refused.items():
                LOG.warning('Remote refused recipient: %s - %s '
                            '[recpient=%s, host=%s, port=%s]',
                            code, response, recipient, host, self.port)

            LOG.info('Message sent. [name=%s, host=%s, port=%s]',
                     msg.name, host, self.port)

    @staticmethod
    def dump(msg):
        """Print a message to console.

        Prints a given message to console in Internet Message Format (IMF).

        Args:
            msg: A message.
        """

        print(MAIL_OUT_PREFIX, msg.as_string(), MAIL_OUT_SUFFIX, sep='\n')
