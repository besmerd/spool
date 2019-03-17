import logging
from inspect import getmembers, isfunction

import yaml
from jinja2 import Environment

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


class NoSenderError(ConfigError):
    """Envelope sender or 'from' missing."""


class NoRecipientsError(ConfigError):
    """Envelope recipient(s) or 'to' missing."""


class Config(object):

    MAIL_FIELDS = [
        'name',
        'description',
        'recipients',
        'subject',
        'headers',
        'sender',
        'to',
        'from',
        'eml',
        'text_body',
        'html_body',
        'attachments',
        'loop',
        'from_crt',
        'from_key',
    ]

    MAIL_MUTUAL_EXCLUSION = [
        ('eml', 'text_body'),
        ('eml', 'text_html'),
        ('eml', 'attachment'),
    ]

    @staticmethod
    def load(config):
        if not isinstance(config, dict):
            logging.info('Parsing file: "%s"', config)
            with open(config, 'r') as fh:
                config = yaml.load(fh)
        return Config(config)

    def check_config(self):

        for mail in self.mails:

            if type(mail) is not dict:
                raise ConfigError('Failed to read config for mail')

            if 'sender' not in mail and 'from' not in mail:
                raise NoSenderError()

            if 'recipients' not in mail and 'to' not in mail:
                raise NoRecipientsError()

            for field, value in mail.items():
                if field not in self.MAIL_FIELDS:
                    raise ConfigError(
                        'Unknown field \'{0}\' for mail config'.format(field))

            for excl in self.MAIL_MUTUAL_EXCLUSION:
                if all(i in mail.keys() for i in excl):
                    raise ConfigError(
                        'Fields are mutually exclusive: {0}'.format(excl))

    def __render(self, field, env, **kwargs):

        if type(field) is str:
            template = env.from_string(field)
            return template.render(**kwargs)

        if type(field) is list:
            copy = []
            for item in field:
                copy.append(self.__render(item, env, **kwargs))
            return copy

        if type(field) is dict:
            copy = {}
            for key, value in field.items():
                copy[key] = self.__render(value, env, **kwargs)
            return copy

        return field

    def __init__(self, config):

        env = Environment()
        env.globals = config.get('vars', None)
        # _filters = {name: function for name, function in getmembers(filters)
        #             if isfunction(function)}
        # env.filters.update(_filters)

        self.mails = []
        for mail in config.get('mails', []):

            for key, value in config.get('defaults', {}).items():
                if key not in mail:
                    mail[key] = value

            loop = mail.pop('loop', None)
            if loop:
                loop = self.__render(loop, env)
                try:
                    loop = yaml.load(loop)
                except Exception:
                    pass
                for item in loop:
                    copy = {}
                    for key, value in mail.items():
                        copy[key] = self.__render(value, env, item=item)
                    self.mails.append(copy)
            else:
                for key, value in mail.items():
                    mail[key] = self.__render(value, env)
                self.mails.append(mail)

        self.check_config()
