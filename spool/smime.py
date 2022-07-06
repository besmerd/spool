import logging
import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from ctypescrypto.cipher import CipherType
from ctypescrypto.cms import EnvelopedData, Flags, SignedData
from ctypescrypto.pkey import PKey
from ctypescrypto.x509 import X509

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

LOG = logging.getLogger(__name__)

PEM_RE = re.compile(
    r'-----BEGIN ([A-Z0-9 ]+)-----\r?\n'
    r'(.*?)'
    r'-----END \1-----\r?\n?',
    re.DOTALL
)

SIGNED_PREAMBLE = 'This is an S/MIME signed message\n'


def parse_pem(certstack):
    """Extract PEM strings from *certstack*."""

    certs = [
        x509.load_pem_x509_certificate(match.group(0).encode('ascii')) for match
        in PEM_RE.finditer(certstack)
    ]

    return certs


def parse_pem_old(certstack):
    """Extract PEM strings from *certstack*."""

    certs = [
        X509(match.group(0)) for match
        in PEM_RE.finditer(certstack)
    ]

    return certs


def encode_cms(mime_part):
    """Encodes a cms structure"""

    mime_part['Content-Transfer-Encoding'] = 'base64'

    if mime_part.get_payload() is None:
        return mime_part

    cms = mime_part.get_payload()

    match = PEM_RE.search(cms)
    if not match:
        raise ValueError('Failed to retrive cms')

    mime_part.set_payload(match.group(2))

    return mime_part


def encode_cms_old(mime_part):
    """Encodes a cms structure"""

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
    """Sign a a given message."""

    # FIXME
    if not detached:
        raise NotImplementedError()

    signed = MIMEMultipart(
        'signed', micalg='sha-256', protocol='application/pkcs7-signature')
    signed.preamble = SIGNED_PREAMBLE

    signed.attach(message)

    cann = message.as_bytes().replace(b'\n', b'\r\n')

    certstack = parse_pem(cert)
    key = serialization.load_pem_private_key(key.encode('ascii'), None)

    cms = pkcs7.PKCS7SignatureBuilder().set_data(cann).add_signer(
        certstack[-1], key, hashes.SHA256()
    )

    for c in certstack[:-1]:
        cms = cms.add_certificate(c)

    options = [
        pkcs7.PKCS7Options.DetachedSignature,
    ]

    cms = cms.sign(
        serialization.Encoding.PEM, options
    )

    signature = MIMEApplication(
        cms, 'pkcs7-signature', encode_cms, name='smime.p7s')
    signature.add_header(
        'Content-Disposition', 'attachment', filename='smime.p7s')

    signed.attach(signature)

    return signed


def encrypt(message, certs, algorithm='des3'):
    """Encrypt a given message."""

    certs, cipher = parse_pem_old(certs), CipherType(algorithm)

    cms = EnvelopedData.create(certs, message.as_bytes(), cipher, flags=0)

    encrypted = MIMEApplication(cms, 'pkcs7-mime', encode_cms_old,
                                smime_type='enveloped-data', name='smime.p7m')

    return encrypted
