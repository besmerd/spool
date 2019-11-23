# Examples

## Loop
```yaml
---
defaults:
  sender: sender@example.com
  recipients: recipient@example.com

mails:
  - name: Spoofed SPF-enabled domain
    description: Mails spoofed from domains with valid SPF configuration
    sender: 'spf-test@{{ item }}'
    subject: 'SPF Check - {{ item }}'
    text_body: This is a SPF verification check.
    loop:
      - gmail.com
      - microsoft.com
      - facebook.com
```

## S/MIME

### Generate a Test Key/Certificate
```sh
openssl req -newkey rsa:2048 -nodes -x509 -days 365 \
            -subj "/CN=Sender\/emailAddress=sender@example.com" \
            -out sender.crt.pem -keyout sender.key.pem
```

### Create a S/MIME Signed Message
```yaml
---
mails:
  - name: S/MIME Signed Message
    description: Creates a S/MIME Signed (detached) Message
    sender: sender@example.com
    recipients: recipient@example.com
    subject: S/MIME Signed Message
    from_key: sender.key.pem
    from_crt: sender.crt.pem
    text_body: |
        A sign of our times.
```

### Create a S/MIME Encrypted Message
```yaml
---
mails:
  - name: S/MIME Signed Message
    description: Creates a S/MIME Encrypted Message
    sender: sender@example.com
    recipients: recipient@example.com
    subject: S/MIME Encrypted Message
    to_crts: recipient.crt.pem
    text_body: |
        A sign of our times.
```

## iCalendar
```yaml
---
mails:
  - name: iCalendar
    sender: sender@example.com
    recipients: recipient@example.com
    subject: Abraham Lincoln
    ical: |
      BEGIN:VCALENDAR
      VERSION:2.0
      PRODID:-//ZContent.net//Zap Calendar 1.0//EN
      CALSCALE:GREGORIAN
      METHOD:PUBLISH
      BEGIN:VEVENT
      SUMMARY:Abraham Lincoln
      UID:c7614cff-3549-4a00-9152-d25cc1fe077d
      SEQUENCE:0
      STATUS:CONFIRMED
      TRANSP:TRANSPARENT
      RRULE:FREQ=YEARLY;INTERVAL=1;BYMONTH=2;BYMONTHDAY=12
      DTSTART:20080212
      DTEND:20080213
      DTSTAMP:20150421T141403
      CATEGORIES:U.S. Presidents,Civil War People
      LOCATION:Hodgenville\, Kentucky
      GEO:37.5739497;-85.7399606
      DESCRIPTION:Born February 12\, 1809\nSixteenth President (1861-1865)\n\n\n
       \nhttp://AmericanHistoryCalendar.com
      URL:http://americanhistorycalendar.com/peoplecalendar/1,328-abraham-lincoln
      END:VEVENT
      END:VCALENDAR

```
