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
from functools import partial

class EmailConnection():
    """
    Defines an email connection to our IMAP server.
    Requires a valid dotenv file to be present.
    Be sure to delete the object afterwards to log out of the server.
    """
    def __init__(self):
        self.get_config()
        self.conn = IMAP4_SSL(self.imap, self.port)
        self.conn.login(self.email, self.pswrd)

    def __del__(self):
        self.conn.close()
        self.conn.logout()

    def get_config(self):
        load_dotenv()
        self.email = getenv('USER_EMAIL')
        self.pswrd = getenv('USER_PASSWORD')
        self.imap = getenv('IMAP_SERVER')
        self.port = getenv('PORT')

        if not (self.email and self.pswrd and self.imap and self.port):
            raise ValueError(
                'Add a file with name ".env" with the correct values:\n'
                'USER_EMAIL: the user\'s email.\n'
                'USER_PASSWORD: the user\'s password for that email.\n'
                'IMAP_SERVER: the imap server of the email address.\n'
                'PORT: the port of the imap server. Usually 993.\n'
            )

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
        print('.', end='')

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
    print('Searching messages... ', end='')
    if typ == 'OK' and messages[0]:
        print('Got list of messages!')
        print('Downloading messages -> ', end='')
        message_queue = Queue()
        finished_queue = Queue()
        for x in range(10):
            worker = Thread(target=fetch_one, args=(message_queue, finished_queue))
            worker.setDaemon(True)
            worker.start()
        
        for index, num in enumerate(messages[0].split()):
            message_queue.put(num)

        message_queue.join()
        print('\nFinished!')
        print('\nSorting messages... ', end='')
        message_list = list(finished_queue.queue)
        print('Finished sorting messages!')
        return message_list
    else:
        print('No message response')
        return ['']

def copy_emails(conn, msg_list, sort_folder):
    if search_mailboxes(conn, sort_folder):
        print('Found existing mailbox, deleting... ', end='')
        conn.delete(sort_folder)
        print('Finished!')
    print('Creating Sorted mailbox... ', end='')
    conn.create(sort_folder)
    print('Finished!')
    conn.select('INBOX')
    print('Copying Emails -> ', end='')
    for num in msg_list:
        conn.copy(num, sort_folder)
        print('.', end='')
    print('\nFinished!')

def move_emails(conn, msg_list, sort_folder):
    if search_mailboxes(conn, sort_folder):
        print('Found existing \'Sorted\', deleting... ', end='')
        conn.delete(sort_folder)
        print('Finished!')
    print('Creating Sorted mailbox... ', end='')
    conn.create(sort_folder)
    print('Finished!')
    conn.select('INBOX')
    print('Moving Emails -> ', end='')
    for num in msg_list:
        conn.copy(num, sort_folder)
        conn.store(num, '+FLAGS', '\\Deleted')
        print('.', end='')
    conn.expunge()
    print('\nFinished!')

def search_mailboxes(conn, sort_folder):
    status, response = conn.list()
    if status == 'OK':
        for item in response:
            stritem = item.decode('utf-8')
            if sort_folder in stritem:
                return True

    return False

def process_message(message_info, search_list):
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
            if ratio_is_match(get_words(part, html_parser), search_list):
                return num
    return False

def main():
    print('Connecting to server... ', end='')
    connection = EmailConnection()
    mail_connection = connection.conn
    print('Connected!')
    count = 0
    yes_count = 0
    no_count = 0
    searches = input('Enter comma-separated search terms: ').strip().lower().split(',')
    print('Searching for terms:')
    print('====================')
    for search in searches:
        print(search)
    
    start = time()
    messages = get_emails(mail_connection)
    if messages:
        print('Processing messages -> ', end='')
        copy_list = []
        process_message_searches = partial(process_message, search_list=searches)
        with Pool(processes=20) as pool:
             for i in pool.imap_unordered(process_message_searches, messages, 20):
                count += 1
                if i != False:
                    copy_list.append(i)
                    print('O', end='')
                    yes_count += 1
                else:
                    print('X', end='')
                    no_count += 1

        try:
            percent = no_count / yes_count
        except ZeroDivisionError:
            percent = 0
        end = time()
        print('\n********** Finished processing emails **********')
        print(f'Processed {count} messages in {end - start}s')
        print(f'{percent}% ({yes_count}/{yes_count + no_count})of messages match')
        if len(copy_list) > 0:
            method = ''
            while method not in ('c', 'm', 'd'):
                method = input('Enter whether to copy, move or display: (C, M, D): ').strip().lower()
            print(f'Method: {method}')
            
            if method == 'c' or method == 'm':
                store_folder = input('Enter storage folder: ').strip()
                store_folder = "".join(store_folder.split())
                if method == 'c':
                    copy_emails(mail_connection, copy_list, store_folder)
                elif method == 'm':
                    move_emails(mail_connection, copy_list, store_folder)
            elif method == 'd':
                print(copy_list)
        else:
            print('No messages fetched...')

        print('Finished all operations for this thread')
        del connection      
    else:
        print('No messages')
    
if __name__ == '__main__':
    while True:
        response = ''
        while response not in ('y', 'n'):
            response = input('Start a new session? (Y/N): ').strip().lower()
        if response == 'y':
            print('OK! Starting new session...')
            main()
        else:
            print('Shutting down...')
            break
