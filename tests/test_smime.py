from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pytest

from spool.smime import encrypt, sign

PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDYZtV1JkTgaLNL
g6256bR+c4z6lSnVc+HKLxJH8ds9oblYjh751/F0dgzFuwkFuLzTYeM8k/ErIfO0
y48cFz3M2j2xEiEY7CSqSgCeXvF4Ps/fn44bDO5k5mK3j7NWmPXtf42PCC5f+BA0
u49knm3VC2GvbwWJ4Y0e+8aVBOvKpwC+TjCXnWHgenURyZ3/CiKsK69cmZ6OE8E1
eFjS7LG938ql+ixyFFxwsWgTwUEVN3fSzTzKcnBtUAi6GbKvw5hkIXAVOr6zu0dw
exMiFZ5LKn1ZPjEyKyXj9t3EhQndn/AUO1xOpriJRO1XSTFa7mqXkNpQrLYXe77V
gaQAawhHAgMBAAECggEAYwhsl3gz/R7tLpnMX1B8sYHf+q1Yv76Qjh6MlzAvzTy9
vbEMq/oPHeUIY1T9BAlPIM2jWI27yKl5BjxB+fEI7z7RDL/nNaib/vJu5gs9JnJY
X1Z9ihOY5cQpWSgCQpcttMqy1cpArtqvT/Kl5L48NUtIISkFt9vo4U0HzBq8bbi4
Lup4FNN0oAnOsY6xJ6ObmPQb8Tzcdcix1WYYWoye1X6WQnwfW1C/nm/OmZpNWwux
Z67j2MSZqbv9PDLYF1Oi1fsiQWPL1EpaUHSFv3m5x8OF1iXLI6SLTDiXXIsDKpVs
IxoK2XM8g0GFE4DvcV6CpIPz2RRe5SDmMmDXrFX4gQKBgQDyoDNHzO2aJ2cO2Xfv
PEfJv05zYNYUsI75oAw09AVqMKG1mpAlzq8d8knBumYReglGi7K8GA3A3vX5CuVL
Yjkod6gGp05HVHS9BDwGWYNtqNtRvFbNTkxGc3yH7cLt3UbAngwHM9KnF0u6m3UQ
abyCVkomAHdaEtB8o8HjtpSnmQKBgQDkVJLk+UuGjKK9dZfJv19f/OnkvO9UK7qo
3yuyyRP+iYJESd/eskfbSGV9bzMck8v1+kfQUecoTEWnI35ASy/w9+Up0Ut5a4OZ
a+ov6oNch0qdomdp0ZKtCeF7sXRV2/KQa/Ur1LdWbQFjuCiA7lguShjQVd/MeHtc
zCY6rdOa3wKBgCA3QVfhUBNN9BM2sQQlHusc6c/MJeDtaK6gn75QQH/PIUm50jYS
8ZGqYDzHAVKEv8KMPhlXoEvhzwtYdQXDbw9+g+MOSAiUoEOQ0l+NdzQSXbzGo0fz
g5E/OGPcICvxW7mrwrEaInhpUXbfuXWKdKthxcqx+ScOpHxISjBwR+DRAoGAIRn1
tcZCYb4vtaG/oJri28qRqfyOAbjZNbQs5J1sDaGnxfijwOg9rJehRv8A/OqcTgu7
r4LALUJpcqKdofqEd72odliGRZMFoA9aAxpPcvGWKqYpsdiVGArvqnv+bpgVYUSV
ZYZQEfJ5mhhPnulu1T8eu81HRaBN2hUqkaUzoScCgYEAgy2R7yT8oRFi8use52K9
qZZym+XVVp3cRjy+4m3b6NrmOS3VHkx+KFWCEjvdluLMZMBXiu2ejpUzBW9OX0mI
UdQSJ2MMux1zEILLClaRux6USuJmK7v7qccSWlnzLaI2KAuHAK72rI1SmSQSBCyg
fxn9Sa5UDZ9PL2IcwWJ1I60=
-----END PRIVATE KEY-----
"""
CERT = """-----BEGIN CERTIFICATE-----
MIIDQzCCAiugAwIBAgIUCdN5Mv7hWC06H3M2qdF9D/o4R7MwDQYJKoZIhvcNAQEL
BQAwMTEvMC0GA1UEAwwmU2VuZGVyL2VtYWlsQWRkcmVzcz1zZW5kZXJAZXhhbXBs
ZS5vcmcwHhcNMjAwNjIwMjEwMDU2WhcNMjEwNjIwMjEwMDU2WjAxMS8wLQYDVQQD
DCZTZW5kZXIvZW1haWxBZGRyZXNzPXNlbmRlckBleGFtcGxlLm9yZzCCASIwDQYJ
KoZIhvcNAQEBBQADggEPADCCAQoCggEBANhm1XUmROBos0uDrbnptH5zjPqVKdVz
4covEkfx2z2huViOHvnX8XR2DMW7CQW4vNNh4zyT8Ssh87TLjxwXPczaPbESIRjs
JKpKAJ5e8Xg+z9+fjhsM7mTmYrePs1aY9e1/jY8ILl/4EDS7j2SebdULYa9vBYnh
jR77xpUE68qnAL5OMJedYeB6dRHJnf8KIqwrr1yZno4TwTV4WNLssb3fyqX6LHIU
XHCxaBPBQRU3d9LNPMpycG1QCLoZsq/DmGQhcBU6vrO7R3B7EyIVnksqfVk+MTIr
JeP23cSFCd2f8BQ7XE6muIlE7VdJMVruapeQ2lCsthd7vtWBpABrCEcCAwEAAaNT
MFEwHQYDVR0OBBYEFAE4N6hUuN4S1Hb6AvzNXop1f/IwMB8GA1UdIwQYMBaAFAE4
N6hUuN4S1Hb6AvzNXop1f/IwMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggEBADmGLnqLP9leIXn19CAINTg5+np/roa1UWCD5T/5ldTH9GRBEsarunLk
3way8ph8LveEVT2MaTQsWLXNeb/WYgFvxgi/SfnpxtBf4+8NcxuggUPZ/GzGSM8N
Re2MnrDJhE4slhll+dp9ERO2Ur9TwP+VghwPKMMQZgTOPSrgfvo+iJrByFZ5cXJ/
I45LGO+aEqbypwqT98Y00kuUlm0JZo2OVvFazAVDlfBnDSTJtFoy6wOSZG92FWiL
EGjnEl57ENN/7AB5RsFV6wlRGIw+ozrZCGNMhsh+KCFJkGkKkVv5ci4JZCofLYZr
sM8ensrJ6/h0cL56uMbXWTsm/EeuqX0=
-----END CERTIFICATE-----
"""
CERT_CHAIN = """-----BEGIN CERTIFICATE-----
MIIDSTCCAjGgAwIBAgIUUKvn0vesiWozUxzGfQswUBa3ylUwDQYJKoZIhvcNAQEL
BQAwNDEyMDAGA1UEAwwpU2VuZGVyL2VtYWlsQWRkcmVzcz1yZWNpcGllbnRAZXhh
bXBsZS5vcmcwHhcNMjAwNjIwMjEwMTE2WhcNMjEwNjIwMjEwMTE2WjA0MTIwMAYD
VQQDDClTZW5kZXIvZW1haWxBZGRyZXNzPXJlY2lwaWVudEBleGFtcGxlLm9yZzCC
ASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAMk8szhuzcT+3qSi5ubh9CF9
ZlMV2a7vgRN2Z+rEtH91SpYM4dyjtgFpz7pvnt+HyNiNngpZYBMURDYKuwoG5KHJ
IAi7CeFQKxduYU/mok+/arCQAtcCppIVL+UQp+ITGCIHggHDBpgXBWrK2lB5KF51
MkWfzO23bv3xMfe9/MKVVvWLUR4UWev3HghhoDluMkUHMaSM8Xc/Y8zbnWjQ2SRG
ogdmJytfXBS3nxhVHELqdKi8kJ4L8K+Gn/KoDqN34iNcOnFywFby4uLRsKPyYw3W
y8QbNLbmY4yMpwIIlE9rVkL1PbEpzUCwBNoWAlUFl6pskqLWu4H5fnY7akWUE/MC
AwEAAaNTMFEwHQYDVR0OBBYEFP0D1Z9SJXn7yIntZyYCnJmeThl8MB8GA1UdIwQY
MBaAFP0D1Z9SJXn7yIntZyYCnJmeThl8MA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZI
hvcNAQELBQADggEBAKidIUibUKaaV76C+dLMAzoUBhbE3CYjNLy0OLylFBCIaF45
MXnk+mLxTEdgTvbK5VJ0XKG2ERMUTOLM6EfF7ck5S5xd95Z7v5JIs/+/N0gWAeB9
bUHXeKafOpjXLlN1njEb3IwtatQuRbKf4xuto5fBA6hAUZmuo8CuxOddCaEmy87I
A9Rs9Pb+S+VhMvfqBVmat0o5lqMO3LNfsJOrWgv4PkETA662dsxdj4fv/KvwGd9b
eeyUHAriWakZNlCZ4+MEwy3uJd1Sc+96FIU4XuhXcQaJqvcjUwsDquyIEum0rznn
OmJkSdlGc0fr9iNNvDiVMHH/sz4WfidJTLxHmoI=
-----END CERTIFICATE-----
"""

@pytest.fixture
def message():
    """Create a dummy MIME message for testing."""

    msg = MIMEText("This is a test message.")
    msg['Subject'] = "Test"
    msg['From'] = "sender@example.com"
    msg['To'] = "recipient@example.com"

    return msg


def test_sign(message):
    """Test the sign function."""

    signed_message = sign(message, PRIVATE_KEY, CERT_CHAIN)

    assert isinstance(signed_message, MIMEMultipart)
    assert signed_message.get_content_type() == 'multipart/signed'
    assert 'application/pkcs7-signature' in [
            part.get_content_type() for part in signed_message.walk()]


def test_encrypt(message):
    """Test the encrypt function."""
    encrypted_message = encrypt(message, CERT)

    assert isinstance(encrypted_message, MIMEApplication)
    assert encrypted_message.get_content_type() == 'application/pkcs7-mime'
    assert encrypted_message.get_param('smime-type') == 'enveloped-data'
