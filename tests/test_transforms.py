from email.mime.text import MIMEText
from unittest.mock import call, patch

import pytest

from spool.parser import DkimSpec, SmimeSpec
from spool.transforms import TransformError, apply_dkim, apply_smime


@patch('spool.transforms.dkim_sign')
def test_dkim_does_not_mutate_config(mock_sign):
    mock_sign.return_value = b'DKIM-Signature: v=1; test=yes\r\n'
    config = DkimSpec(
        domain='example.org',
        selector='test',
        privkey='private key',
    )

    first = apply_dkim(MIMEText('first'), config)
    second = apply_dkim(MIMEText('second'), config)

    assert config.domain == 'example.org'
    assert config.selector == 'test'
    assert config.privkey == 'private key'
    assert first['DKIM-Signature'] == 'v=1; test=yes'
    assert second['DKIM-Signature'] == 'v=1; test=yes'
    assert mock_sign.call_count == 2
    assert mock_sign.call_args.kwargs == {
        'domain': b'example.org',
        'selector': b'test',
        'privkey': b'private key',
    }


@patch('spool.transforms.encrypt')
@patch('spool.transforms.sign')
def test_smime_signs_before_encrypting(mock_sign, mock_encrypt):
    message = MIMEText('message')
    signed = MIMEText('signed')
    encrypted = MIMEText('encrypted')
    mock_sign.return_value = signed
    mock_encrypt.return_value = encrypted

    result = apply_smime(message, SmimeSpec(
        from_key='private key',
        from_crt='sender certificate',
        to_crts='recipient certificate',
    ))

    assert result is encrypted
    assert mock_sign.call_args_list == [
        call(message, 'private key', 'sender certificate')]
    assert mock_encrypt.call_args_list == [
        call(signed, 'recipient certificate')]


def test_empty_transform_configs_return_original_message():
    message = MIMEText('message')

    assert apply_smime(message, None) is message
    assert apply_dkim(message, None) is message


def test_smime_wraps_unsupported_encryption_error():
    message = MIMEText('message')

    with pytest.raises(
            TransformError, match='S/MIME encryption is not supported'):
        apply_smime(message, SmimeSpec(to_crts='recipient certificate'))
