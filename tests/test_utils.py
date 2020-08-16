from python_email_client import utils

# Utils testing
def test_email_to_datetime():
    assert utils.email_to_datetime('Mon, 20 Nov 1995 19:12:08 -0500').timestamp() == 816912728.0

test_unicode = '🌥🈽💭🸪📰🊀🧊🁨🀉🄽🌷🖇🹶🶱👖🏛🰦🭟🪝🨑🢭🵟🄻🤸🡚🻨🻖🾩🤚🌍🤑🮴🬍🪻🎣🬌💕🗥🎰😴🤔🞭🇭'
def test_parse_sub():
    returned = utils.parse_sub(test_unicode)
    assert len(returned) == 3
    assert returned == b'...'
    assert isinstance(returned, bytes)

def test_parse_complete_sub():
    returned = utils.parse_complete_sub(test_unicode)
    assert len(returned) == 0
    assert isinstance(returned, str)

def test_parse_payload():
    returned = utils.parse_payload(test_unicode)
    for char in test_unicode:
        assert (char not in returned)

def test_make_tag_list():
    sample_tags = ',blah, here some more blah, blah blah, hello there,,'
    returned = utils.make_tag_list(sample_tags)
    for tag in returned:
        assert (tag != '') and (not tag.isspace())

def test_merge_tags():
    sample_tag_set_1 = ',blah, here some more blah, blah blah, hello there,,'
    sample_tag_set_2 = ',blah, kinda blah but less, blah blah, hello there,,'
    returned = utils.merge_tags(sample_tag_set_1, sample_tag_set_2)
    assert len(returned) == 66
    assert returned == 'blah,here some more blah,blah blah,hello there,kinda blah but less'