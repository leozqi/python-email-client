from datetime import datetime
import time
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