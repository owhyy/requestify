import re
from urllib import parse
from . import utils

JSON_ERROR_NAME = 'JSONDecodeError'

# name that will be used for class with requests
REQUEST_CLASS_NAME = 'RequestsTest'
REQUEST_MATCHING_DATA_DICT_NAME = 'workflow'
REQUEST_VARIABLE_NAME = 'request'
RESPONSE_VARIABLE_NAME = 'response'

# methods to be called if data flags are present
DATA_HANDLER = {
    '-d': lambda x: utils.get_data_dict(x),
    '--data': lambda x: utils.get_data_dict(x),
    '--data-ascii': lambda x: utils.get_data_dict(x),
    '--data-binary': lambda x: bytes(x, encoding='utf-8'),
    '--data-raw': lambda x: utils.get_data_dict(x),
    '--data-urlencode': lambda x: parse.quote(x),
}

METHOD_REGEX = re.compile(
    f'({"|".join(name for name in DATA_HANDLER)})|(?:-X)\s+(\S\w+\S)'
)
OPTS_REGEX = re.compile(
    """ (-{1,2}\S+)\s+?"([\S\s]+?)"|(-{1,2}\S+)\s+?'([\S\s]+?)'""", re.VERBOSE
)
URL_REGEX = re.compile(
    '((?:(?<=[^a-zA-Z0-9]){0,}(?:(?:https?\:\/\/){0,1}(?:[a-zA-Z0-9\%]{1,}\:[a-zA-Z0-9\%]{1,}[@]){,1})(?:(?:\w{1,}\.{1}){1,5}(?:(?:[a-zA-Z]){1,})|(?:[a-zA-Z]{1,}\/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\:[0-9]{1,4}){1})){1}(?:(?:(?:\/{0,1}(?:[a-zA-Z0-9\-\_\=\-]){1,})*)(?:[?][a-zA-Z0-9\=\%\&\_\-]{1,}){0,1})(?:\.(?:[a-zA-Z0-9]){0,}){0,1})'
)
