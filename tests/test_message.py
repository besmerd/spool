import pytest
import yaml

from pathlib import Path
from unittest.mock import patch

from email.parser import HeaderParser
from spool.message import Message, parse_addrs

#combinations = [
#    (
#        {
#            'sender': 'sender@example.org',
#            'recipients': 'recipient@example.org'
#        },
#        'sender@example.org',
#        'recipient@example.org',
#    ),
#    (
#        {
#            'sender': 'sender@example.com',
#            'from_addr': 'sender@example.org',
#            'recipients': 'recipient@example.org',
#        },
#        'sender@example.org',
#        'recipient@example.org',
#    ),
#    (
#        {
#            'sender': 'sender@example.org',
#            'to_addrs': 'recipient@example.org',
#            'recipients': 'recpient@example.com',
#        },
#        'sender@example.org',
#        'recipient@example.org',
#    ),
#    (
#        {
#            'sender': 'sender@example.com',
#            'from_addr': 'sender@example.org',
#            'recipients': 'recipient@example.com',
#            'to_addrs': 'recipient@example.org',
#        },
#        'sender@example.org',
#        'recipient@example.org',
#    ),
#]
#
#
#@pytest.mark.parametrize('config, from_header, to_header', combinations)
#def test_rfc822_headers(config, from_header, to_header):
#    msg = Message(**config).as_string()
#    parsed = HeaderParser().parsestr(msg)
#
#    assert 'from' in parsed and parsed.get('from') == from_header
#    assert 'to' in parsed and parsed.get('to') == to_header
#    assert 'subject' in parsed
#
#
#recipients = [
#    (
#        'john.doe@example.org',
#        [
#            ('', 'john.doe@example.org'),
#        ],
#    ),
#    (
#        '<john.doe@example.org>, Jane Doe <jane.doe@example.org>',
#        [
#            ('', 'john.doe@example.org'),
#            ('Jane Doe', 'jane.doe@example.org'),
#        ]
#    ),
#    (
#        [
#            'John Doe <john.doe@example.org>',
#            'Jane Doe <jane.doe@example.org>',
#        ],
#        [
#            ('John Doe', 'john.doe@example.org'),
#            ('Jane Doe', 'jane.doe@example.org'),
#        ]
#    ),
#]
#
#
#@pytest.mark.parametrize('recipients, parsed', recipients)
#def test_parse_addrs(recipients, parsed):
#    assert parsed == parse_addrs(recipients)


def messages():
    path = Path(__file__).parent / 'data_message.yml'
    with open(path) as fh:
        messages = yaml.safe_load(fh)

    for msg in messages:
        yield msg['config'], msg['expected']


@pytest.mark.parametrize('config, expected', messages())
def test_generation(config, expected):
    with patch('spool.message.make_msgid') as mock_msgid:
        mock_msgid.return_value = '<1.41421356237@example.org>'
        with patch('random.randrange') as mock_boundary:
            mock_boundary.return_value = 1
            message = Message(**config)
            assert message.as_string() == expected
