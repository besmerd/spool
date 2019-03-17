# $ mailman_

Send mails with YAML.

## Installation
```sh
pip install .
```

## Installation for Development
```sh
pip install --editable .
```

## Usage
```sh
mailman --help
```

Example config file:
```yaml
---
# mails.yml

# Optional defaults for keys mails.
defaults:
  sender: foo@example.com
  recipents: Bar <bar@example.com>, baz@example.com

# Optional variables which can be used below.
vars:
  message: Hello world.

# Mails to send.
mails:
  - name: Test Mail
    description: Hello world test mail
    headers:
      X-Mailer: Mailman Mailer
    text_body: '{{ message }}'
```

Generate mails:
```sh
mailman example/simple.yml
```

Generate key/certificate for signing:
```sh
openssl req -newkey rsa:1024 -nodes -x509 -days 365 -out sign.pem
```
