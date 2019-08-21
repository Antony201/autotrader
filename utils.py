from decimal import Decimal


def norm(d: Decimal):
    if int(d) == d:
        return f'{d.normalize():f}'
    only_8_digits = Decimal(f'{d.normalize():.8f}')
    return f'{only_8_digits.normalize():f}'


def singleton(cls):
    instances = {}

    def getinstance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return getinstance
