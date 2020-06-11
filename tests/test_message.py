import pytest

from email.parser import HeaderParser
from spool.message import Message, parse_addrs

combinations = [
    (
        {
            'sender': 'sender@example.org',
            'recipients': 'recipient@example.org'
        },
        'sender@example.org',
        'recipient@example.org',
    ),
    (
        {
            'sender': 'sender@example.com',
            'from_addr': 'sender@example.org',
            'recipients': 'recipient@example.org',
        },
        'sender@example.org',
        'recipient@example.org',
    ),
    (
        {
            'sender': 'sender@example.org',
            'to_addrs': 'recipient@example.org',
            'recipients': 'recpient@example.com',
        },
        'sender@example.org',
        'recipient@example.org',
    ),
    (
        {
            'sender': 'sender@example.com',
            'from_addr': 'sender@example.org',
            'recipients': 'recipient@example.com',
            'to_addrs': 'recipient@example.org',
        },
        'sender@example.org',
        'recipient@example.org',
    ),
]


@pytest.mark.parametrize('config, from_header, to_header', combinations)
def test_rfc822_headers(config, from_header, to_header):
    msg = Message(**config).as_string()
    parsed = HeaderParser().parsestr(msg)

    assert 'from' in parsed and parsed.get('from') == from_header
    assert 'to' in parsed and parsed.get('to') == to_header
    assert 'subject' in parsed


recipients = [
    (
        'john.doe@example.org',
        [
            ('', 'john.doe@example.org'),
        ],
    ),
    (
        '<john.doe@example.org>, Jane Doe <jane.doe@example.org>',
        [
            ('', 'john.doe@example.org'),
            ('Jane Doe', 'jane.doe@example.org'),
        ]
    ),
    (
        [
            'John Doe <john.doe@example.org>',
            'Jane Doe <jane.doe@example.org>',
        ],
        [
            ('John Doe', 'john.doe@example.org'),
            ('Jane Doe', 'jane.doe@example.org'),
        ]
    ),
]


@pytest.mark.parametrize('recipients, parsed', recipients)
def test_parse_addrs(recipients, parsed):
    assert parsed == parse_addrs(recipients)
