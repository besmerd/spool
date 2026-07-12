"""Message transforms applied after MIME content is built."""

from email.message import Message as EmailMessage

from dkim import dkim_sign

from .exceptions import SpoolError
from .parser import DkimSpec, SmimeSpec
from .smime import encrypt, sign


class TransformError(SpoolError):
    """A configured message transform could not be applied."""


def apply_smime(
        message: EmailMessage,
        config: SmimeSpec | None) -> EmailMessage:
    """Apply configured S/MIME signing and encryption."""

    if not config:
        return message

    if config.from_key and config.from_crt:
        message = sign(message, config.from_key, config.from_crt)

    if config.to_crts:
        try:
            message = encrypt(message, config.to_crts)
        except NotImplementedError as ex:
            raise TransformError(
                'S/MIME encryption is not supported') from ex

    return message


def apply_dkim(
        message: EmailMessage,
        config: DkimSpec | None) -> EmailMessage:
    """Add a DKIM signature without mutating its configuration."""

    if not config:
        return message

    header = dkim_sign(
        message.as_bytes(),
        domain=config.domain.encode(),
        selector=config.selector.encode(),
        privkey=config.privkey.encode(),
    ).decode()
    name, value = header.split(':', 1)
    message[name] = value.strip()

    return message
