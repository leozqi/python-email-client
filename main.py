from email import message_from_bytes, parser
from imaplib import IMAP4_SSL
from html.parser import HTMLParser
from dotenv import load_dotenv
from fuzzywuzzy import fuzz
import os

class EmailHTMLParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        super(EmailHTMLParser, self).__init__(*args, **kwargs)
        self.data = []
        
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
    html_parser.feed(part.get_payload())
    data = html_parser.data
    data = [ x.strip() for x in data if x.isspace() != True ]
    returnData = []
    for item in data:
        returnData.extend(item.split())

    del html_parser
    return returnData

def is_match(termList, matchList):
    for search in matchList:
        for item in termList:
            if fuzz.WRatio(item, search) > 80:
                return True

def main(email_add, password, imap_server, port):
    print('Connecting to server...')
    with IMAP4_SSL(imap_server, port=port) as mail_connection:
        print('Logging in to server...')
        mail_connection.login(email_add, password)
        print('Log in OK!')
        if 'Sorted' not in mail_connection.list():
            mail_connection.create('Sorted')
            
        print(mail_connection.list())
        mail_connection.select('INBOX')
        typ, messages = mail_connection.search(
            None,
            'SEEN'
        )
        print('Got messages!')
        if typ == 'OK' and messages[0]:
            for index, num in enumerate(messages[0].split()):
                typ, data = mail_connection.fetch(num, '(RFC822)')
                message = message_from_bytes(data[0][1])
                print(message.keys())
                for part in message.walk():
                    if part.get_content_maintype() == 'text' and part.get_content_subtype() == 'html':
                        if is_match(parse_html(part), ['Dropbox']):
                            print(part.get_payload())
                            #mail_connection.copy(num, 'Sorted') # was here
                #changes status typ, data = mail_connection.store(num, '+FLAGS', '\\Seen')

if __name__ == '__main__':
    USERNAME, PASSWORD, IMAPSERVER, PORT = get_config()
    messages = main(USERNAME, PASSWORD, IMAPSERVER, PORT)
