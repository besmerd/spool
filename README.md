# $ mailman_

Send (test) mails with YAML.

## Installation
```sh
pip install .
```

## Usage
```sh
mailman --help
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
      X-Mailer: Mailman Mailer
    text_body: '{{ message }}'
```

### Generate mail(s):
```sh
mailman example/simple.yml
```

For further examples visit the [documentation](https://besmerd.github.io/mailman).
