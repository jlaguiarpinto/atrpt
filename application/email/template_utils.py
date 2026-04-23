#atrpt/application/email/template_utils.py

class SafeDict(dict):

    def __missing__(self, key):
        return "{" + key + "}"