import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7

LOG = logging.getLogger(__name__)


def sign(message, key, cert):
    """Sign a a given message."""

    signed = MIMEMultipart('signed',
                           micalg='sha-256',
                           protocol='application/pkcs7-signature')
    signed.preamble = 'This is an S/MIME signed message\n'

    signed.attach(message)

    cann = message.as_bytes().replace(b'\n', b'\r\n')

    certstack = x509.load_pem_x509_certificates(cert.encode())
    key = serialization.load_pem_private_key(key.encode(), None)

    cms = pkcs7.PKCS7SignatureBuilder().set_data(cann).add_signer(
        certstack[-1], key, hashes.SHA256())

    for c in certstack[:-1]:
        cms = cms.add_certificate(c)

    options = [pkcs7.PKCS7Options.DetachedSignature]
    cms = cms.sign(serialization.Encoding.DER, options)

    signature = MIMEApplication(cms, 'pkcs7-signature', name='smime.p7s')
    signature.add_header('Content-Disposition',
                         'attachment',
                         filename='smime.p7s')

    signed.attach(signature)

    return signed


def encrypt(message, certs):
    """Encrypt a given message."""

    certs = x509.load_pem_x509_certificates(certs.encode())

    options = [pkcs7.PKCS7Options.Text]
    envelope = pkcs7.PKCS7EnvelopeBuilder().set_data(message.as_bytes())

    for cert in certs:
        envelope = envelope.add_recipient(cert)

    envelope = envelope.encrypt(serialization.Encoding.PEM, options)

    return MIMEApplication(envelope,
                           'pkcs7-mime',
                           smime_type='enveloped-data',
                           name='smime.p7m')
