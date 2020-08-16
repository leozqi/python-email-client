from datetime import datetime
import time
from email.header import Header, decode_header, make_header
import quopri
import email.utils
import os
from dotenv import load_dotenv
import platform

def email_to_datetime(email_date):
    '''Returns a datetime object from (email_date) in RFC 2822 format
    Keyword arguments:
    email_date -- a date in RFC 2822 format:
                  eg. 'Mon, 20 Nov 1995 19:12:08 -0500'
    
    Returns: datetime.datetime object
    '''
    return datetime.fromtimestamp(
        time.mktime(email.utils.parsedate(email_date)))

def parse_sub(subject):
    '''Returns an ascii encoded bytes string that ignores complex unicode'''
    decoded = make_header(decode_header(subject))
    if len(str(decoded)) <= 40:
        return str(decoded).encode(encoding='ascii', errors='ignore')
    else:
        return ''.join((str(decoded)[:40], '...')).encode(encoding='ascii',
                                                          errors='ignore')

def parse_complete_sub(subject):
    decoded = make_header(decode_header(subject))
    return str(decoded).encode(encoding='ascii', errors='ignore').decode('utf-8')

def parse_payload(payload):
    decoded = payload.encode(encoding='ascii', errors='ignore').decode('utf-8')
    decoded = quopri.decodestring(decoded).decode(encoding='utf-8', errors='ignore')
    count = 0
    terms = [] #[(search_term, value)]
    while count < len(decoded):
        if ord(decoded[count]) > 65535:
            terms.append(decoded[count])
        count += 1
    for t in terms:
        decoded = decoded.replace(t, ''.join(('{U', str(ord(t)), '}')))
    return decoded

def get_store_path():
    if platform.system() == 'Windows':
        return os.path.join(os.path.expanduser('~'), 'AppData\\Local\\Python Email')
    else:
        return os.path.join(os.path.expanduser('~'), 'Python Email')

def make_tag_list(tags):
    '''Makes a list from a string of tags of form:
    'tag,anothertag,finaltag' and returns that list.
    '''
    return [ t.strip() for t in tags.split(',') if not t.isspace() and t != '' ]

def merge_tags(tagstr1, tagstr2):
    '''Merges the tags from (tagstr2) into the tags from (tagstr1) to
    form a combined string of tags. Guaranteed no duplicate tags during
    the process.
    '''
    taglist1 = make_tag_list(tagstr1)
    taglist2 = make_tag_list(tagstr2)
    for tag in taglist2:
        if tag not in taglist1:
            taglist1.append(tag)
    return ','.join(taglist1)

def is_whitespace(string):
    if (string.isspace()) or (string == ''):
        return True
    else:
        return False