import logging
import mimetypes

from email import encoders, message_from_bytes
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formataddr, make_msgid, parseaddr
from pathlib import Path

from M2Crypto import BIO, SMIME, EVP, X509
from dkim import dkim_sign

from .exceptions import SpoolError


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


class Message:

    def __init__(self, name, sender, recipients,
                 from_addr=None, to_addrs=None, subject=None, cc_addrs=None,
                 bcc_addrs=None, headers=None, text_body=None, html_body=None,
                 ical=None, dkim=None, smime=None, charset='utf-8'):

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

        self.headers = []
        if headers:
            self.headers = headers

    def attach(self, file_path):
        self.attachments.append(file_path)

    def as_string(self):
        """Return the entire message flattened as a string."""

        if self.attachments or self.ical:
            msg = self._multipart()
        else:
            msg = self._plaintext()

        msg = self._set_rfc822_headers(msg)

        for key in self.headers:
            msg[key] = self.headers[key]

        if (self.smime
            and ('from_key' in self.smime or 'from_key_path' in self.smime)
            and ('from_crt' in self.smime or 'from_crt_path' in self.smime)):
            msg = self._sign(msg)

        if self.dkim:

            for key, value in self.dkim.items():
                self.dkim[key] = value.encode()

            sig = dkim_sign(msg.as_bytes(), **self.dkim).decode()

        else:

            sig = ''

        return sig + msg.as_string()

    def _encrypt(self, msg):
        pass

    def _sign(self, msg):

        outer_headers = []
        for header, value in msg.items():

            if header.lower().startswith('content-'):
                continue

            outer_headers.append((header, value))
            del msg[header]

        bio = BIO.MemoryBuffer(msg.as_bytes())
        smime = SMIME.SMIME()

        if 'from_key' in self.smime:
            smime.pkey = EVP.load_key_string(self.smime['from_key'].encode())
        else:
            smime.pkey = EVP.load_key(self.smime['from_key_path'])

        if 'from_crt' in self.smime:
            smime.x509 = X509.load_cert_string(self.smime['from_crt'].encode())
        else:
            smime.x509 = X509.load_cert_string(self.smime['from_crt_path'])

        cms = smime.sign(bio, flags=SMIME.PKCS7_DETACHED, algo='sha256')

        bio = BIO.MemoryBuffer(msg.as_bytes())
        out = BIO.MemoryBuffer()

        smime.write(out, cms, bio)
        msg = message_from_bytes(out.read())

        del msg['MIME-Version']
        for header, value in outer_headers:
            msg[header] = value

        return msg

    def _set_rfc822_headers(self, msg):

        msg['From'] = formataddr(self.from_addr)
        msg['To'] = COMMASPACE.join([formataddr(r) for r in self.to_addrs])
        msg['Subject'] = Header(self.subject, self.charset)

        if self.cc_addrs:
            msg['Cc'] = COMMASPACE.join([formataddr(r) for r in self.cc_addrs])

        msg['Message-ID'] = make_msgid()

        return msg

    def _multipart(self):
        msg = MIMEMultipart('mixed')
        msg.attach(self._plaintext())

        if self.ical:
            part = MIMEText(self.ical, 'calendar;method=REQUEST', self.charset)
            msg.attach(part)

        for att in self.attachments:
            msg.attach(self._get_attachment_part(att))

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
                        'attachment; filename="{0}"'.format(path.name))
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
