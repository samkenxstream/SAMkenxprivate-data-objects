# Copyright 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
utility.py -- common utility routines

NOTE: functions defined in this file are designed to be run
before logging is enabled.
"""

import os
import errno
import pdo.common.crypto as crypto

import logging
logger = logging.getLogger(__name__)

__all__ = [
    'build_simple_file_name',
    'build_file_name',
    'find_file_in_path',
    'from_transaction_signature_to_id',
    'valid_service_url',
    'normalize_service_url',
    'are_the_urls_same'
    ]

__default_data_directory__ = None

# -----------------------------------------------------------------
# -----------------------------------------------------------------
import inspect
import functools

def deprecated(func):
    """decorator to mark functions as deprecated, logs a warning
    with information about the function and the caller
    """
    @functools.wraps(func)
    def new_func(*args, **kwargs):
        stack = inspect.stack()
        logger.warn('invocation of deprecated function %s by %s in file %s', func.__name__, stack[1][3], stack[1][1])
        return func(*args, **kwargs)

    return new_func

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def build_simple_file_name(basename, extension='') :
    """build a file name from the basename and extension; this is a
    common operation for scripts that process a configuration file

    :param str basename: base name of a file, may be a full path, may have an extension
    :param str extension: the extension to add to the file if it doesnt have one
    """

    if basename[-len(extension):] != extension :
        basename += extension

    if os.path.split(basename)[0] :
        return os.path.realpath(basename)

    return basename

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def build_file_name(basename, data_dir = None, data_sub = None, extension = '') :
    """build a file name from the basename and directory; this is a
    common operation for scripts that process a configuration file

    :param str basename: base name of a file, may be a full path, may have an extension
    :param str data_dir: directory where the file will be placed
    :param str data_sub: subdirectory where the files of this type are stored
    :param str extension: the extension to add to the file if it doesnt have one
    """

    global __default_data_directory__
    if data_dir is None :
        if __default_data_directory__ is None :
            import pdo.common.config as pconfig
            __default_data_directory__ = pconfig.shared_configuration(['Contract', 'DataDirectory'],"./data")

        data_dir = __default_data_directory__

    if data_sub is not None :
        data_dir = os.path.join(data_dir, data_sub)

    # os.path.abspath only works for full paths, not relative paths
    # this check should catch './abc'
    if os.path.split(basename)[0] :
        return os.path.realpath(basename)
    if basename[-len(extension):] == extension :
        return os.path.join(data_dir, basename)
    else :
        return os.path.join(data_dir, basename + extension)

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def find_file_in_path(filename, search_path) :
    """general utility to search for a file name in a path

    :param str filename: name of the file to locate, absolute path ignores search_path
    :param list(str) search_path: list of directores where the files may be located
    """

    # os.path.abspath only works for full paths, not relative paths
    # this check should catch './abc'
    if os.path.split(filename)[0] :
        if os.path.isfile(filename) :
            return filename
        raise FileNotFoundError(errno.ENOENT, "file does not exist", filename)

    for path in search_path :
        full_filename = os.path.join(path, filename)
        if os.path.isfile(full_filename) :
            return full_filename

    raise FileNotFoundError(errno.ENOENT, "unable to locate file in search path", filename)

# -----------------------------------------------------------------
# -----------------------------------------------------------------
def from_transaction_signature_to_id(transaction_signature) :
    """function to transform a hex transaction signature (or transaction identifier)
    into a base64 id which is used (for instance) for a contract id
    """
    id = crypto.byte_array_to_base64(crypto.compute_message_hash(crypto.hex_to_byte_array(transaction_signature)))
    return id

#--------------------------------------------------------------------
#--------------------------------------------------------------------
import socket
from urllib.parse import urlparse

def valid_service_url(url) :
    """Predicate to determine if the string argument
    is a valid URL
    """
    try :
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except :
        return False

def normalize_service_url(url) :
    """Normalize a service URL for consistency, normalized URL
    is based on the host ip address
    """
    parsed = urlparse(url)
    (hostname, hostport) = parsed.netloc.split(':')
    hostip = socket.gethostbyname(hostname)
    return "{}://{}:{}".format(parsed.scheme, hostip, hostport)

def are_the_urls_same(url1, url2):
    """Though not a perfect comparison, we make make sure that
    http://127.0.0.1:7101/ and http://localhost:7101 are considered the same.
    It would be good to first check  if the input is a valid url itself."""

    if url1 is None or url2 is None:
        return False

    if (url1 == url2):
        return True

    return normalize_service_url(url1) == normalize_service_url(url2)
