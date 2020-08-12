import logging
import os.path

import jinja2
import yaml
from cerberus import Validator

from .exceptions import SpoolError

LOG = logging.getLogger(__name__)


def to_list(string):
    """Returns a list of values from a comma separated string"""

    if isinstance(string, list):
        return string

    return [item.strip() for item in string.split(',')]


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
                'recipients': {
                    'type': ['string', 'list'],
                    'required': True,
                },
                'subject': {'type': 'string'},
                'headers': {
                    'type': 'dict',
                    'valuesrules': {
                        'type': ['string', 'number'],
                        'nullable': True,
                    },
                },
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
                'smime': {
                    'type': 'dict',
                    'schema': {
                        'from_crt': {
                            'type': 'string',
                            'excludes': ['from_crt_file'],
                        },
                        'from_crt_file': {
                            'type': 'string',
                            'excludes': ['from_crt'],
                        },
                        'from_key': {
                            'type': 'string',
                            'excludes': ['from_key_file'],
                        },
                        'from_key_file': {
                            'type': 'string',
                            'excludes': ['from_key'],
                        },
                        'to_crts': {
                            'type': 'string',
                            'excludes': ['to_crts_file'],
                        },
                        'to_crts_file': {
                            'type': 'string',
                            'excludes': ['to_crts'],
                        }
                    },
                },
                'ical': {'type': 'string', 'excludes': ['eml']},
                'attachments': {
                    'type': ['string', 'list'],
                    'excludes': ['eml'],
                },
                'loop': {'type': 'list'},
                'tags': {
                    'type': ['string', 'list'],
                    'coerce': to_list
                },
            },
        },
    },
}

FILTERS = {
    'basename': lambda p: os.path.basename(p),
    'dirname': lambda p: os.path.dirname(p),
}


class ConfigError(SpoolError):
    """Base class for all parsing errors."""


class ValidationError(ConfigError):
    """Validation Error."""



class Config:
    """Represents a single mail instance config."""


    def __init__(self, config):

        env = jinja2.Environment()

        for f in FILTERS:
            env.filters[f] = FILTERS[f]

        env.globals = config.get('vars', None)

        mails = []
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
                    mails.append(copy)
            else:
                for key, value in mail.items():
                    mail[key] = self._render(value, env)
                mails.append(mail)

        # FIXME
        config['mails'] = mails
        self._config = self.check_config(config)

    @property
    def mails(self):
        return self._config['mails']

    @staticmethod
    def load(config):
        """Create a config object from a config file."""

        if not isinstance(config, dict):
            LOG.info('Parsing config file. [path=%s]', config)
            with open(config, 'r') as fh:
                config = yaml.safe_load(fh)
        return Config(config)

    @staticmethod
    def check_config(config):

        v = Validator()
        if not v.validate(config, CONFIG_SCHEMA, normalize=False):
            raise ValidationError(v.errors)

        return v.normalized(config)

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
