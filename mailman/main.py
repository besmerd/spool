import argparse
import logging
import os
import sys

from .mailer import Mailer, MailerError
from .message import Message, MessageError
from .parser import Config, ConfigError


LOG = logging.getLogger(__name__)
LOG_FORMAT = '%(asctime)s %(levelname)s %(message)s'


def parse_args(args):
    """Parse command line arguments."""

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
        '-S', '--smtp-server',
        default='localhost:1025',
        help='smtp server, defauls to: localhost:1025',
    )

    parser.add_argument(
        '-r', '--reuse-connection',
        action='store_true',
        help='reuse smtp connection to server',
    )

    parser.add_argument(
        '-H', '--helo',
        help='helo name used when connecting to the smtp server',
    )

    parser.add_argument(
        'path',
        nargs='+', metavar='config', #type=argparse.FileType('r'),
        help='path of mailman config',
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

    host, port = args.smtp_server.split(':', 1)
    port = int(port)

    for path in args.path:

        if not os.path.isfile(path):
            LOG.warning("No such file '%s' skipping.", path)
            continue

        try:
            config = Config.load(path)
        except ConfigError as ex:
            LOG.error("Error while parsing config '%s': %s", path, ex)
            continue

        config_dir = os.path.dirname(path)

        with Mailer(host, port, helo=args.helo, debug=args.debug,
                    reuse_connection=args.reuse_connection) as mailer:

            for mail in config.mails:
                name = mail.pop('name', None)
                attachments = mail.pop('attachments', [])

                for prop in ('from_key', 'from_crt'):
                    if prop in mail:
                        mail[prop] = os.path.join(config_dir, mail[prop])

                msg = Message(**mail)

                if isinstance(attachments, str):
                    attachments = [attachments]

                for a in attachments:
                    file_path = os.path.join(config_dir, a)
                    msg.attach(file_path)

                try:
                    mailer.send(msg, args.dry_run)
                    LOG.info('Message sent. [name=%s, path=%s]', name, path)

                except MessageError as ex:
                    LOG.error(
                        'Failed to create message: %s. [name=%s, path=%s]',
                        ex, name, path
                    )

                except MailerError as ex:
                    LOG.error(
                        'Error while sending message: %s. [name=%s, path=%s]',
                        ex, name, path
                    )


def cli():
    """Command line interface entry point."""
    try:
        run()
    except Exception as ex:
        logging.debug(ex, exc_info=True)
        logging.critical(ex)
        sys.exit(1)


if __name__ == '__main__':
    cli()
