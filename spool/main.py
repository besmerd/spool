import argparse
import logging
import sys
import time
import random
import string
from pathlib import Path

from .exceptions import SpoolError
from .mailer import Mailer
from .message import Message, MessageError
from .parser import Config, ConfigError


LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'
LOG = logging.getLogger(__name__)



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
        '-N', '--no-cache',
        action='store_true',
        help='disable dns cache'
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
        '-t', '--tags',
        help='tags to execute',
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


def tags_matches_mail(tags, mail):
    """Returns True if mail has a matching tag."""

    if not tags:
        return True

    tags = [tag.strip() for tag in tags.split(',')]

    return any(tag in mail for tag in tags)


def parse_files(path, mail):
    copy_properties = [
        ('from_key_file', 'from_key'),
        ('from_crt_file', 'from_crt'),
        ('to_crts_file', 'to_crts'),
    ]

    for src, dst in copy_properties:

        if 'smime' not in mail or src not in mail['smime']:
            continue

        with open(path.parent / mail['smime'][src], 'r') as fh:
            mail['smime'][dst] = fh.read()

        del mail['smime'][src]

    return mail


class LogFormatter(logging.Formatter):

    GREY = '\x1b[38;21m'
    YELLOW = '\x1b[33;21m'
    RED = '\x1b[31;21m'
    BOLD_RED = '\x1b[31;1m'
    RESET = '\x1b[0m'

    FORMATS = {
        logging.DEBUG: GREY + LOG_FORMAT + RESET,
        logging.INFO: GREY + LOG_FORMAT + RESET,
        logging.WARNING: YELLOW + LOG_FORMAT + RESET,
        logging.ERROR: RED + LOG_FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + LOG_FORMAT + RESET,
    }

    def __init__(self, *args, **kwargs):
        self.has_color = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        super().__init__(*args, **kwargs)


    def format(self, record):

        if self.has_color:
            log_fmt = self.FORMATS[record.levelno]
        else:
            log_fmt = LOG_FORMAT

        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)


def config_logger(verbosity):
    verbosity = min(verbosity, 2)
    log_level = logging.WARNING - verbosity * 10

    console = logging.StreamHandler()
    console.setFormatter(LogFormatter())

    logging.basicConfig(level=log_level, handlers=[console,])


def get_uuid(length=6):
    uuid = random.sample(string.digits + string.ascii_lowercase, length)
    return ''.join(uuid)


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
                    starttls=args.starttls, no_cache=args.no_cache) as mailer:

            for mail in config.mails:

                if not tags_matches_mail(args.tags, mail.pop('tags', [])):
                    LOG.debug('Skipping message "%s", does not match tags: %s',
                              mail['name'], args.tags)
                    continue

                if not first and args.delay:
                    LOG.debug('Delay sending of next message by %.2f seconds.',
                              args.delay)
                    time.sleep(args.delay)
                else:
                    first = False

                mail.pop('description', None)
                mail = parse_files(path, mail)
                attachments = mail.pop('attachments', [])

                msg = Message(**mail)

                if isinstance(attachments, str):
                    attachments = [attachments]

                for attachment in attachments:
                    file_path = path.parent / attachment
                    msg.attach(file_path)

                try:
                    mailer.send(msg, args.print_only)

                except MessageError as ex:
                    LOG.error(
                        'Failed to create message: %s. [name=%s, path=%s]',
                        ex, mail['name'], path
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
