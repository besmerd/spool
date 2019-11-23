import logging

import jinja2
import yaml

LOG = logging.getLogger(__name__)


class ConfigError(Exception):
    """Base class for all parsing errors."""


class NoSenderError(ConfigError):
    """Envelope sender or 'from' missing."""


class NoRecipientsError(ConfigError):
    """Envelope recipient(s) or 'to' missing."""


class Config:
    """Represents a single mail instance config."""

    MAIL_FIELDS = [
        'name',
        'description',
        'recipients',
        'subject',
        'headers',
        'sender',
        'from',
        'to',
        'cc',
        'bcc',
        'eml',
        'text_body',
        'html_body',
        'ical',
        'attachments',
        'loop',
        'from_crt',
        'from_key',
    ]

    MAIL_MUTUAL_EXCLUSION = [
        ('eml', 'text_body'),
        ('eml', 'text_html'),
        ('eml', 'ical'),
        ('eml', 'attachment'),
    ]

    @staticmethod
    def load(config):
        """Create a config object from a config file."""
        if not isinstance(config, dict):
            LOG.info('Parsing file: %s', config)
            with open(config, 'r') as fh:
                config = yaml.safe_load(fh)
        return Config(config)

    def _check_config(self):

        for mail in self.mails:

            if not isinstance(mail, dict):
                raise ConfigError('Failed to read config for mail')

            # discard description
            mail.pop('description', '')

            if 'sender' not in mail and 'from' not in mail:
                raise NoSenderError()

            if 'recipients' not in mail and 'to' not in mail:
                raise NoRecipientsError()

            for field, _ in mail.items():
                if field not in self.MAIL_FIELDS:
                    raise ConfigError(
                        'Unknown field \'{0}\' for mail config'.format(field))

            for excl in self.MAIL_MUTUAL_EXCLUSION:
                if all(i in mail.keys() for i in excl):
                    raise ConfigError(
                        'Fields are mutually exclusive: {0}'.format(excl))

    def _render(self, field, env, **kwargs):

        if isinstance(field, str):
            template = env.from_string(field)
            return template.render(**kwargs)

        if isinstance(field, list):
            copy = []
            for item in field:
                copy.append(self._render(item, env, **kwargs))
            return copy

        if isinstance(field, dict):
            copy = {}
            for key, value in field.items():
                copy[key] = self._render(value, env, **kwargs)
            return copy

        return field

    def __init__(self, config):

        env = jinja2.Environment()
        env.globals = config.get('vars', None)

        self.mails = []
        for mail in config.get('mails', []):

            for key, value in config.get('defaults', {}).items():
                if key not in mail:
                    mail[key] = value

            loop = mail.pop('loop', None)
            if loop:
                loop = self._render(loop, env)
                try:
                    loop = yaml.safe_load(loop)
                except AttributeError:
                    pass
                except yaml.YAMLError as ex:
                    LOG.error(ex)

                for item in loop:
                    copy = {}
                    for key, value in mail.items():
                        copy[key] = self._render(value, env, item=item)
                    self.mails.append(copy)
            else:
                for key, value in mail.items():
                    mail[key] = self._render(value, env)
                self.mails.append(mail)

        self._check_config()

        for mail in self.mails:
            mail['from_addr'] = mail.pop('from', None)
            mail['to_addrs'] = mail.pop('to', None)
            mail['cc_addrs'] = mail.pop('cc', None)
            mail['bcc_addrs'] = mail.pop('bcc', None)
