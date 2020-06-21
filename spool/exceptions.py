class SpoolError(Exception):
    """Base class for exceptions."""

    def __init__(self, msg=None):
        self.msg = msg

    def __str__(self):
        if not self.msg:
            return 'Undefined error occured.'

        return str(self.msg)
