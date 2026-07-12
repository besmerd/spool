import codecs
import logging
import os.path
from pathlib import Path

import jinja2
import yaml
from pydantic import (BaseModel, ConfigDict, Field,
                      ValidationError as PydanticValidationError,
                      field_validator, model_validator)

from .exceptions import SpoolError

LOG = logging.getLogger(__name__)


class EmlSpec(BaseModel):
    model_config = ConfigDict(extra='forbid')

    template: str
    vars: dict[str, object] = Field(default_factory=dict)


class DkimSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    domain: str
    selector: str
    privkey: str


class SmimeSpec(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)

    from_crt: str | None = None
    from_crt_file: str | None = None
    from_key: str | None = None
    from_key_file: str | None = None
    to_crts: str | None = None
    to_crts_file: str | None = None

    @model_validator(mode='after')
    def check_inline_or_file(self):
        pairs = (
            ('from_crt', 'from_crt_file'),
            ('from_key', 'from_key_file'),
            ('to_crts', 'to_crts_file'),
        )
        for inline, file in pairs:
            if (getattr(self, inline) is not None
                    and getattr(self, file) is not None):
                raise ValueError(f'{inline} and {file} are mutually exclusive')

        has_key = self.from_key is not None or self.from_key_file is not None
        has_cert = self.from_crt is not None or self.from_crt_file is not None
        if has_key != has_cert:
            raise ValueError(
                'S/MIME signing requires both a private key and certificate')
        return self

    def resolve_files(self, base_dir: Path):
        """Return a copy with referenced certificate and key files loaded."""

        resolved = self
        file_fields = (
            ('from_key_file', 'from_key'),
            ('from_crt_file', 'from_crt'),
            ('to_crts_file', 'to_crts'),
        )
        for file_field, value_field in file_fields:
            filename = getattr(resolved, file_field)
            if filename is None:
                continue

            contents = (base_dir / filename).read_text()
            resolved = resolved.model_copy(update={
                file_field: None,
                value_field: contents,
            })

        return resolved


class MailSpec(BaseModel):
    """A rendered and validated mail definition."""

    model_config = ConfigDict(
        extra='forbid', frozen=True, validate_by_name=True)

    name: str | None = None
    description: str | None = None
    envelope_from: str = Field(validation_alias='sender')
    envelope_recipients: str | list[str] = Field(
        validation_alias='recipients')
    subject: str | None = None
    headers: dict[str, str | int | float | None] = Field(
        default_factory=dict)
    from_addr: str | None = Field(default=None, validation_alias='from')
    to_addrs: str | list[str] | None = Field(
        default=None, validation_alias='to')
    cc_addrs: str | list[str] | None = Field(
        default=None, validation_alias='cc')
    bcc_addrs: str | list[str] | None = Field(
        default=None, validation_alias='bcc')
    eml: str | EmlSpec | None = None
    text_body: str | None = None
    html_body: str | None = None
    dkim: DkimSpec | None = None
    smime: SmimeSpec | None = None
    ical: str | None = None
    attachments: str | list[str] | None = None
    tags: list[str] = Field(default_factory=list)

    @field_validator('tags', mode='before')
    @classmethod
    def split_tags(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            return [tag.strip() for tag in value.split(',')]
        return value

    @model_validator(mode='after')
    def check_eml_is_exclusive(self):
        if self.eml is None:
            return self

        conflicts = ('text_body', 'html_body', 'attachments', 'ical')
        present = [name for name in conflicts if getattr(self, name) is not None]
        if present:
            raise ValueError(
                'eml cannot be combined with ' + ', '.join(present))
        return self

    def matches_tags(self, requested: str | None) -> bool:
        """Return whether this mail matches a comma-separated tag filter."""

        if not requested:
            return True

        tags = {tag.strip() for tag in requested.split(',')}
        return any(tag in self.tags for tag in tags)

    def build_message(self, base_dir: Path):
        """Build a message, resolving files relative to the config file."""

        from .message import Message

        smime = self.smime.resolve_files(base_dir) if self.smime else None
        message = Message(
            name=self.name,
            envelope_from=self.envelope_from,
            envelope_recipients=self.envelope_recipients,
            from_addr=self.from_addr,
            to_addrs=self.to_addrs,
            subject=self.subject,
            cc_addrs=self.cc_addrs,
            bcc_addrs=self.bcc_addrs,
            headers=self.headers,
            text_body=self.text_body,
            html_body=self.html_body,
            ical=self.ical,
            dkim=self.dkim,
            smime=smime,
            eml=self.eml,
        )
        attachments = self.attachments or []
        if isinstance(attachments, str):
            attachments = [attachments]

        for attachment in attachments:
            message.attach(base_dir / attachment)

        return message


FILTERS = {
    'basename': lambda p: os.path.basename(p),
    'dirname': lambda p: os.path.dirname(p),
    'base64': lambda s: codecs.encode(s.encode(), 'base64').decode(),
    'quoted_printable': lambda s: codecs.encode(
        s.encode(), 'quoted_printable').decode(),
}


class ConfigError(SpoolError):
    """Base class for all parsing errors."""


class ValidationError(ConfigError):
    """Configuration validation failed."""


def load_mails(config) -> tuple[MailSpec, ...]:
    """Load, render and validate mail definitions from a path or mapping."""

    if not isinstance(config, dict):
        LOG.info('Parsing config file. [path=%s]', config)
        with open(config, 'r') as fh:
            config = yaml.safe_load(fh) or {}

    _validate_config_shape(config)
    env = jinja2.Environment()
    env.filters.update(FILTERS)
    env.globals = config.get('vars', {})

    rendered_mails = []
    defaults = config.get('defaults', {})
    for configured_mail in config.get('mails', []):
        mail = {**defaults, **configured_mail}
        loop = mail.get('loop')
        mail = {key: value for key, value in mail.items() if key != 'loop'}

        if loop:
            rendered_loop = _render(loop, env)
            if isinstance(rendered_loop, str):
                try:
                    rendered_loop = yaml.safe_load(rendered_loop)
                except yaml.YAMLError as ex:
                    raise ValidationError(str(ex)) from ex

            for item in rendered_loop:
                rendered_mails.append(_render(mail, env, item=item))
        else:
            rendered_mails.append(_render(mail, env))

    try:
        return tuple(MailSpec.model_validate(mail) for mail in rendered_mails)
    except PydanticValidationError as ex:
        raise ValidationError(str(ex)) from ex


def _validate_config_shape(config):
    if not isinstance(config, dict):
        raise ValidationError('Configuration must be a mapping')

    unknown = set(config) - {'defaults', 'vars', 'mails'}
    if unknown:
        raise ValidationError(f'Unknown configuration fields: {sorted(unknown)}')

    if not isinstance(config.get('defaults', {}), dict):
        raise ValidationError('defaults must be a mapping')
    if not isinstance(config.get('vars', {}), dict):
        raise ValidationError('vars must be a mapping')

    mails = config.get('mails', [])
    if not isinstance(mails, list) or not all(
            isinstance(mail, dict) for mail in mails):
        raise ValidationError('mails must be a list of mappings')


def _render(field, env, **kwargs):
    if isinstance(field, str):
        return env.from_string(field).render(**kwargs)

    if isinstance(field, list):
        return [_render(item, env, **kwargs) for item in field]

    if isinstance(field, dict):
        return {
            key: _render(value, env, **kwargs)
            for key, value in field.items()
        }

    return field
