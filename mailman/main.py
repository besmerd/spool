import argparse
import logging
import os
import sys

from .mailer import Mailer, Message
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
        '-D', '--debug',
        action='store_true',
        help='enable debugging on smtp conversation',
    )

    parser.add_argument(
        '-s', '--smtp-server',
        default='localhost:1025',
        help='smtp server, defauls to: localhost:1025',
    )

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        default=0,
        help='increase verbosity of the output',
    )

    parser.add_argument(
        'path',
        nargs='+',
        metavar='config',
        help='path of mailman config',
    )

    return parser.parse_args(args)


def main():

    args = parse_args(sys.argv[1:])

    host, port = args.smtp_server.split(':', 1)
    mailer = Mailer(host, int(port), debug=args.debug)

    for path in args.path:


        if not os.path.isfile(path):
            logging.warning('No such file "%s", skipping.', path)
            continue

        config = Config.load(path)
        config_dir = os.path.dirname(path)

        for mail in config.mails:
            name = mail.pop('name', None)
            description = mail.pop('description', None)
            attachments = mail.pop('attachments', [])

            if mail['from_key']:
                mail['from_key'] = os.path.join(config_dir, mail['from_key'])

            if mail['from_crt']:
                mail['from_crt'] = os.path.join(config_dir, mail['from_crt'])

            msg = Message(**mail)

            if isinstance(attachments, str):
                attachments = [attachments]

            for a in attachments:
                file_path = os.path.join(config_dir, a)
                msg.attach(file_path)

            if not args.dry_run:
                mailer.send(msg)
            else:
                print(MAIL_OUT_PREFIX, msg.as_string(),
                      MAIL_OUT_SUFFIX, sep='\n')

if __name__ == '__main__':
    sys.exit(main())
