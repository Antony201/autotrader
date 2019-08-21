import peony

from utils import singleton


@singleton
class TwitterPeonySingle:
    def __new__(cls, *args, **kwargs):
        return peony.PeonyClient(*args, **kwargs)
