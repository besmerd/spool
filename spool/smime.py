import re
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

PEM_RE = re.compile(
    r'-----BEGIN ([A-Z0-9 ]+)-----\r?\n'
    r'(.*?)'
    r'-----END \1-----\r?\n?',
    re.DOTALL,
)

SIGNED_PREAMBLE = 'This is an S/MIME signed message\n'


def parse_pem(certstack):
    """Extract certificates from a PEM stack."""

    return [
        x509.load_pem_x509_certificate(match.group(0).encode('ascii'))
        for match in PEM_RE.finditer(certstack)
    ]


def encode_cms(mime_part):
    """Convert a PEM CMS payload to MIME base64 content."""

    mime_part['Content-Transfer-Encoding'] = 'base64'
    if mime_part.get_payload() is None:
        return mime_part

    match = PEM_RE.search(mime_part.get_payload())
    if not match:
        raise ValueError('Failed to retrieve CMS payload')

    mime_part.set_payload(match.group(2))
    return mime_part


def sign(message, key, cert):
    """Return a detached S/MIME signature around a message."""

    signed = MIMEMultipart(
        'signed', micalg='sha-256', protocol='application/pkcs7-signature')
    signed.preamble = SIGNED_PREAMBLE
    signed.attach(message)

    canonical_message = message.as_bytes().replace(b'\n', b'\r\n')
    certificates = parse_pem(cert)
    private_key = serialization.load_pem_private_key(
        key.encode('ascii'), None)

    builder = pkcs7.PKCS7SignatureBuilder().set_data(
        canonical_message).add_signer(
            certificates[-1], private_key, hashes.SHA256())
    for certificate in certificates[:-1]:
        builder = builder.add_certificate(certificate)

    cms = builder.sign(
        serialization.Encoding.PEM,
        [pkcs7.PKCS7Options.DetachedSignature],
    )
    signature = MIMEApplication(
        cms, 'pkcs7-signature', encode_cms, name='smime.p7s')
    signature.add_header(
        'Content-Disposition', 'attachment', filename='smime.p7s')
    signed.attach(signature)

    return signed


def encrypt(_message, _certs):
    """Encrypt a message for the supplied certificates."""

    raise NotImplementedError('S/MIME encryption is not implemented')
