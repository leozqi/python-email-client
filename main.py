from email import message_from_bytes, parser
from imaplib import IMAP4_SSL
from html.parser import HTMLParser
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
from multiprocessing import Pool
from time import time
from os import getenv
from queue import Queue
from threading import Thread

class EmailConnection():
    """
    Defines an email connection to our IMAP server
    """
    def __init__(self):
        #print('Getting config... ', end='')
        self.get_config()
        #print('Got config!')
        #print('Connecting to server... ', end='')
        self.conn = IMAP4_SSL(self.imap, self.port)
        #print('Connected!')
        #print('Logging in... ', end='')
        self.conn.login(self.email, self.pswrd)
        #print('Logged in!')

    def __del__(self):
        self.conn.close()
        self.conn.logout()

    def get_config(self):
        load_dotenv()
        self.email = getenv('USER_EMAIL')
        self.pswrd = getenv('USER_PASSWORD')
        self.imap = getenv('IMAP_SERVER')
        self.port = getenv('PORT')

class EmailHTMLParser(HTMLParser):
    """
    Extends the HTMLParser class for our own email parser
    """
    def __init__(self, *args, **kwargs):
        super(EmailHTMLParser, self).__init__(*args, **kwargs)
        self.data = []
        
    def handle_data(self, data):
        self.data.append(data)

    def clear_data(self):
        self.data = []

def parse_html(part, html_parser):
    if part is not None:
        try:
            html_parser.feed(part.get_payload()) 
        except NotImplementedError:
            return ['']
    else:
        return ['']
    data = [ x.strip().lower() for x in html_parser.data if x.isspace() != True ]
    html_parser.clear_data()
    return data

def get_words(part, html_parser):
    data = parse_html(part, html_parser)
    returnData = []
    for item in data:
        returnData.extend([ x for x in item.split()])
    returnData = list(dict.fromkeys(returnData))
    return returnData

def specific_match(termList, matchList):
    for term in termList:
        for search in matchList:  
            if term in search:
                return True
    return False

def ratio_is_match(termList, matchList):
    for item in termList:
        for search in matchList: # to do: make all termList items must be 90
            if fuzz.WRatio(item, search) > 90:
                return True
    return False

def fetch_one(inbox, outbox):
    email = EmailConnection()
    conn = email.conn
    conn.select('INBOX')
    
    while True:
        num = inbox.get()
        typ, data = conn.fetch(num, '(RFC822)')
        outbox.put((message_from_bytes(data[0][1]), num))
        inbox.task_done()
        print('Completed 1')

def get_emails(conn):
    mail_connection = conn
    print(
        'There are '
        + str(mail_connection.select('INBOX')[1])
        + ' messages in INBOX'
    )
    mail_connection.select('INBOX')
    typ, messages = mail_connection.search(
        None,
        'ALL'
    )
    message_list = []
    append = message_list.append
    print('Getting Messages... ', end='')
    if typ == 'OK' and messages[0]:
        print('Got messages!')
        message_queue = Queue()
        finished_queue = Queue()
        for x in range(10):
            worker = Thread(target=fetch_one, args=(message_queue, finished_queue))
            worker.setDaemon(True)
            worker.start()
        
        for index, num in enumerate(messages[0].split()):
            message_queue.put(num)
        message_queue.join()

        message_list = []
        while not finished_queue.empty():
            message_list.append(finished_queue.get())
            finished_queue.task_done()
        return message_list
    else:
        print('No message response')
        return ['']

def copy_emails(conn, msg_list):
    mail_connection = conn
    print('Logging in to server...')
    mail_connection.login(email_add, password)
    print('Log in OK!')
    if 'Sorted' in mail_connection.list():
        mail_connection.delete(mailbox)
    mail_connection.create('Sorted')
    mail_connection.select('INBOX')
    for num in msg_list:
        mail_connection.copy(num, 'Sorted')
    print('Finished!')

def process_message(message_info):
    html_parser = EmailHTMLParser()
    message = message_info[0]
    num = message_info[1]
    important_keys = {
        'Date': message.get('Date'),
        'Sender': message.get('Sender'),
        'To': message.get('To'),
        'From': message.get('From'),
        'Subject': message.get('Subject')
    }
    for part in message.walk():
        if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'html':
            if ratio_is_match(get_words(part, html_parser), ['Leo', 'Qi']):
            #if specific_match(parse_html(part), ['dropbox']):
                return num
    return False

def main():
    print('Connecting to server... ', end='')
    connection = EmailConnection()
    mail_connection = connection.conn
    print('Connected!')
    start = time()
    count = 0
    messages = get_emails(mail_connection)
    if messages:
        copy_list = []
        with Pool(processes=20) as pool:
            for i in pool.imap_unordered(process_message, messages, 1):
                print(i)
                count += 1
                if i != False:
                    copy_list.append(i)

        end = time()
        print('Finished Processing ALL ************')
        print(f'Processed {count} messages in {end - start}s')
        #copy_emails(mail_connection, copy_list)
    else:
        print('No messages')

if __name__ == '__main__':
    messages = main()

## ------ Other Stuff ------ ##
##def fetch_one(val):
##    num = val[1]
##    conn = open_conn(
##        getenv('USER_EMAIL'),
##        getenv('USER_PASSWORD'),
##        getenv('IMAP_SERVER'),
##        getenv('PORT')
##    )
##    conn.select('INBOX')
##    typ, data = conn.fetch(num, '(RFC822)')
##    conn.close()
##    conn.logout()
##    return (message_from_bytes(data[0][1]), num)
##
##mail_connection.copy(num, 'Sorted') # was here
###changes status
##typ, data = mail_connection.store(num, '+FLAGS', '\\Seen')
