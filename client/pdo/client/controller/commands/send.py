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

import argparse
import ast
import random
import sys

import logging
logger = logging.getLogger(__name__)

import pdo.common.crypto as crypto
from pdo.common.keys import ServiceKeys
from pdo.common.utility import valid_service_url
from pdo.service_client.enclave import EnclaveServiceClient

from pdo.client.controller.commands.contract import get_contract
from pdo.client.controller.commands.eservice import get_eservice
import pdo.service_client.service_data.eservice as eservice_db
from pdo.client.controller.util import invocation_parameter
from pdo.contract import invocation_request

from pdo.submitter.create import create_submitter

__all__ = ['command_send', 'send_to_contract']

## -----------------------------------------------------------------
## -----------------------------------------------------------------
def send_to_contract(state, message, save_file, eservice_url=None, wait=False, commit=True) :

    # ---------- load the invoker's keys ----------
    try :
        keyfile = state.private_key_file
        keypath = state.get(['Key', 'SearchPath'])
        client_keys = ServiceKeys.read_from_file(keyfile, keypath)
    except Exception as e :
        raise Exception('unable to load client keys; {0}'.format(str(e)))

    # ---------- read the contract ----------
    try :
        contract = get_contract(state, save_file)
    except Exception as e :
        raise Exception('unable to load the contract')

    # ---------- set up the enclave service ----------
    if eservice_url is None :
        eservice_url = 'preferred'

    if valid_service_url(eservice_url) :
        try :
            eservice_client = EnclaveServiceClient(eservice_url)
        except Exception as e :
            raise Exception('unable to connect to enclave service; {0}'.format(str(e)))

        if eservice_client.enclave_id not in contract.provisioned_enclaves :
            raise Exception('requested enclave not provisioned for the contract; %s', eservice_url)
    else :
        if eservice_url == 'preferred' :
            enclave_id = contract.extra_data.get('preferred-enclave', random.choice(contract.provisioned_enclaves))
            eservice_info = eservice_db.get_by_enclave_id(enclave_id)
        elif eservice_url == 'random' :
            enclave_id = random.choice(contract.provisioned_enclaves)
            eservice_info = eservice_db.get_by_enclave_id(enclave_id)
        else :
            eservice_info = eservice_db.get_by_name(eservice_url)

        if eservice_info is None :
            raise Exception('attempt to use an unknown enclave; %s', enclave_id)

        try :
            eservice_client = EnclaveServiceClient(eservice_info.url)
        except Exception as e :
            raise Exception('unable to connect to enclave service; {0}'.format(str(e)))

    # ---------- send the message to the enclave service ----------
    try :
        update_request = contract.create_update_request(client_keys, message, eservice_client)
        update_response = update_request.evaluate()
    except Exception as e:
        raise Exception('enclave failed to evaluate expression; {0}'.format(str(e)))

    if not update_response.status :
        raise ValueError(update_response.invocation_response)

    data_directory = state.get(['Contract', 'DataDirectory'])
    ledger_config = state.get(['Ledger'])

    if update_response.state_changed and commit :

        contract.set_state(update_response.raw_state)

        # asynchronously submit the commit task: (a commit task replicates
        # change-set and submits the corresponding transaction)
        try:
            update_response.commit_asynchronously(ledger_config)
        except Exception as e:
            raise Exception('failed to submit commit: %s', str(e))

        # wait for the commit to finish.
        # TDB:
        # 1. make wait_for_commit a separate shell command.
        # 2. Add a provision to specify commit dependencies as input to send command.
        # 3. Return commit_id after send command back to shell so as to use as input
        #    commit_dependency in a future send command
        try:
            txn_id = update_response.wait_for_commit()
            if txn_id is None:
                raise Exception("Did not receive txn id for the send operation")
        except Exception as e:
            raise Exception("Error while waiting for commit: %s", str(e))

        if wait :
            try :
                # we are trusting the submitter to handle polling of the ledger
                # and we dont care what the result is... if there is a result then
                # the state has been successfully committed
                submitter = create_submitter(ledger_config)
                encoded_state_hash = crypto.byte_array_to_base64(update_response.new_state_hash)
                _ = submitter.get_state_details(update_response.contract_id, encoded_state_hash)
            except Exception as e:
                raise Exception("Error while waiting for global commit: %s", str(e))

    return update_response.invocation_response

## -----------------------------------------------------------------
## -----------------------------------------------------------------
def command_send(state, bindings, pargs) :
    """controller command to send a message to a contract
    """

    parser = argparse.ArgumentParser(prog='send')
    parser.add_argument('-e', '--enclave', help='URL of the enclave service to use', type=str)
    parser.add_argument('-f', '--save-file', help='File where contract data is stored', type=str)
    parser.add_argument('-p', '--positional', help='JSON encoded list of positional parameters', type=invocation_parameter)
    parser.add_argument('-s', '--symbol', help='Save the result in a symbol for later use', type=str)
    parser.add_argument('--wait', help='Wait for the transaction to commit', action = 'store_true')

    parser.add_argument('-k', '--kwarg',
                        help='add a keyword argument to the invocation',
                        nargs=2, type=invocation_parameter, action='append')

    parser.add_argument('method',
                        help='message to be sent to the contract',
                        type=str)

    parser.add_argument('positional_params',
                        help='positional parameters sent to the invocation',
                        type=invocation_parameter, nargs='*')

    options = parser.parse_args(pargs)
    waitflag = options.wait

    method = options.method

    pparams = []
    if options.positional :
        assert type(options.positional) is list
        pparams.extend(options.positional)

    if options.positional_params :
        pparams.extend(options.positional_params)

    kparams = dict()
    if options.kwarg :
        for (k, v) in options.kwarg :
            if type(k) is not str :
                raise RuntimeError('expecting string key; {0}'.format(str(k)))
            kparams[k] = v

    message = invocation_request(method, *pparams, **kparams)

    result = send_to_contract(
        state,
        message,
        options.save_file,
        eservice_url=options.enclave,
        wait=options.wait)
    if options.symbol :
        bindings.bind(options.symbol, result)
