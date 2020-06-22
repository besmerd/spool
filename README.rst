$ spool\_
=========

Spool allows you to generate test mails specified in YAML.

Installation
------------

.. code:: sh

   pip install .


Usage
-----

.. code:: sh

   spool --help

Example configuration file:
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

   ---
   # mails.yml

   # Optional defaults for keys mails
   defaults:
     sender: foo@example.com
     recipents: Bar <bar@example.com>, baz@example.com

   # Optional variables which can be used below
   vars:
     message: |
       Hello world,

       Foo bar baz ...

       Kind regards,
       Foo

   # Mails to generate/send
   mails:
     - name: Test Mail
       description: Hello world test mail
       headers:
         X-Mailer: Spool Mailer
       text_body: '{{ message }}'

Send/generate mail(s):
~~~~~~~~~~~~~~~~~~~~~~

.. code:: sh

   # Send mails to/trought a relay smtp server
   spool --verbose --relay localhost:2525 example/simple.yml

   # Send mails directly to remote smtp server
   spool --verbose example/simple.yml

   # Use Google's dns servers for MX rr lookup
   spool --verbose --nameserver 8.8.8.8 example/simple.yml

For further examples visit the
`documentation <https://besmerd.github.io/spool>`__.
