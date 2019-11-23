import logging
import mimetypes
import os
import smtplib
import ssl
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formataddr, make_msgid, parseaddr
from email import message_from_bytes

from M2Crypto import BIO, SMIME


class Mailer:
    """
    Represents an SMTP connection.
    """

    def __init__(self, host='localhost', port=1025, timeout=5,
                 starttls=False, debug=False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.starttls = starttls
        self.debug = debug

    def send(self, msg):
        """
        Send one or a sequence of messages.
        """
        if isinstance(msg, Message):
            msg = [msg]

        try:
            server = smtplib.SMTP(self.host, self.port, timeout=self.timeout)

            if self.debug:
                server.set_debuglevel(1)

            if self.starttls:
                context = ssl.create_default_context()
                server.starttls(context=context)

            for m in msg:
                self._send(server, m)

        finally:
            server.quit()

    @staticmethod
    def _send(server, msg):

        sender = formataddr(msg.sender)

        recipients = msg.recipients + msg.cc_addrs + msg.bcc_addrs
        recipients = [formataddr(r) for r in recipients]

        server.sendmail(sender, recipients, msg.as_string())



try:
    from email import encoders
except ImportError:
    from email import Encoders as encoders

logger = logging.getLogger(__name__)

DEFAULT_ATTACHMENT_MIME_TYPE = 'application/octet-stream'

RFC5322_EMAIL_LINE_LENGTH_LIMIT = 998
ADDRESS_HEADERS = (
    'from',
    'sender',
    'reply-to',
    'to',
    'cc',
    'bcc',
    'resent-from',
    'resent-sender',
    'resent-to',
    'resent-cc',
    'resent-bcc',
)

def parseaddrs(addrs):

    if isinstance(addrs, str):
        addrs = addrs.split(',')

    if isinstance(addrs, list):
        return [parseaddr(i) for i in addrs]

    return [parseaddr(addrs)]


class Message:

    def __init__(self, sender, recipients,
                 from_addr=None, to_addrs=None, subject=None, cc_addrs=None,
                 bcc_addrs=None, headers=None, text_body=None, html_body=None,
                 ical=None, from_key=None, from_crt=None, charset='utf-8'):

        self.sender = parseaddr(sender)

        if from_addr:
            self.from_addr = parseaddr(from_addr)
        else:
            self.from_addr = self.sender

        self.recipients = parseaddrs(recipients)

        if to_addrs:
            self.to_addrs = parseaddrs(to_addrs)
        else:
            self.to_addrs = self.recipients

        if cc_addrs:
            self.cc_addrs = parseaddrs(cc_addrs)
        else:
            self.cc_addrs = []

        if bcc_addrs:
            self.bcc_addrs = parseaddrs(bcc_addrs)
        else:
            self.bcc_addrs = []

        self.subject = subject
        self.charset = charset

        self.html_body = html_body
        self.text_body = text_body
        self.ical = ical

        self.from_key = from_key
        self.from_crt = from_crt

        self.attachments = []

        self.headers = []
        if headers:
            self.headers = headers

    def attach(self, file_path):
        self.attachments.append(file_path)

    def as_string(self):

        if self.attachments or self.ical:
            msg = self._multipart()
        else:
            msg = self._plaintext()

        msg = self._set_rfc822_headers(msg)

        for key in self.headers:
            msg[key] = self.headers[key]

        if self.from_key and self.from_crt:
            msg = self._sign(msg, self.from_key, self.from_crt)

        return msg.as_string()

    def _encrypt(self, msg):
        pass

    @staticmethod
    def _sign(msg, from_key, from_crt):
        outer_headers = []
        for header, value in msg.items():
            if header == 'Content-Type':
                continue
            outer_headers.append((header, value))
            del msg[header]
        bio = BIO.MemoryBuffer(msg.as_bytes())
        smime = SMIME.SMIME()
        smime.load_key(from_key, from_crt)
        cms = smime.sign(bio, flags=SMIME.PKCS7_DETACHED)
        bio = BIO.MemoryBuffer(msg.as_bytes())
        out = BIO.MemoryBuffer()
        smime.write(out, cms, bio)
        msg = message_from_bytes(out.read())
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

        for a in self.attachments:
            msg.attach(self._get_attachment_part(a))

        return msg

    @staticmethod
    def _get_attachment_part(file_path):

        mime_type, encoding = mimetypes.guess_type(file_path)

        if mime_type is None or encoding is not None:
            mime_type = DEFAULT_ATTACHMENT_MIME_TYPE

        part = MIMEBase(*mime_type.split('/'))

        with open(file_path, 'rb') as attachment:
            part.set_payload(attachment.read())

        encoders.encode_base64(part)

        file_name = os.path.basename(file_path)
        part.add_header('Content-Disposition',
                        'attachment; filename="{0}"'.format(file_name))
        return part

    def _plaintext(self):

        if not self.html_body:
            msg = MIMEText(self.text_body, 'plain', self.charset)
        else:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(self.text_body, 'plain', self.charset))
            msg.attach(MIMEText(self.html_body, 'html', self.charset))

        return msg

    def __str__(self):
        recipients = COMMASPACE.join([a for n, a in self.recipients])
        return '<Email sender="{0}" recipients="{1}" subject="{2}">'.format(
            self.sender[1], recipients, self.subject)
