import logging

import jinja2
import yaml

from cerberus import Validator

from .exceptions import SpoolError


LOG = logging.getLogger(__name__)

CONFIG_SCHEMA = {
    'defaults': {'type': 'dict', 'allow_unknown': True},
    'vars': {'type': 'dict', 'allow_unknown': True},
    'mails': {
        'type': 'list',
        'schema': {
            'type': 'dict',
            'schema': {
                'name': {'type': 'string'},
                'description': {'type': 'string'},
                'sender': {'type': 'string', 'required': True},
                'recipients': {'type': ['string', 'list'], 'required': True},
                'subject': {'type': 'string'},
                'headers': {'type': 'dict'},
                'from': {'type': 'string', 'rename': 'from_addr'},
                'to': {'type': ['string', 'list'], 'rename': 'to_addrs'},
                'cc': {'type': ['string', 'list'], 'rename': 'cc_addrs'},
                'bcc': {'type': ['string', 'list'], 'rename': 'bcc_addrs'},
                'eml': {
                    'type': 'string',
                    'excludes': [
                        'text_body',
                        'html_body',
                        'attachments',
                        'ical',
                    ],
                },
                'text_body': {'type': 'string', 'excludes': ['eml']},
                'html_body': {'type': 'string', 'excludes': ['eml']},
                'dkim': {
                    'type': 'dict',
                    'schema': {
                        'privkey': {'type': 'string'},
                        'selector': {'type': 'string'},
                        'domain': {'type': 'string'},
                    },
                },
                'ical': {'type': 'string', 'excludes': ['eml']},
                'attachments': {
                    'type': ['string', 'list'],
                    'excludes': ['eml'],
                },
                'loop': {'type': 'list'},
                'from_crt': {'type': 'string'},
                'from_key': {'type': 'string'},
            },
        },
    },
}


class ConfigError(SpoolError):
    """Base class for all parsing errors."""

    def __str__(self):
        return self.__doc__


class ValidationError(ConfigError):
    """Validation Error."""


class Config:
    """Represents a single mail instance config."""

    @staticmethod
    def load(config):
        """Create a config object from a config file."""
        if not isinstance(config, dict):
            LOG.info('Parsing config file. [path=%s]', config)
            with open(config, 'r') as fh:
                config = yaml.safe_load(fh)
        return Config(config)

    def _check_config(self):

        v = Validator()
        if not v.validate(self.config, CONFIG_SCHEMA):
            raise ValidationError()

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

        # FIXME
        self.config = config
        self.config['mails'] = self.mails
        self._check_config()
