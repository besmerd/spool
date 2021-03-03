import logging
import mimetypes
from collections import OrderedDict
from collections.abc import MutableMapping
from email import encoders, message_from_string
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from pathlib import Path

from dkim import dkim_sign

from .exceptions import SpoolError
from .smime import encrypt, sign

LOG = logging.getLogger(__name__)
DEFAULT_ATTACHMENT_MIME_TYPE = 'application/octet-stream'
COMMASPACE = ', '


def parse_addrs(addrs):
    """Parses a comma separated string to list of email addresses.

    Wrapper arround pythons `email.utils.parseaddr` function to parse a
    comma separated list of email addresses.

    Args:
        addrs: Comma separated string or list of email addresses to parse

    Returns:
        list: A list of tuples consiting of *realname* and *email address*
            parts

    Examples:
        >>> parse_addrs('john doe <john@example.com>, jane.doe@example.com')
        [('john doe', 'john@example.com'), ('', 'jane.doe@example.com')]
        >>> parse_addrs(', john doe <john.doe@example.com>')
        [('john doe', 'john.doe@example.com')]
    """

    if isinstance(addrs, str):
        addrs = addrs.split(',')

    if isinstance(addrs, list):
        return [parseaddr(item) for item in addrs if item]

    raise TypeError(f'Expected str or list, received: {type(addrs)}')


class MessageError(SpoolError):
    """Base class for message related errors."""


class EmailHeaders(MutableMapping):
    """Case insensitive dictionary to store email headers.

    Copied from Requests CaseInsensitiveDict.

    .._ Requests:
        https://requests.readthedocs.io
    """

    def __init__(self, data=None, **kwargs):
        self._store = OrderedDict()
        if data is None:
            data = {}

        self.update(data, **kwargs)

    def __setitem__(self, key, value):
        self._store[key.lower()] = (key, value)

    def __getitem__(self, key):
        return self._store[key.lower()][1]

    def __delitem__(self, key):
        del self._store[key.lower()]

    def __iter__(self):
        return (key for key, value in self._store.values())

    def __len__(self):
        return len(self._store)

    def __repr__(self):
        return str(dict(self.items()))


class Message:
    """Represents a single email message."""

    def __init__(self, name, sender, recipients,
                 from_addr=None, to_addrs=None, subject=None, cc_addrs=None,
                 bcc_addrs=None, headers=None, text_body=None, html_body=None,
                 ical=None, dkim=None, smime=None, eml=None, charset='utf-8'):

        self.name = name

        self.sender = parseaddr(sender)

        if from_addr:
            self.from_addr = parseaddr(from_addr)
        else:
            self.from_addr = self.sender

        self.recipients = parse_addrs(recipients)

        if to_addrs:
            self.to_addrs = parse_addrs(to_addrs)
        else:
            self.to_addrs = self.recipients

        if cc_addrs:
            self.cc_addrs = parse_addrs(cc_addrs)
        else:
            self.cc_addrs = []

        if bcc_addrs:
            self.bcc_addrs = parse_addrs(bcc_addrs)
        else:
            self.bcc_addrs = []

        self.subject = subject
        self.charset = charset

        self.html_body = html_body
        self.text_body = text_body
        self.ical = ical

        self.dkim = dkim
        self.smime = smime

        self.attachments = []

        self.eml = eml

        self._headers = EmailHeaders(headers)

    @property
    def headers(self):
        """Get the message headers."""

        headers = EmailHeaders({
            'From': formataddr(self.from_addr),
            'To': COMMASPACE.join([formataddr(r) for r in self.to_addrs]),
            'Subject': Header(self.subject, self.charset),
            'Date': formatdate(localtime=True),
            # do not call make_msgid unless it's required, since make_msgid
            # depends on dns resolution on the hostname
            'Message-ID': make_msgid() if 'message-id' not in self._headers
                          else self._headers['message-id'],
        })

        if self.cc_addrs:
            headers['Cc'] = COMMASPACE.join(
                [formataddr(r) for r in self.cc_addrs])

        for name, value in self._headers.items():

            if name in headers and value is None:
                del headers[name]

            else:
                headers[name] = value

        return headers

    def attach(self, file_path):
        """Add file to message attachments.

        Adds a given path to the set of files which are appended to
        the generated message when the method `as_string` is called.

        Args:
            file_path (str): relative or absolute path to the file.
        """

        self.attachments.append(file_path)

    def as_string(self):
        """Return the entire message flattened as a string.

        Returns:
            str: The message as Internet Message Format (IMF)
                formatted string.
        """

        if self.attachments or self.ical:
            msg = self._multipart()
        elif self.eml:
            msg = self._get_eml(self.eml)
        else:
            msg = self._plaintext()

        if self.smime:
            if 'from_key' in self.smime and 'from_crt' in self.smime:
                msg = sign(msg, self.smime['from_key'], self.smime['from_crt'])

            if 'to_crts' in self.smime:
                msg = encrypt(msg, self.smime['to_crts'])

        for name, value in self.headers.items():
            msg[name] = value

        if self.dkim:

            for key, value in self.dkim.items():
                self.dkim[key] = value.encode()

            dkim_header = dkim_sign(msg.as_bytes(), **self.dkim).decode()
            name, value = dkim_header.split(':', 1)
            msg[name] = value

        return msg.as_string()

    def _multipart(self):
        msg = MIMEMultipart('mixed')
        msg.attach(self._plaintext())

        if self.ical:
            part = MIMEText(self.ical, 'calendar;method=REQUEST', self.charset)
            msg.attach(part)

        for attachment in self.attachments:
            msg.attach(self._get_attachment_part(attachment))

        return msg

    @staticmethod
    def _get_eml(file_path):

        path = Path(file_path)
        if not path.is_file():
            raise MessageError('File not found: %s' % file_path)

        from jinja2 import Template
        with open(path) as fh:
            template = Template(fh.read())

        rendered = template.render()

        return message_from_string(rendered)

    @staticmethod
    def _get_attachment_part(file_path):

        path = Path(file_path)
        if not path.is_file():
            raise MessageError('File not found: %s' % file_path)

        mime_type, encoding = mimetypes.guess_type(str(file_path))

        if mime_type is None or encoding is not None:
            mime_type = DEFAULT_ATTACHMENT_MIME_TYPE

        part = MIMEBase(*mime_type.split('/'))

        with open(file_path, 'rb') as attachment:
            part.set_payload(attachment.read())

        encoders.encode_base64(part)

        part.add_header('Content-Disposition',
                        'attachment', filename=path.name)

        return part

    def _plaintext(self):

        if not self.html_body:
            msg = MIMEText(self.text_body, 'plain', self.charset)

        elif not self.text_body:
            msg = MIMEText(self.html_body, 'html', self.charset)

        else:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(self.text_body, 'plain', self.charset))
            msg.attach(MIMEText(self.html_body, 'html', self.charset))

        return msg

    def __str__(self):
        recipients = COMMASPACE.join([a for n, a in self.recipients])
        return (f'[sender={self.sender[1]}, recipients={recipients}, '
                f'subject={self.subject}]')
