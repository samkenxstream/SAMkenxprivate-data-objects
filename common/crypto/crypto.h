/* Copyright 2018 Intel Corporation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#pragma once
#if _CLIENT_ONLY_
#else
#include "sgx_defaults.h"
#endif
#include <openssl/sha.h>
#include "crypto_shared.h"
#include "crypto_utils.h"
#include "pkenc.h"
#include "pkenc_private_key.h"
#include "pkenc_public_key.h"
#include "hash.h"
#include "sig.h"
#include "sig_private_key.h"
#include "sig_public_key.h"
#include "skenc.h"
#if _CLIENT_ONLY_
#else
#include "verify_ias_report/ias-certificates.h"
#include "verify_ias_report/verify-report.h"
#endif
