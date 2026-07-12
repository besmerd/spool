import argparse
import logging
import sys
import time
from pathlib import Path

from .exceptions import SpoolError
from .mailer import Mailer
from .parser import ConfigError, load_mails

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


def run():
    """Main method."""

    args = parse_args(sys.argv[1:])
    configure_logger(args.verbosity)

    for path, config in load_configurations(args.path):

        if args.check:
            continue

        try:
            mails = load_mails(path)

            if args.check:
                continue

        except ConfigError as ex:
            LOG.error('Error while parsing config: %s [path=%s]', ex, path)
            continue

        mailer = Mailer(
            relay=args.relay, port=args.port, helo=args.helo,
            debug=args.debug, nameservers=args.nameservers,
            starttls=args.starttls, no_cache=args.no_cache,
        )

        for mail in mails:
            if not mail.matches_tags(args.tags):
                LOG.debug('Skipping message "%s", does not match tags: %s',
                          mail.name, args.tags)
                continue

            if not first and args.delay:
                LOG.debug('Delay sending of next message by %.2f seconds.',
                          args.delay)
                time.sleep(args.delay)
            else:
                first = False

            try:
                msg = mail.build_message(path.parent)
                mailer.send(msg, args.print_only)

            except (SpoolError, OSError) as ex:
                LOG.error(
                    'Failed to process message: %s. [name=%s, path=%s]',
                    ex, mail.name, path
                )


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
