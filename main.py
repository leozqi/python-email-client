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

class PrintLogger():
    def __init__(self):
        self.on = True
        self.q = Queue()
        self.printer = Thread(target=self.print_messages())
        self.printer.setDaemon(True)
        self.printer.start()
    
    def print(self):
        while self.on:
            if not self.q.empty():
                message = self.q.get()
                if message[1] == True:
                    print(message[0])
                else:
                    print(message[0], end="")
                self.q.task_done()
        
    def put(self, message, newln=True):
        """
        Put a message into the queue to be printed.

        Keyword arguments:
        message -- a tuple consisting of a message
        newln -- whether the message ends in a newline (default True)
        """
        self.q.put((message, newln))
## End class PrintLogger() ##

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
        try:
            self.conn.close()
        except imaplib.error:
            pass
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

    def copy_emails(self, msg_list, sort_folder):
        if self.search_mailboxes(sort_folder):
            print('Found existing mailbox, deleting... ', end='')
            self.conn.delete(sort_folder)
            print('Finished!')
        print(f'Creating mailbox {sort_folder} ... ', end='')
        self.conn.create(sort_folder)
        print('Finished!')
        self.conn.select('INBOX')
        print('Copying Emails -> ', end='')
        for num in msg_list:
            self.conn.copy(num, sort_folder)
            print('.', end='')
        print('\nFinished!')

    def move_emails(self, msg_list, sort_folder):
        if self.search_mailboxes(sort_folder):
            print('Found existing mailbox, deleting... ', end='')
            self.conn.delete(sort_folder)
            print('Finished!')
        print(f'Creating mailbox {sort_folder} ... ', end='')
        self.conn.create(sort_folder)
        print('Finished!')
        self.conn.select('INBOX')
        print('Moving Emails -> ', end='')
        for num in msg_list:
            self.conn.copy(num, sort_folder)
            self.conn.store(num, '+FLAGS', '\\Deleted')
            print('.', end='')
        self.conn.expunge()
        print('\nFinished!')

    def search_mailboxes(self, sort_folder):
        status, response = self.conn.list()
        if status == 'OK':
            for item in response:
                stritem = item.decode('utf-8')
                if sort_folder in stritem:
                    return True
        return False
## End class EmailConnection ##

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
## End class EmailHTMLParser ##

class EmailGetter:
    def __init__(self, conn, threads):
        """
        Keyword arguments:
        conn -- An EmailConnection connection (EmailConnection.conn)
        threads -- An integer representing the amount of threads to spawn
        """
        self.active = True
        self.conn = conn
        self.message_queue = Queue()
        self.finished_queue = Queue()
        self.workers = []

        for x in range(threads):
            self.workers.append(Thread(target=self.fetch))
            self.workers[-1].setDaemon(True)
            self.workers[-1].start()
        
        self.emails = self.get_emails()

    def __del__(self):
        self.active = False

    def get_emails(self):
        print(
            'There are '
            + str(self.conn.select('INBOX')[1])
            + ' messages in INBOX'
        )
        self.conn.select('INBOX')
        typ, messages = self.conn.search(None, 'ALL')
        print('Searching messages... ', end='')
        if typ == 'OK' and messages[0]:
            print('Got list of messages!')
            print('Downloading messages -> ', end='')

            for index, num in enumerate(messages[0].split()):
                self.message_queue.put(num)

            self.message_queue.join()
            print('\nFinished!')
            print('\nSorting messages... ', end='')
            msg_list = list(self.finished_queue.queue)
            print('Finished sorting messages!')
            return msg_list
        else:
            print('No message response')
            return ['']

    def fetch(self):
        email = EmailConnection()
        conn = email.conn
        try:
            conn.select('INBOX')
        except imaplib.IMAP4.error:
            return False
        
        while self.active:
            msg_num = self.message_queue.get()
            status, data = conn.fetch(msg_num, '(RFC822)')
            self.finished_queue.put((message_from_bytes(data[0][1]), msg_num))
            self.message_queue.task_done()
            print('.', end='')
        return True

    def get_subjects(self, num_list):
        subject_list = []
        for item in self.emails:
            if item[1] in num_list:
                subject_list.append(item[0].get('Subject'))
        return subject_list
