from email import message_from_bytes
from imaplib import IMAP4_SSL
from queue import Queue
from threading import Thread
import utils

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
        self.config = utils.get_config()
        self.email = self.config['email']
        self.pswrd = self.config['pswrd']
        self.imap = self.config['imap']
        self.port = self.config['port']

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
        self.print('Finished!')

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
    def __init__(self, conn, threads, print_func, bar_func=None):
        """
        Keyword arguments:
        conn -- An EmailConnection connection (EmailConnection.conn)
        threads -- An integer representing the amount of threads to spawn
        print_func -- An Application() class's put_msg function
        bar_func -- An Application() class's add_bar function
        """
        self.active = True
        self.conn = conn
        self.message_queue = Queue()
        self.finished_queue = Queue()
        self.workers = []
        self.print = print_func
        self.bar = bar_func
        self.emails = None

    def __del__(self):
        self.active = False

    def get_emails_online(self, threads, since):
        self.print('Creating threads...')
        msg_amt = int(self.conn.select('INBOX')[1][0].decode('utf-8'))
        self.print(
            'There are '
            + str(msg_amt)
            + ' messages in INBOX'
        )
        msg_bar = 100 / msg_amt
        
        self.conn.select('INBOX')

        # Search code
        last_date = since
        search_str = ''
        if last_date == None:
            search_str = 'ALL'
        else:
            search_str = f'(SINCE "{last_date}")'
        typ, messages = self.conn.search(
            None, 
            search_str
        )
        self.print('Searching messages... ')
        if typ == 'OK' and messages[0]:
            for x in range(threads):
                self.workers.append(Thread(target=self.fetch, args=(msg_bar,)))
                self.workers[-1].setDaemon(True)
                self.workers[-1].start()

            self.print('Got list of messages!')
            self.print('Downloading messages -> ')
            for index, num in enumerate(messages[0].split()):
                self.message_queue.put(num)

            self.message_queue.join()
            self.print('Finished!')
            self.print('Shutting down threads...')
            for worker in self.workers:
                self.message_queue.put(None)
            
            self.message_queue.join()
            self.print('Threads finished.')
            self.print('Sorting messages... ')
            msg_list = list(self.finished_queue.queue)
            self.print('Finished sorting messages!')
            self.active = False
            self.emails = msg_list
            return True
        else:
            self.print('No message response')
            self.emails = []
            return False

    def fetch(self, inc_amt):
        """
        Keyword arguments:
        inc_amt -- the amount that progress bar should 
                   increment for message proccessed.
        """
        email = EmailConnection()
        conn = email.conn
        try:
            conn.select('INBOX')
        except:
            return False
        
        while self.active:
            msg_num = self.message_queue.get()
            if msg_num == None:
                self.message_queue.task_done()
                return True
            status, data = conn.fetch(msg_num, '(RFC822)')
            message = message_from_bytes(data[0][1])
            self.finished_queue.put((message, msg_num))
            self.message_queue.task_done()
            self.print(f'Got message {msg_num}')
            if self.bar != None:
                self.bar(inc_amt)
        return True

    def get_subjects(self, num_list):
        subject_list = []
        for item in self.emails:
            if item[1] in num_list:
                subject_list.append(item[0].get('Subject'))
        return subject_list
## End EmailGetter class ##