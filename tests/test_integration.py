import pytest

from pathlib import Path
from unittest import mock

from spool import main


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
  recipients: recipient@example.org, other@example.com

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

EXAMPLE_DIR = Path(__file__).parent / '../examples'


@mock.patch('sys.argv', ['spool', '--help'])
def test_help_flag():
    with pytest.raises(SystemExit) as error:
        main.cli()

    assert error.type == SystemExit
    assert error.value.code == 0


@mock.patch('sys.argv', ['spool', ])
def test_fail_with_no_config():
    with pytest.raises(SystemExit) as error:
        main.cli()

    assert error.type == SystemExit
    assert error.value.code == 2


def test_success_with_simple_config(smtp_server, tmp_path):

    config_1 = tmp_path / 'simple.yml'
    config_1.write_text(SIMPLE)

    config_2 = tmp_path / 'with_vars.yml'
    config_2.write_text(WITH_VARS)

    with mock.patch('sys.argv', [
        'spool', '--relay', smtp_server.host, '--port', str(smtp_server.port),
        str(config_1), str(config_2)
    ]):
        main.cli()

    assert len(smtp_server.messages) == 2


def test_success_with_loop(smtp_server, tmp_path):

    config = tmp_path / 'with_vars.yml'
    config.write_text(WITH_LOOP)

    with mock.patch('sys.argv', [
        'spool', '--relay', smtp_server.host, '--port', str(smtp_server.port),
        str(config)
    ]):
        main.cli()

    assert len(smtp_server.messages) == 3


@pytest.mark.parametrize('config', EXAMPLE_DIR.glob('*.yml'))
def test_examples(smtp_server, tmp_path, caplog, config):

    args = ['spool', '--relay', smtp_server.host,
            '--port', str(smtp_server.port), f'{config}']

    with mock.patch('sys.argv', args):
        main.cli()
        for record in caplog.records:
            assert record.levelname not in ['ERROR', 'CRITICAL']
