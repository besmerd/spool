$ spool\_
=========

Spool allows you to generate test mails specified in YAML.

Installation
------------

.. code:: sh

   pip install .

*Note*: The module M2Crypto, which handles S/MIME signing and encryption
requires the installation of `swig`. Use your favourite package manager to
install (e.g. `sudo yum install swig`).


Usage
-----

.. code:: sh

   spool --help

Example configuration file:
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: yaml

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

Generate mail(s):
~~~~~~~~~~~~~~~~~

.. code:: sh

   spool --verbose --relay localhost:2525 example/simple.yml

For further examples visit the
`documentation <https://besmerd.github.io/spool>`__.