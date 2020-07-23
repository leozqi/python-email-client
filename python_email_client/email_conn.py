from email import message_from_bytes
from imaplib import IMAP4_SSL
from queue import Queue
from os import getenv
from threading import Thread
from dotenv import load_dotenv

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
        except:
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