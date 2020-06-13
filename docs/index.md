# Spool

Send mails with YAML.

## Installation

```sh
pip install spool
```

See [installation](installation.md) for further instructions.

## Usage

```
spool --help
```

### Example configuration file:

```yaml
---
# mails.yml

# Optional defaults for keys mails.
defaults:
 sender: foo@example.com
 recipents: Bar <bar@example.com>, baz@example.com

# Optional variables which can be used below.
vars:
 message: |
   Hello world,

   Foo bar baz ...

   Kind regards,
   Foo

# Mails to send.
mails:
 - name: Test Mail
   description: Hello world test mail
   headers:
     X-Mailer: Spool Mailer
   text_body: '{{ message }}'
```

### Generate mail(s):

```sh
spool --verbose --relay localhost:2525 example/simple.yml
```

Have a look at the [reference](reference.md) section or take a peek at the [examples](examples.md).
