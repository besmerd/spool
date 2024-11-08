import argparse
import logging
import random
import string
import sys
import time
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
        help='SMTP relay server'
    )
    parser.add_argument(
        '-p', '--port', type=int, default=25,
        help='Remote server port (default: 25)'
    )
    parser.add_argument(
        '-n', '--nameservers',
        help='Nameservers for MX record lookup'
    )
    parser.add_argument(
        '-N', '--no-cache', action='store_true',
        help='Disable DNS cache'
    )
    parser.add_argument(
        '-d', '--delay', type=float,
        help='Delay (in seconds) after each mail'
    )
    parser.add_argument(
        '-D', '--debug', action='store_true',
        help='Enable SMTP conversation debugging'
    )
    parser.add_argument(
        '-P', '--print-only', action='store_true',
        help='Print messages but do not send'
    )
    parser.add_argument(
        '-H', '--helo',
        help='HELO name for SMTP server connection'
    )
    parser.add_argument(
        '-c', '--check', action='store_true',
        help='Check config files and exit'
    )
    parser.add_argument(
        '-t', '--tags', help='Tags for execution'
    )
    parser.add_argument(
        '--starttls', action='store_true',
        help='Use STARTTLS'
    )

    parser.add_argument(
        'path', nargs='+', metavar='config', type=Path,
        help='Path to spool config file'
    )


    output_group = parser.add_mutually_exclusive_group()

    output_group.add_argument(
        '-v', '--verbose', action='count', default=0, dest='verbosity',
        help='Increase verbosity',
    )

    output_group.add_argument(
        '-s', '--silent', action='store_const', const=-1, default=0, dest='verbosity',
        help='Silent mode (only errors)',
    )

    return parser.parse_args(args)


def tags_matches_mail(tags, mail):
    """Check if the mail has matching tags."""

    if not tags:
        return True

    tags = [tag.strip() for tag in tags.split(',')]

    return any(tag in mail for tag in tags)


def parse_files(file_path, mail):
    """Parse files for S/MIME-related fields."""
    copy_properties = [
        ('from_key_file', 'from_key'),
        ('from_crt_file', 'from_crt'),
        ('to_crts_file', 'to_crts'),
    ]

    for src, dst in copy_properties:
        if 'smime' not in mail or src not in mail['smime']:
            continue

        with open(file_path.parent / mail['smime'][src], 'r') as fh:
            mail['smime'][dst] = fh.read()

        del mail['smime'][src]

    return mail


class LogFormatter(logging.Formatter):
    """Custom log formatter with color support."""

    COLOR_MAP = {
        logging.DEBUG: '\x1b[38;21m', # GREY
        logging.INFO: '\x1b[38;21m', # GREY
        logging.WARNING: '\x1b[33;21m', # YELLOW
        logging.ERROR: '\x1b[31;21m', # RED
        logging.CRITICAL: '\x1b[31;1m', # BOLD and RED
    }
    RESET = '\x1b[0m'

    def __init__(self, *args, **kwargs):
        self.has_color = hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
        super().__init__(*args, **kwargs)

    def format(self, record):

        if self.has_color:
            log_fmt = self.COLOR_MAP[record.levelno] + LOG_FORMAT + self.RESET
        else:
            log_fmt = LOG_FORMAT

        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)


def configure_logger(verbosity):
    """Configure logging based on verbosity level."""
    verbosity = min(verbosity, 2)
    log_level = logging.WARNING - verbosity * 10

    console = logging.StreamHandler()
    console.setFormatter(LogFormatter())

    logging.basicConfig(level=log_level, handlers=[
        console,
    ])


def load_configurations(file_paths):
    """Load configuration files and returning valid configurations."""
    for path in file_paths:
        if not path.is_file():
            LOG.warning('No such file, skipping. [path=%s]', path)
            continue
        try:
            config = Config.load(path)
            yield path, config
        except ConfigError as ex:
            LOG.error('Error while parsing config: %s [path=%s]', ex, path)


def process_message(mailer, mail, path, print_only):
    """Process and send a single mail message."""

    mail.pop('description', None)
    mail = parse_files(path, mail)
    attachments = mail.pop('attachments', [])
    msg = Message(**mail)

    if isinstance(attachments, str):
        attachments = [attachments]
    for attachment in attachments:
        msg.attach(path.parent / attachment)

    try:
        mailer.send(msg, print_only)
    except MessageError as exc:
        LOG.error('Failed to create message: %s. [name=%s, path=%s]', exc,
                 mail['name'], path)


def run():
    """Main method."""

    args = parse_args(sys.argv[1:])
    configure_logger(args.verbosity)

    for path, config in load_configurations(args.path):

        if args.check:
            continue


        with Mailer(relay=args.relay, port=args.port, helo=args.helo,
                    debug=args.debug, nameservers=args.nameservers,
                    starttls=args.starttls, no_cache=args.no_cache) as mailer:

            for idx, mail in enumerate(config.mails):

                if not tags_matches_mail(args.tags, mail.pop('tags', [])):
                    LOG.debug('Skipping message "%s", does not match tags: %s',
                              mail['name'], args.tags)
                    continue

                process_message(mailer, mail, path, args.print_only)

                if args.delay and idx < len(config.mails) - 1:
                    LOG.debug('Delaying next message by %.2f seconds.', args.delay)
                    time.sleep(args.delay)


def cli():
    """Main cli entry point."""
    try:
        run()

    except SpoolError as ex:
        logging.critical(ex)
        sys.exit(1)

    except Exception as exc:
        logging.critical('Unexpected error occured: %s', exc, exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
