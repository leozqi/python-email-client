from html.parser import HTMLParser
from fuzzywuzzy import fuzz
import utils

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

def parse_html(part, html_parser):
    if part is not None:
        try:
            html_parser.feed(part.get_payload())
        except NotImplementedError:
            return ['']
    else:
        return ['']
    data = [x.strip().lower() for x in html_parser.data if x.isspace() != True]
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
    data = [ x.strip() for x in data if x.isspace() != True ]
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
    html_parser = EmailHTMLParser()
    message = message_info[0]
    num = message_info[1]
    important_keys = {
        'Date': utils.email_to_datetime(message.get('Date')),
    #'Sender': message.get('Sender'),
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

    del html_parser
    return False