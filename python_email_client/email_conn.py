from email import message_from_bytes
from imaplib import IMAP4_SSL
from queue import Queue
from os import getenv
from threading import Thread
from dotenv import load_dotenv

class EmailConnection():
    def __init__(self, print_func=None):
        """
        Defines an email connection to our IMAP server.
        Requires a valid dotenv file to be present.
        Be sure to delete the object afterwards to log out of the server.

        Keyword arguments
        print_func -- An Application() class's put_msg function
        """
        self.get_config()
        self.conn = IMAP4_SSL(self.imap, self.port)
        self.conn.login(self.email, self.pswrd)
        self.print = print_func
        
    def __del__(self):
        try:
            self.conn.close()
        except:
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
                self.print('Found existing mailbox, deleting... ')
                self.conn.delete(sort_folder)
                self.print('Finished!')
            self.print(f'Creating mailbox {sort_folder} ... ')
            self.conn.create(sort_folder)
            self.print('Finished!')
            self.conn.select('INBOX')
            self.print('Copying Emails -> ')
            for num in msg_list:
                self.conn.copy(num, sort_folder)
                self.print('.')
            self.print('\nFinished!')

        def move_emails(self, msg_list, sort_folder):
            if self.search_mailboxes(sort_folder):
                self.print('Found existing mailbox, deleting... ')
                self.conn.delete(sort_folder)
                self.print('Finished!')
            self.print(f'Creating mailbox {sort_folder} ... ')
            self.conn.create(sort_folder)
            self.print('Finished!')
            self.conn.select('INBOX')
            self.print('Moving Emails -> ')
            for num in msg_list:
                self.conn.copy(num, sort_folder)
                self.conn.store(num, '+FLAGS', '\\Deleted')
                self.print('.')
            self.conn.expunge()
            self.print('\nFinished!')

        def search_mailboxes(self, sort_folder):
            status, response = self.conn.list()
            if status == 'OK':
                for item in response:
                    stritem = item.decode('utf-8')
                    if sort_folder in stritem:
                        return True
            return False
## End class EmailConnection ##

class EmailGetter:
    def __init__(self, conn, threads, print_func):
        """
        Keyword arguments:
        conn -- An EmailConnection connection (EmailConnection.conn)
        threads -- An integer representing the amount of threads to spawn
        print_func -- An Application() class's put_msg function
        """
        self.active = True
        self.conn = conn
        self.message_queue = Queue()
        self.finished_queue = Queue()
        self.workers = []
        self.print = print_func
        self.print('Creating threads...')
        for x in range(threads):
            self.workers.append(Thread(target=self.fetch))
            self.workers[-1].setDaemon(True)
            self.workers[-1].start()
        
        self.emails = self.get_emails()

    def __del__(self):
        self.active = False

    def get_emails(self):
        self.print(
            'There are '
            + str(self.conn.select('INBOX')[1])
            + ' messages in INBOX'
        )
        self.conn.select('INBOX')
        typ, messages = self.conn.search(None, 'ALL')
        self.print('Searching messages... ')
        if typ == 'OK' and messages[0]:
            self.print('Got list of messages!')
            self.print('Downloading messages -> ')

            for index, num in enumerate(messages[0].split()):
                self.message_queue.put(num)

            self.message_queue.join()
            self.print('\nFinished!')
            self.print('\nSorting messages... ')
            msg_list = list(self.finished_queue.queue)
            self.print('Finished sorting messages!')
            return msg_list
        else:
            self.print('No message response')
            return ['']

    def fetch(self):
        email = EmailConnection()
        conn = email.conn
        try:
            conn.select('INBOX')
        except:
            return False
        
        while self.active:
            msg_num = self.message_queue.get()
            status, data = conn.fetch(msg_num, '(RFC822)')
            message = message_from_bytes(data[0][1])
            self.finished_queue.put((message, msg_num))
            self.message_queue.task_done()
            self.print('.')
        return True

    def get_subjects(self, num_list):
        subject_list = []
        for item in self.emails:
            if item[1] in num_list:
                subject_list.append(item[0].get('Subject'))
        return subject_list
## End EmailGetter class ##