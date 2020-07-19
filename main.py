from email import message_from_bytes, parser
from imaplib import IMAP4_SSL
#from bs4 import BeautifulSoup
from html.parser import HTMLParser
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from queue import Queue
import os
import threading
#import multiprocessing
from time import time
print_lock = threading.Lock()
count_lock = threading.Lock()

message_queue = Queue()
count = 0

class EmailHTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super(EmailHTMLParser, self).__init__(*args, **kwargs)
        self.data = []
        self.unknowndata = []
        
    def handle_data(self, data):
        self.data.append(data)

def get_config():
    load_dotenv()
    USER_EMAIL = os.getenv('USER_EMAIL')
    USER_PASSWORD = os.getenv('USER_PASSWORD')
    IMAP_SERVER = os.getenv('IMAP_SERVER')
    PORT = os.getenv('PORT')

    if USER_EMAIL and USER_PASSWORD and IMAP_SERVER and PORT:
        print('Config Success')
        return USER_EMAIL, USER_PASSWORD, IMAP_SERVER, PORT
    else:
        raise ValueError('Add an .env file with the proper config information')       

def parse_html(part):
    html_parser = EmailHTMLParser()
    if part is not None:
        try:
            html_parser.feed(part.get_payload())
        except NotImplementedError:
            return ['']
    else:
        return ['']
    
    data = [ x.strip().lower() for x in html_parser.data if x.isspace() != True ]
    returnData = []
    for item in data:
        returnData.extend([ x for x in item.split()])
    returnData = list(dict.fromkeys(returnData))
    del html_parser
    return returnData

def is_match(termList, matchList):
    for search in matchList: # to do: make all termList items must be 90
        for item in termList:
            if fuzz.WRatio(item, search) > 90:
                return True
    return False

def get_emails(email_add, password, imap_server, port):
    print('Connecting to server...')
    with IMAP4_SSL(imap_server, port=port) as mail_connection:
        print('Logging in to server...')
        mail_connection.login(email_add, password)
        print('Log in OK!')
        if 'Sorted' not in mail_connection.list():
            mail_connection.create('Sorted')

        mail_connection.select('INBOX')
        typ, messages = mail_connection.search(
            None,
            'SEEN'
        )
        print('Got messages!')
        if typ == 'OK' and messages[0]:
            for index, num in enumerate(messages[0].split()):
                typ, data = mail_connection.fetch(num, '(RFC822)')
                print(num)
                message = message_from_bytes(data[0][1])
                yield message

def manager():
    while True:
        message = message_queue.get()
        process_message(message)
        message_queue.task_done()
    
def process_message(message):
    with print_lock:
        print('[STARTED MSG] ', end = '')
    important_keys = {
        'Date': message.get('Date'),
        'Sender': message.get('Sender'),
        'To': message.get('To'),
        'From': message.get('From'),
        'Subject': message.get('Subject')
    }
    for part in message.walk():
        if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'html':
            if is_match(parse_html(part), ['Leo', 'Qi']):
                with print_lock:
                    print('TRUE  [Finished]')
                return True
    with print_lock:
        print('FALSE [Finished]')

    with count_lock:
        global count
        count += 1
    
    return False

    """
    mail_connection.copy(num, 'Sorted') # was here
    #changes status
    typ, data = mail_connection.store(num, '+FLAGS', '\\Seen')
    """
    
def main(email_add, password, imap_server, port):
    start = time()
    global count
    for x in range(30):
        t = threading.Thread(target=manager)
        t.daemon = True
        t.start()
        
    messages = get_emails(email_add, password, imap_server, port)
    if messages:
        for message in messages:
            message_queue.put(message)
        
        message_queue.join()
        end = time()
        print('Finished Processing ALL ************')
        print(f'Processed {count} messages in {end - start} ms')
    else:
        print('No messages')

if __name__ == '__main__':
    USERNAME, PASSWORD, IMAPSERVER, PORT = get_config()
    messages = main(USERNAME, PASSWORD, IMAPSERVER, PORT)
