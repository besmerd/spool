import pytest

from unittest import mock

from mailman import main


SIMPLE = '''\
---
mails:
  - name: simple
    description: A simple text message
    sender: sender@example.org
    recipients: recipient@example.org
    subject: Simple Text Message
    text_body: |
        Just a simple text message.
'''

WITH_VARS = '''\
---
defaults:
  sender: sender@example.org
  recipients: recipient@example.org

vars:
  subject: Simple Text Message

mails:
  - name: with-vars
    subject: '{{ subject|upper }}'
    text_body: |
        Just a simple text message.
'''

WITH_LOOP = '''\
---
defaults:
  sender: sender@example.org

vars:
  friends:
    - Ben
    - Karol
    - Steve

mails:
  - name: with-loop
    subject: Simple Text Message
    recipients: '{{ item }}'
    text_body: |
        Just a simple text message.

    loop: '{{ friends }}'
'''


@mock.patch('sys.argv', ['mailman', '--help'])
def test_help_flag():
    with pytest.raises(SystemExit) as error:
        main.cli()

    assert error.type == SystemExit
    assert error.value.code == 0


@mock.patch('sys.argv', ['mailman', ])
def test_fail_with_no_config():
    with pytest.raises(SystemExit) as error:
        main.cli()

    assert error.type == SystemExit
    assert error.value.code == 2


def test_success_with_simple_config(smtpd, tmp_path):

    config_1 = tmp_path / 'simple.yml'
    config_1.write_text(SIMPLE)

    config_2 = tmp_path / 'with_vars.yml'
    config_2.write_text(WITH_VARS)

    with mock.patch('sys.argv', ['mailman', '--relay',
                    f'{smtpd.host}:{smtpd.port}', str(config_1), str(config_2)]):
        main.cli()

    assert len(smtpd.messages) == 2


def test_success_with_loop(smtpd, tmp_path):

    config = tmp_path / 'with_vars.yml'
    config.write_text(WITH_LOOP)

    with mock.patch('sys.argv', ['mailman', '--relay',
                    f'{smtpd.host}:{smtpd.port}', str(config)]):
        main.cli()

    assert len(smtpd.messages) == 3
