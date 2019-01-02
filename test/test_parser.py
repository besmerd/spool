from unittest import TestCase

from hermodr.parser import Config, ConfigError


class TestConfig(TestCase):

    def test_empty_config(self):
        Config.load({})

    def test_no_mails(self):
        Config.load({'mails': []})

    def test_minimal_config(self):
        Config.load({
            'mails': [{
                'sender': '<sender@test.com>',
                'recipients': '<recipient@test.com>',
                'subject': 'Test email',
                'text_body': 'This is a test email.'
            }]
        })

    def test_fail_missing_receivers_or_to(self):
        with self.assertRaises(ConfigError):
            Config.load({
                'mails': [{
                    'sender': '<sender@test.com>',
                    'subject': 'Test email',
                    'text_body': 'This is a test email.'
                }]
            })
