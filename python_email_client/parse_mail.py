from html.parser import HTMLParser
from fuzzywuzzy import fuzz
import utils

class EmailHTMLParser(HTMLParser):
    '''Extends the HTMLParser class for our own email parser'''
    def __init__(self, *args, **kwargs):
        super(EmailHTMLParser, self).__init__(*args, **kwargs)
        self.data = []
        
    def handle_data(self, data):
        self.data.append(data)

    def clear_data(self):
        self.data = []
## End class EmailHTMLParser ##

html_parser = EmailHTMLParser()

def parse_html(part, html_parser):
    if part is not None:
        try:
            html_parser.feed(part.get_payload())
        except NotImplementedError:
            return ['']
    else:
        return ['']
    data = [x.strip().lower() for x in html_parser.data if not x.isspace()]
    html_parser.clear_data()
    return data

def get_words(part, html_parser):
    data = parse_html(part, html_parser)
    returnData = []
    for item in data:
        returnData.extend([ x for x in item.split()])
    returnData = list(dict.fromkeys(returnData))
    return returnData

def get_words_txt(part):
    txt = ''
    if part is not None:
        txt = part.get_payload()
    else:
        return []
    data = txt.strip().lower().split()
    data = [x.strip() for x in data if not x.isspace()]
    return data

def specific_match(termList, matchList, allMatch=False):
    for term in termList:
        matches = 0
        for search in matchList:
            if term in search:
                if allMatch:
                    matches += 1
                else:
                    return True
        if allMatch:
            if matches == len(matchList):
                return True
    return False

def ratio_is_match(termList, matchList, allMatch=False):
    for item in termList:
        matches = 0
        for search in matchList:
            if len(item) >= len(search) - 1 and fuzz.WRatio(item, search) > 90:
                if allMatch:
                    matches += 1
                else:
                    return True
        if allMatch:
            if matches == len(matchList):
                return True

    return False

def process_message(message_info, subject, to_ln, from_ln, search_list,
                    all_match=False):
    '''Processes an email by parsing its contents and then returning
    the message's data if it matches a term in the search list, or False
    otherwise.
    Keyword arguments:
    message_info -- a tuple of form (email_msg, email_num integer). See
                    README.md, Documentation.
    subject -- a boolean value (or integer) that represents whether or
               not to search in the subject line of an email.
    to_ln -- a boolean value representing whether or not to search in
             the to line of an email.
    from_ln -- a boolean value representing whether or not to search in
               the from line of an email.
    search_list -- a list or tuple of possible search values (as
                   strings)
    all_match -- a boolean value representing whether or not to match
                 all search values in search_list. (Default False)
    '''
    global html_parser
    message = message_info[0]
    num = message_info[1]
    important_keys = {
        'Date': utils.email_to_datetime(message.get('Date')),
        'To': message.get('To'),
        'From': message.get('From'),
        'Subject': message.get('Subject')
    }
    if subject and specific_match([important_keys['Subject'].lower()],
                                  search_list, all_match):
        return important_keys
    if to_ln and specific_match([important_keys['To'].lower()],
                                search_list, all_match):
        return important_keys
    if from_ln and specific_match([important_keys['From'].lower()],
                                  search_list, all_match):
        return important_keys
    
    for part in message.walk():
        if part.get_content_maintype() == 'text':
            if part.get_content_subtype() == 'html':
                if ratio_is_match(get_words(part, html_parser),
                                  search_list, all_match):
                    return important_keys
            elif part.get_content_subtype() == 'plain':
                if ratio_is_match(get_words_txt(part),
                                  search_list, all_match):
                    return important_keys

    html_parser.clear_data()
    return False