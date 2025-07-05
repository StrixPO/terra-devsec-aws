import re

def validate_paste_id(paste_id):
    return re.match(r'^[a-zA-Z0-9_-]{3,50}$', paste_id)
