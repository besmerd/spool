from __future__ import print_function

import argparse
import logging
import os
import sys

from .mailer import Email
from .parser import Config

logging.basicConfig(format='%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)

MAIL_OUT_PREFIX = '---------- MESSAGE FOLLOWS ----------'
MAIL_OUT_SUFFIX = '------------ END MESSAGE ------------'


def parse_args(args):
    parser = argparse.ArgumentParser(description='Send mails with YAML.')

    parser.add_argument(
        '-d', '--dry-run',
        action='store_true',
        help='create, but do not send messages',
    )

    parser.add_argument(
        '-s', '--smtp-server',
        default='localhost:1025',
        help='smtp server, defauls to: localhost:1025',
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        help='increase verbosity of the output',
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
    if args.verbose > 0:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
    for path in args.path:
        if not os.path.isfile(path):
            logging.warning('No such file "%s", skipping.', path)
            continue
        config = Config.load(path)
        for mail in config.mails:

            name = mail.pop('name', None)
            description = mail.pop('description', None)

            config_dir = os.path.dirname(path)

            for key in ('from_key', 'from_crt', 'to_crt', 'eml'):
                if key not in mail:
                    continue
                mail[key] = os.path.join(config_dir, mail[key])

            attachments = mail.pop('attachments', [])
            email = Email(**mail)
            logging.info('Processing mail: %s', str(email))
            if type(attachments) is str:
                attachments = [attachments]
            for a in attachments:
                email.add_attachment(os.path.join(config_dir, a))

            if not args.dry_run:
                host, port = args.smtp_server.split(':', 1)
                email.send(host=host, port=port)
                logging.info('Mail sent: %s', str(email))
            else:
                print(MAIL_OUT_PREFIX, email.body, MAIL_OUT_SUFFIX, sep='\n')


if __name__ == '__main__':
    sys.exit(main())
