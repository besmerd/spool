from email.parser import HeaderParser

import pytest

from spool.message import Message, parse_addrs

combinations = [
    (
        {
            'name': 'test',
            'envelope_from': 'sender@example.org',
            'envelope_recipients': 'recipient@example.org'
        },
        'sender@example.org',
        'recipient@example.org',
    ),
    (
        {
            'name': 'test',
            'envelope_from': 'sender@example.com',
            'from_addr': 'sender@example.org',
            'envelope_recipients': 'recipient@example.org',
        },
        'sender@example.org',
        'recipient@example.org',
    ),
    (
        {
            'name': 'test',
            'envelope_from': 'sender@example.org',
            'to_addrs': 'recipient@example.org',
            'envelope_recipients': 'recpient@example.com',
        },
        'sender@example.org',
        'recipient@example.org',
    ),
    (
        {
            'name': 'test',
            'envelope_from': 'sender@example.com',
            'from_addr': 'sender@example.org',
            'envelope_recipients': 'recipient@example.com',
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


def test_envelope_and_message_headers_are_distinct():
    message = Message(
        name='spoofed sender',
        envelope_from='Envelope Sender <bounce@attacker.example>',
        envelope_recipients='gateway-test@example.org',
        from_addr='CEO <ceo@company.example>',
        to_addrs='Employee <employee@company.example>',
    )

    assert message.envelope_from == (
        'Envelope Sender', 'bounce@attacker.example')
    assert message.envelope_recipients == [
        ('', 'gateway-test@example.org')]

    parsed = HeaderParser().parsestr(message.as_string())
    assert parsed['From'] == 'CEO <ceo@company.example>'
    assert parsed['To'] == 'Employee <employee@company.example>'
