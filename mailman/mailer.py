import logging
import mimetypes
import os
import smtplib
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formataddr, make_msgid, parseaddr

from six import text_type

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


class Email(object):

    def __init__(self,
        sender=None, recipients=None, _from=None, to=None, subject='',
        cc=None, bcc=None, headers=None, text_body=None, html_body=None,
        charset='utf-8', from_crt=None, from_key=None, to_crt=None):

        self.sender = parseaddr(sender)
        self.recipients = self.__parse_addr_list(recipients)
        self.subject = subject
        self.charset = charset

        if _from:
            self._from = parseaddr(_from)
        else:
            self._from = self.sender

        if to:
            self.to = self.__parse_addr_list(to)
        else:
            self.to = list(self.recipients)

        self.cc = self.__parse_addr_list(cc)
        self.bcc = self.__parse_addr_list(bcc)

        self.parts = []
        if text_body:
            self.parts.append(MIMEText(text_body, 'plain', self.charset))

        if html_body:
            self.parts.append(MIMEText(html_body, 'html', self.charset))

        self.headers = [] if headers is None else headers
        self.has_attachments = False

        self.from_key = from_key
        self.from_crt = from_crt
        self.to_crt = to_crt

    def __parse_addr_list(self, list):

        if not list:
            return []

        if isinstance(list, text_type):
            list = list.split(',')

        return [parseaddr(i) for i in list]

    @property
    def body(self):
        message = MIMEMultipart(_charset=self.charset)
        if not self.parts:
            message = MIMEText('')
        if len(self.parts) == 1 and not self.has_attachments:
            message = self.parts.pop()
        message['From'] = formataddr(self._from)
        message['Subject'] = Header(self.subject, self.charset)
        message['To'] = COMMASPACE.join([formataddr(r) for r in self.to])
        message['Message-ID'] = make_msgid()
        if self.cc:
            message['Cc'] = COMMASPACE.join([formataddr(r) for r in self.cc])

        for key in self.headers:
            message[key] = self.headers[key]

        for part in self.parts:
            message.attach(part)

        return message.as_string()

    def send(self, host='localhost', port=25, timeout=20):
        smtp = smtplib.SMTP(host=host, port=port, timeout=timeout)

        recipients = []
        recipients.extend([formataddr(i) for i in self.recipients])
        if self.cc:
            recipients.extend([formataddr(i) for i in self.cc])
        if self.bcc:
            recipients.extend([formataddr(i) for i in self.bcc])

        try:
            return smtp.sendmail(self.sender, recipients, self.body)
        except smtplib.SMTPException as e:
            logger.exception(e)

    def add_attachment(self, file_path, mime_type=None):
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)

        if mime_type is None:
            mime_type = 'application/octet-stream'

        major, minor = mime_type.split('/')
        with open(file_path, 'rb') as attachment:
            part = MIMEBase(major, minor)
            part.set_payload(attachment.read())
        encoders.encode_base64(part)

        file_name = os.path.basename(file_path)
        part.add_header('Content-Disposition',
                        'attachment; filename="{0}"'.format(file_name))

        logger.debug('Add attachment with type %s: "%s"',
                     mime_type, file_path)
        self.has_attachments = True
        self.parts.append(part)

    def __str__(self):
        recipients = COMMASPACE.join([a for n, a in self.recipients])
        return '<Email sender="{0}" recipients="{1}" subject="{2}">'.format(
            self.sender[1], recipients, self.subject)
