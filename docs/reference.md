# Reference

## Defaults
The `defaults` section can be used for properties that should apply for all
messages in a given configuration file. Properties defined in the `mails`
section have a higher precedence and therefore overwrite the default values.

The following configuration would result in a message from *sender@example.com*
to *recipient@example.net*
```yaml
---
defaults:
  sender: sender@example.com
  recipients: recipient@example.com

mails:
  - subject: Hello World
    text_body: This is a simple hello.

  - sender: other@example.com
    subject: Hello World
    text_body: This is a simple hello.
```

## Vars
The `vars` section holds variables which can be used in other sections
like `mails` or `defaults`.

```yaml
---
vars:
  names:
    - Alice
    - Bob
    - Rachel

mails:
  - sender: sender@example.com
    recipients: recipient@example.com
    subject: 'Hello {{ item }}'
    text_body: This is a simple hello.
    loop: '{{ names }}'
```

## Mails
The `mails` section defines the messages which should be generated. The
following configuration would create a message from 'sender@example.com' to
'recipient@example.com'

```yaml
---
mails:
  - name: hello-world
    sender: sender@example.com
    recipients: recipient@example.com
    subject: Hello World
    text_body: This is a simple hello.
```

name
: An reference name for the message

description
: An optional description for the message

sender
: Defines the envelope sender

recipients
: Defines a single or a list of recipients

subject
: Subject of the message

from
: Corresponds to the `from` header in [IMF][1], defaults to `sender`

to
: Corresponds to the `to` header in [IMF][1], defaults to `recipients`

cc
: Corresponds to the `cc` header in [IMF][1]

bcc
: Corresponds to the `bcc` header in [IMF][1]

text_body
: A MIME part of type `text/plain`

text_html
: A MIME part of type `text/html`

attachments
: List of files which are attached to the message

dkim
: Specifies the settings for dkim signing

smime
: Specifies the parameters for smime singing/encryption

loop
: List of parameters to loop over.

[1]: https://tools.ietf.org/html/rfc5322
