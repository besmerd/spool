import logging
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from ctypescrypto.cipher import CipherType
from ctypescrypto.cms import EnvelopedData, Flags, SignedData
from ctypescrypto.pkey import PKey
from ctypescrypto.x509 import X509

LOG = logging.getLogger(__name__)

PEM_RE = re.compile(
    r'-----BEGIN ([A-Z0-9 ]+)-----\r?\n'
    r'(.*?)'
    r'-----END \1-----\r?\n?',
    re.DOTALL
)

SIGNED_PREAMBLE = 'This is an S/MIME signed message\n'

SKIPPED_HEADERS = [
    'Content-Type',
    'Content-Transfer-Encoding',
    'MIME-Version',
]


def parse_pem(certstack):

    certs = [
        X509(match.group(0)) for match
        in PEM_RE.finditer(certstack)
    ]

    return certs


def encode_cms(mime_part):

    mime_part['Content-Transfer-Encoding'] = 'base64'

    if mime_part.get_payload() is None:
        return mime_part

    cms = mime_part.get_payload().pem()

    match = PEM_RE.search(cms)
    if not match:
        raise ValueError('Failed to retrive cms')

    mime_part.set_payload(match.group(2))

    return mime_part


def sign(message, key, cert, detached=True):

    # FIXME
    if not detached:
        raise NotImplementedError()

    signed = MIMEMultipart(
        'signed', micalg='sha-256', protocol='application/pkcs7-signature')
    signed.preamble = SIGNED_PREAMBLE

    for header, value in message.items():
        if header in SKIPPED_HEADERS:
            LOG.debug('Skipping header: %s', header)
            continue

        del message[header]
        signed[header] = value

    signed.attach(message)

    cann = message.as_bytes().replace(b'\n', b'\r\n')

    key = PKey(privkey=key.encode())
    certstack = parse_pem(cert)

    cms = SignedData.create(
            cann, certstack[-1], key, flags=Flags.DETACHED+Flags.BINARY,
            certs=certstack[0:-1])

    signature = MIMEApplication(
        cms, 'pkcs7-signature', encode_cms, name='smime.p7s')
    signature.add_header(
        'Content-Disposition', 'attachment', filename='smime.p7s')

    signed.attach(signature)

    return signed


def encrypt(message, certs, algorithm='des3'):

    certs, cipher = parse_pem(certs), CipherType(algorithm)

    headers = []

    for header, value in message.items():
        if header in SKIPPED_HEADERS:
            LOG.debug('Skipping header: %s', header)
            continue

        del message[header]
        headers.append((header, value))

    cms = EnvelopedData.create(certs, message.as_bytes(), cipher, flags=0)

    encrypted = MIMEApplication(cms, 'pkcs7-mime', encode_cms,
                                smime_type='enveloped-data', name='smime.p7m')

    for header, value in headers:
        encrypted[header] = value

    return encrypted
