from typing import Dict

import aiohttp


class HuobiException(Exception):
    pass


class HuobiResponseException(HuobiException):
    pass


class HuobiAuthenticationRequired(HuobiException):
    pass


class HuobiAPIException(HuobiException):
    def __init__(self, response: aiohttp.ClientResponse, response_json: Dict):
        self.api_code = response_json.get('err-code', 'Unknown code.')
        self.api_message = response_json.get('err-msg', 'Unknown message.')
        self.http_code = response.status

        self.response = response
        self.request_info = response.request_info

    def __str__(self):  # pragma: no cover
        return f'APIError(http_code={self.http_code}, api_code={self.api_code}): {self.api_message}'
