from typing import List

import yaml

from common import NTCredential

FILENAME = './credentials.yaml'


class NonUniqueCredentials(Exception):
    pass


def read_file():
    with open(FILENAME) as f:
        return f.read()


def get_credentials():
    return check_unique(
        [
            NTCredential(
                owner,
                exchange_name,
                credential['api_key'],
                credential['secret_key']
            )
            for exchange_name, accounts in yaml.load(read_file(), Loader=yaml.FullLoader).items()
            for owner, credential in accounts.items()
            if credential['enabled']
        ]
    )


def check_unique(creds: List[NTCredential]):
    unique_creds = set()
    for c in creds:
        unique_creds.add(
            (c.exchange_name, c.api_key, c.api_secret)
        )
    diff = len(creds) - len(unique_creds)
    if diff:
        raise NonUniqueCredentials('Found %d non unique credentials, please check!', diff)

    return creds
