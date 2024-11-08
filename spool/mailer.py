import itertools
import logging
import re
import smtplib
import socket
import ssl
from email.utils import formataddr

from dns.exception import Timeout
from dns.resolver import NXDOMAIN, Cache, Resolver

from .exceptions import SpoolError

LOG = logging.getLogger(__name__)

MAIL_OUT_PREFIX = '---------- MESSAGE FOLLOWS ----------'
MAIL_OUT_SUFFIX = '------------ END MESSAGE ------------'
DOMAIN_LITERAL = re.compile(r'\[(?P<ip_address>(\d{1,3}\.){3}\d{1,3})\]')


class MailerError(SpoolError):
    """Base class for all errors related to the mailer."""


class RemoteNotFoundError(MailerError):
    """Remote server could not be evaluated."""


class ResolverTimeoutError(MailerError):
    """Resolver query timed out."""


class Mailer:
    """Represents an SMTP connection."""

    def __init__(self,
                 relay=None,
                 port=25,
                 helo=None,
                 timeout=5,
                 debug=False,
                 starttls=False,
                 nameservers=None,
                 no_cache=False):

        self.port = port
        self.relay = relay
        self.helo = helo or self._get_helo_name()
        self.timeout = timeout
        self.starttls = starttls
        self.debug = debug
        self.no_cache = no_cache
        self.reorder_recipients = True

        self.resolver = self._configure_resolver(nameservers)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def send(self, msg, print_only=False):
        """Send a message.

        Args:
            msg: The message to send (or print to console)
            print_only (:obj: `bool`, optional): Whether to print the
                message to console instead of sending to remote.
        """

        if print_only:
            self._dump_message(msg)
            return

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
                    host = self._get_remote(domain)

                except RemoteNotFoundError as err:
                    LOG.error('Failed to send message: %s [name=%s]', err,
                              msg.name)
                    continue

                self._send_message(host, sender, list(recipients), msg)

    def _configure_resolver(self, nameservers):
        """Configure the DNS resolver."""
        resolver = Resolver(configure=False) if nameservers else Resolver()

        if nameservers:
            resolver.nameservers = [n.strip() for n in nameservers.split(',')]

        if not self.no_cache:
            resolver.cache = Cache()

        return resolver

    @staticmethod
    def _get_helo_name():
        """Retrieve the helo/ehlo name based on the hostname."""
        fqdn = socket.getfqdn()
        if '.' in fqdn:
            return fqdn
        return f'[{socket.gethostbyname(socket.gethostname())}]'

    def _get_remote(self, domain, lifetime=10.0):
        """Returns the mail exchange server for a given domain."""

        match = DOMAIN_LITERAL.fullmatch(domain)
        if match:
            return match.group('ip_address')

        try:
            answers = self.resolver.query(domain, 'MX', lifetime=lifetime)
            peer = min(answers, key=lambda rdata: rdata.preference).exchange
            return peer.to_text().rstrip('.') or peer.to_text()

        except Timeout as exc:
            raise ResolverTimeoutError(
                'Query for mx record timed out. '
                f'[domain={domain}, timeout={lifetime}s]') from exc

        except NXDOMAIN as exc:
            raise RemoteNotFoundError(
                f'No mx record found for domain. [domain={domain}]') from exc

    def _connect(self, host, port):
        """Connect to the SMTP server."""
        LOG.info('Connecting to remote server. [host=%s, port=%s, helo=%s]',
                 host, port, self.helo)

        try:
            server = smtplib.SMTP(host,
                                  port,
                                  timeout=self.timeout,
                                  local_hostname=self.helo)

        except ConnectionRefusedError as exc:
            raise MailerError(
                f'Remote refused connection. [host={host}, port={port}]'
            ) from exc

        except socket.timeout as exc:
            raise MailerError(
                f'Timeout while connecting to remote. [host={host}, port={port}]'
            ) from exc

        if self.debug:
            server.set_debuglevel(2)

        if self.starttls:
            context = ssl.create_default_context()
            try:
                server.starttls(context=context)
            except smtplib.SMTPNotSupportedError:
                LOG.warning(
                    ('No support for STARTTLS command by remote server. '
                     '[host=%s, port=%s]'), host, port)

        return server

    def _send_message(self, host, sender, recipients, msg):
        """Send a message to a single remote mail server"""

        try:
            connection = self._connect(host, self.port)
            refused = connection.sendmail(sender, recipients, msg.as_string())

        except smtplib.SMTPResponseException as err:

            if isinstance(err, smtplib.SMTPSenderRefused):
                LOG.error(('Failed to send message: Sender rejected.'
                           '[name=%s, host=%s, port=%s]'), msg.name, host,
                          self.port)
            else:
                LOG.error(('Error while sending message: %s - %s '
                           '[name=%s, host=%s, port=%s]'), err.smtp_code,
                          err.smtp_error.decode(), msg.name, host, self.port)

        except smtplib.SMTPException as exc:

            if isinstance(exc, smtplib.SMTPRecipientsRefused):
                err = 'Remote refused all recipients.'

            elif isinstance(exc, smtplib.SMTPServerDisconnected):
                err = 'Connection closed by remote host.'

            LOG.error('Failed to send message: %s [name=%s, host=%s, port=%s]',
                      err, msg.name, host, self.port)

        else:
            for recipient, (code, response) in refused.items():
                LOG.warning('Remote refused recipient: %s [host=%s, port=%s]',
                            recipient, host, self.port)

            LOG.info('Message sent. [name=%s, host=%s, port=%s]', msg.name,
                     host, self.port)

    @staticmethod
    def _dump_message(msg):
        """Print a message to console."""
        print(MAIL_OUT_PREFIX, msg.as_string(), MAIL_OUT_SUFFIX, sep='\n')
