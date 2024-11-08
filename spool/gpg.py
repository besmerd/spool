import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import gnupg

LOG = logging.getLogger(__name__)

gpg = gnupg.GPG()

def sign(message, key_fingerprint):
    """Sign a given message with GPG."""
    signed = MIMEMultipart('signed', protocol='application/pgp-signature')
    signed.preamble = 'This is a PGP/MIME signed message\n'

    signed.attach(message)

    result = gpg.sign(message.as_string(), keyid=key_fingerprint, detach=True, clearsign=False)

    if not result:
        LOG.error('Failed to sign message with key: %s', key_fingerprint)
        raise ValueError(f'GPG signing failed for key: {key_fingerprint}')

    signature = MIMEApplication(result.data, 'pgp-signature', name='signature.asc')
    signature.add_header('Content-Disposition', 'attachment', filename='signature.asc')

    signed.attach(signature)

    return signed

def encrypt(message, recipients):
    """Encrypt a given message with GPG."""
    encrypted_data = gpg.encrypt(message.as_string(), recipients)

    if not encrypted_data.ok:
        LOG.error('Failed to encrypt message for recipients: %s', ', '.join(recipients))
        raise ValueError(f'GPG encryption failed: {encrypted_data.stderr}')

    return MIMEApplication(str(encrypted_data), 'pgp-encrypted', name='message.asc')
