import argparse
import logging
import sys
import time

from pathlib import Path

from .mailer import Mailer, MailerError
from .message import Message, MessageError
from .parser import Config, ConfigError
from .exceptions import SpoolError


LOG = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'


def parse_args(args):
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description='Send mails with YAML.')

    parser.add_argument(
        '-r', '--relay',
        help='smtp relay smtp server',
    )

    parser.add_argument(
        '-p', '--port',
        type=int, default=25,
        help='port on remote server, default: 25',
    )

    parser.add_argument(
        '-n', '--nameservers',
        help='nameservers for lookup of MX records'
    )

    parser.add_argument(
        '-d', '--delay',
        type=float,
        help='delay delivery by a given number of seconds after each mail'
    )

    parser.add_argument(
        '-D', '--debug',
        action='store_true',
        help='enable debugging on smtp conversation',
    )

    parser.add_argument(
        '-P', '--print-only',
        action='store_true',
        help='print, but do not send messages',
    )

    parser.add_argument(
        '-H', '--helo',
        help='helo name used when connecting to the smtp server',
    )

    parser.add_argument(
        '-c', '--check',
        action='store_true',
        help='check config files and quit',
    )

    parser.add_argument(
        '--starttls',
        action='store_true',
        help=''
    )

    parser.add_argument(
        'path',
        nargs='+', metavar='config', type=Path,
        help='path of spool config',
    )

    output_group = parser.add_mutually_exclusive_group()

    output_group.add_argument(
        '-v', '--verbose',
        action='count', default=0, dest='verbosity',
        help='verbose output (repeat for increased verbosity)',
    )

    output_group.add_argument(
        '-s', '--silent',
        action='store_const', const=-1, default=0, dest='verbosity',
        help='quiet output (show errors only)',
    )

    return parser.parse_args(args)


def config_logger(verbosity):
    verbosity = min(verbosity, 2)
    log_level = logging.WARNING - verbosity * 10

    logging.basicConfig(level=log_level, format=LOG_FORMAT)


def run():
    """Main method."""

    args = parse_args(sys.argv[1:])
    config_logger(args.verbosity)

    first = True

    for path in args.path:

        if not path.is_file():
            LOG.warning('No such file, skipping. [path=%s]', path)
            continue

        try:
            config = Config.load(path)

            if args.check:
                continue

        except ConfigError as ex:
            LOG.error('Error while parsing config: %s [path=%s]', ex, path)
            continue

        with Mailer(relay=args.relay, port=args.port, helo=args.helo,
                    debug=args.debug, nameservers=args.nameservers,
                    starttls=args.starttls) as mailer:

            for mail in config.mails:

                if not first and args.delay:
                    LOG.debug('Delay sending of next message by %.2f seconds.',
                              args.delay)
                    time.sleep(args.delay)
                else:
                    first = False

                mail.pop('description', None)
                attachments = mail.pop('attachments', [])

                for prop in ('from_key', 'from_crt'):
                    if prop in mail:
                        mail[prop] = path.parent / mail[prop]

                msg = Message(**mail)

                if isinstance(attachments, str):
                    attachments = [attachments]

                for a in attachments:
                    file_path = path.parent / a
                    msg.attach(file_path)

                try:
                    mailer.send(msg, args.print_only)

                except MessageError as ex:
                    LOG.error(
                        'Failed to create message: %s. [name=%s, path=%s]',
                        ex, mail.name, path
                    )


def cli():
    """Main cli entry point."""
    try:
        run()

    except SpoolError as ex:
        logging.critical(ex)
        sys.exit(1)

    except Exception:
        logging.critical('Unexpected error occured.', exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
