from datetime import datetime
import time
from email.header import Header, decode_header, make_header
import quopri
import email.utils

def askForBool(message):
    subject = ''
    while subject not in ('y', 'n'):
        subject = input(f'{message} (Y/N): ').lower()
    if subject == 'y':
        return True
    else:
        subject = False

def email_to_datetime(email_date):
    """
    Keyword arguments:
    email_date -- a date in RFC 2822 format:
                  eg. 'Mon, 20 Nov 1995 19:12:08 -0500'
    
    Returns: datetime.datetime object
    """
    return datetime.fromtimestamp(
        time.mktime(email.utils.parsedate(email_date))
    )

def parse_sub(subject):
    decoded = make_header(decode_header(subject))
    return ''.join((str(decoded)[:40], '...')).encode(encoding='ascii',
                                                      errors='ignore')

def parse_payload(payload):
    decoded = payload.encode(encoding='ascii', errors='ignore').decode('utf-8')
    return quopri.decodestring(decoded)