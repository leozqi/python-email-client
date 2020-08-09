from datetime import datetime
import time
from email.header import Header, decode_header, make_header
import quopri
import email.utils
from os import getenv
from dotenv import load_dotenv

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
    decoded = quopri.decodestring(decoded).decode(encoding='utf-8', errors='ignore')
    count = 0
    terms = [] #[(search_term, value)]
    while count < len(decoded):
        if ord(decoded[count]) > 65535:
            terms.append(decoded[count])
        count += 1

    for t in terms:
        decoded = decoded.replace(t, ''.join(('{U', str(ord(t)), '}')))

    return decoded

def get_config():
    load_dotenv()
    config_vals = {
        'email': getenv('USER_EMAIL'),
        'pswrd': getenv('USER_PASSWORD'),
        'imap': getenv('IMAP_SERVER'),
        'port': getenv('PORT'),
        'version': getenv('VERSION')
    }

    if None in config_vals.values():
        raise ValueError(
            'Add a file with name ".env" with the correct values:\n'
            'USER_EMAIL: the user\'s email.\n'
            'USER_PASSWORD: the user\'s password for that email.\n'
            'IMAP_SERVER: the imap server of the email address.\n'
            'PORT: the port of the imap server. Usually 993.\n'
            'VERSION: the version of the program.\n'
        )
    
    return config_vals

# Currently Unused
class TaskManager():
    '''
    Manages the application's tasks. These tasks are run sequentially in a
    separate thread to not interfere with the main GUI, and any print statements
    are passed to the GUI separately.

    Tuple format: (function, (args,))
    '''
    def __init__(self, print_func, bar_func, reset_func):
        self.task_q = Queue()
        self.task_t = Thread(target=self.task_getter)
        self.task_t.daemon = True
        self.task_t.start()
    
    def __del__(self):
        while not self.task_q.empty():
            self.task_q.get()
            self.task_q.task_done()
    
    def task_getter(self):
        while True:
            if not self.task_q.empty():
                data = self.task_q.get()
                func = data[0]
                func_args = data[1] # tuple of args
                func(*data[1])
                self.task_q.task_done()

    def put_task(self, func, *args):
        self.task_q.put( (func, *args) )