## End EmailGetter class ##

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
        for search in matchList:
            if len(item) >= len(search) - 1 and fuzz.WRatio(item, search) > 90:
                return True
    return False

def process_message(message_info, subject, to_ln, from_ln, search_list):
    html_parser = EmailHTMLParser()
    message = message_info[0]
    num = message_info[1]
    important_keys = {
        #'Date': message.get('Date'),
        #'Sender': message.get('Sender'),
        'To': message.get('To'),
        'From': message.get('From'),
        'Subject': message.get('Subject')
    }
    if subject and specific_match([important_keys['Subject'].lower()], search_list):
        return num
    if to_ln and specific_match([important_keys['To'].lower()], search_list):
        return num
    if from_ln and specific_match([important_keys['From'].lower()], search_list):
        return num
    
    for part in message.walk():
        if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'html':
            if ratio_is_match(get_words(part, html_parser), search_list):
                return num
    return False

def askForBool(message):
    subject = ''
    while subject not in ('y', 'n'):
        subject = input(f'{message} (Y/N): ').lower()
    if subject == 'y':
        return True
    else:
        subject = False

def main():
    print('Connecting to server... ', end='')
    email_server = EmailConnection()
    conn = email_server.conn
    print('Connected!')
    count = 0
    yes_count = 0
    no_count = 0
    searches = input('Enter comma-separated search terms: ').replace(' ', '').lower().split(',')
    print('searches')
    print('Searching for terms:')
    print('====================')
    for search in searches:
        print(search)
    print('====================')
    threads = 11
    while threads > 10:
        try:
            threads = int(input('Enter amount of threads (Max 10): '))
        except ValueError:
            pass
    start = time()
    email_get = EmailGetter(conn, threads)
    messages = email_get.emails
    if messages:
        copy_list = []
        subject = askForBool('Search subject lines?')
        to_ln = askForBool('Search To: lines?')
        from_ln = askForBool('Search From: lines?')
        process_message_searches = partial(
            process_message,
            subject=subject,
            to_ln=to_ln,
            from_ln=from_ln,
            search_list=searches
        )
        print('\nProcessing messages -> ', end='')
        with Pool() as pool:
             for i in pool.imap_unordered(process_message_searches, messages):
                count += 1
                if i != False:
                    copy_list.append(i)
                    print('O', end='')
                    yes_count += 1
                else:
                    print('X', end='')
                    no_count += 1
        try:
            percent = (yes_count/no_count) * 100
        except ZeroDivisionError:
            percent = 0
        end = time()
        print('\n\n********** Finished processing emails **********')
        print(f'Processed {count} messages in {end - start}s')
        print(f'{percent}% ({yes_count}/{yes_count + no_count}) of messages match')
        if len(copy_list) > 0:
            method = ''
            while method not in ('c', 'm', 'd'):
                method = input('Enter whether to copy, move or display: (C, M, D): ').strip().lower()
            print(f'Method: {method}')
            
            if method == 'c' or method == 'm':
                store_folder = input('Enter storage folder: ').strip()
                store_folder = "".join(store_folder.split())
                if method == 'c':
                    email_server.copy_emails(copy_list, store_folder)
                elif method == 'm':
                    email_server.move_emails(copy_list, store_folder)
            elif method == 'd':
                subjects = email_get.get_subjects(copy_list)
                print('\nSubject Lines:')
                print('====================')
                for subject in subjects:
                    print(subject)
                print('====================')
        else:
            print('\nNo messages fetched...')

        print('\nFinished all operations for this thread')
        del email_get
        del email_server      
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
