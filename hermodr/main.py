from __future__ import print_function

import sys
import os
import argparse
import logging

from parser import Config
from mailer import Email


logging.basicConfig(format='%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAIL_PREFIX = '---------- MESSAGE FOLLOWS ----------'
MAIL_SUFFIX = '------------ END MESSAGE ------------'


def parse_args(args):
    parser = argparse.ArgumentParser(description='Send mails with YAML.')

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='create, but do not send messages',
    )

    parser.add_argument(
        'path',
        nargs='+',
        metavar='config',
        help='path of hermodr config',
    )

    return parser.parse_args(args)


def main():
    args = parse_args(sys.argv[1:])
    for path in args.path:
        if not os.path.isfile(path):
            logging.warning('No such file "%s", skipping.', path)
            continue
        config = Config.load(path)
        for mail in config.mails:

            name = mail.pop('name', None)
            description = mail.pop('description', None)

            attachments = mail.pop('attachments', [])
            email = Email(**mail)
            logging.info('Processing mail: %s', str(email))
            if type(attachments) is str:
                attachments = [attachments]
            for a in attachments:
                a_path = os.path.join(os.path.dirname(path), a)
                email.add_attachment(a_path)

            if not args.dry_run:
                email.send(port=1025)
            else:
                print(MAIL_PREFIX, email.body, MAIL_SUFFIX, sep='\n')


if __name__ == '__main__':
    sys.exit(main())
