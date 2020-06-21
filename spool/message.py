import logging
import mimetypes
from collections import OrderedDict
from collections.abc import MutableMapping
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import (COMMASPACE, formataddr, formatdate, make_msgid,
                         parseaddr)
from pathlib import Path

from dkim import dkim_sign

from .exceptions import SpoolError
from .smime import encrypt, sign

LOG = logging.getLogger(__name__)
DEFAULT_ATTACHMENT_MIME_TYPE = 'application/octet-stream'


def parse_addrs(addrs):

    if isinstance(addrs, str):
        addrs = addrs.split(',')

    if isinstance(addrs, list):
        return [parseaddr(i) for i in addrs]

    return [parseaddr(addrs)]


class MessageError(SpoolError):
    """Base class for essage errors."""


class EmailHeaders(MutableMapping):
    """Copied from requests CaseInsensitiveDict"""

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

    def __init__(self, name, sender, recipients,
                 from_addr=None, to_addrs=None, subject=None, cc_addrs=None,
                 bcc_addrs=None, headers=None, text_body=None, html_body=None,
                 ical=None, dkim=None, smime=None, charset='utf-8'):

        # FIXME
        self.make_msgid = True

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

        self._headers = EmailHeaders(headers)

    @property
    def headers(self):

        headers = EmailHeaders({
            'From': formataddr(self.from_addr),
            'To': COMMASPACE.join([formataddr(r) for r in self.to_addrs]),
            'Subject': Header(self.subject, self.charset),
            'Date': formatdate(localtime=True),
            'Message-ID': make_msgid(),
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
        """Add file to message attachments."""

        self.attachments.append(file_path)

    def as_string(self):
        """Return the entire message flattened as a string."""

        if self.attachments or self.ical:
            msg = self._multipart()
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

        for a in self.attachments:
            msg.attach(self._get_attachment_part(a))

        return msg

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
        return '[sender={0}, recipients={1}, subject={2}]'.format(
            self.sender[1], recipients, self.subject)
