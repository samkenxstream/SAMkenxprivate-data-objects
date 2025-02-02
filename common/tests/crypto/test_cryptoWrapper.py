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

import pdo.common.crypto as crypto
import logging
import sys
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARN)
logger = logging.getLogger()
logging.basicConfig(level=logging.WARN)

# ECDSA tests on default curve (if undefined) or defined curve
def test_ecdsa(sig_curve=crypto.SigCurve_UNDEFINED):
    try:
     if(sig_curve == crypto.SigCurve_UNDEFINED):
        # test with private key from default constructor
        esk = crypto.SIG_PrivateKey()
     elif(sig_curve == crypto.SigCurve_SECP256K1 or sig_curve == crypto.SigCurve_SECP384R1):
        # test with private key from curve-defined constructor
        esk = crypto.SIG_PrivateKey(sig_curve)
     else:
        logger.error("ERROR: unsupported sigcurve " + crypto.sig_curve)
        sys.exit(-1)

     # test private key generation
     esk.Generate()

     # test public key retrieval from public key
     epk = esk.GetPublicKey()
    except Exception as exc:
     logger.error("ERROR: Signature Private and Public keys generation test failed: ", exc)
     sys.exit(-1)
    logger.debug("Signature Private and Public keys generation test successful!")

    try:
     # test private key serialization
     eskString = esk.Serialize()
     # test public key serialization
     epkString = epk.Serialize()
     # test public key xy serialization
     hepkString = epk.SerializeXYToHex()
     # test private key PEM constructor
     esk1 = crypto.SIG_PrivateKey(eskString)
     # test public key PEM constructor
     epk1 = crypto.SIG_PublicKey(epkString)
     # test private key serialization
     eskString1 = esk1.Serialize()
     # test public key serialization
     epkString1 = epk1.Serialize()
     # generate key pair for tests
     esk2 = crypto.SIG_PrivateKey()
     esk2.Generate()
     epk2 = crypto.SIG_PublicKey(esk2)
     # test private key deserialization
     esk2.Deserialize(eskString1)
     # test public key deserialization
     epk2.Deserialize(epkString1)
     # test PEM equivalence following deserialization-serialization steps
     eskString2 = esk2.Serialize()
     epkString2 = epk2.Serialize()
     if eskString1 != eskString2 or epkString1 != epkString2:
        logger.error("ERROR: PEM differ after deserialization-serialization steps")
        sys.exit(-1)
    except Exception as exc:
     logger.error("ERROR: Signature Private and Public keys serialize/deserialize test failed: ", exc)
     sys.exit(-1)
    logger.debug("Signature Private and Public keys serialize/deserialize test successful!")

    try:
     # test deserializing public key as private key
     esk1.Deserialize(epkString1)
     logger.error("ERROR: Signature invalid private key deserialize test failed: not detected.")
     sys.exit(-1)
    except Exception as exc:
      if (type(exc) == ValueError):
       logger.debug("Signature invalid private key deserialize test successful!")
      else:
       logger.error("ERROR: Signature invalid private key deserialize test failed: ", exc)
       sys.exit(-1)

    try:
     # test deserializing private key as public key
     epk1.Deserialize(eskString1)
     logger.error("ERROR: Signature invalid public key deserialize test failed: not detected.")
     sys.exit(-1)
    except Exception as exc:
      if (type(exc) == ValueError):
       logger.debug("Signature invalid public key deserialize test successful!")
      else:
       logger.error("ERROR: Signature invalid public key deserialize test failed: ", exc)
       sys.exit(-1)

    try:
     # test message signing and verification
     msg = b'A message!'
     sig = esk.SignMessage(msg)
     res = epk.VerifySignature(msg, sig)
    except Exception as exc:
     logger.error("ERROR: Signature creation and verification test failed: ", exc)
     sys.exit(-1)
    if (res == 1):
        logger.debug("Signature creation and verification test successful!")
    else:
        logger.error("ERROR: Signature creation and verification test failed: signature does not verify.")
        exit(-1)

    try:
     # test invalid signature verification
     res = epk.VerifySignature(msg, bytes("invalid signature", 'ascii'))
    except Exception as exc:
     logger.error("ERROR: Invalid signature detection test failed: ", exc)
     sys.exit(-1)
    if (res != 1):
        logger.debug("Invalid signature detection test successful!")
    else:
        logger.error("ERROR: Invalid signature detection test failed.")
        exit(-1)

# TEST ECDSA default (secp256k1)
test_ecdsa()
# TEST ECDSA secp256k1
test_ecdsa(crypto.SigCurve_SECP256K1)
# TEST ECDSA secp384r1
test_ecdsa(crypto.SigCurve_SECP384R1)

# TEST RSA
msg = b'A message!'
try:
 rsk = crypto.PKENC_PrivateKey()
 rsk.Generate()
 rpk = crypto.PKENC_PublicKey(rsk)
except Exception as exc:
 logger.error("ERROR: Asymmetric encryption Private and Public keys generation test failed: ", exc)
 sys.exit(-1)
logger.debug("Asymmetric encryption Private and Public keys generation test successful!")
try:
 rskString = rsk.Serialize()
 rpkString = rpk.Serialize()
 rsk1 = crypto.PKENC_PrivateKey(rskString)
 rpk1 = crypto.PKENC_PublicKey(rpkString)
 rskString1 = rsk1.Serialize()
 rpkString1 = rpk1.Serialize()
 rsk2 = crypto.PKENC_PrivateKey()
 rsk2.Generate();
 rpk2 = crypto.PKENC_PublicKey(rsk2)
 rsk2.Deserialize(rskString1)
 rpk2.Deserialize(rpkString1)
 rskString2 = rsk2.Serialize()
 rpkString2 = rpk2.Serialize()
except Exception as exc:
 logger.error("ERROR: Asymmetric encryption Private and Public keys serialize/deserialize test failed: ", exc)
 sys.exit(-1)

try:
 rsk1.Deserialize(rpkString1)
 logger.error("error: Asymmetric encryption invalid private key deserialize test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Asymmetric encryption invalid private key deserialize test successful!")
  else:
   logger.error("error: Asymmetric encryption invalid private key deserialize test failed: ", exc)
   sys.exit(-1)

try:
 rpk1.Deserialize(rskString1)
 logger.error("error: Asymmetric encryption invalid public key deserialize test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Asymmetric encryption invalid public key deserialize test successful!")
  else:
   logger.error("error: Asymmetric encryption invalid public key deserialize test failed: ", exc)
   sys.exit(-1)


try:
 ciphertext = rpk.EncryptMessage(msg)
 plaintext = rsk.DecryptMessage(ciphertext)
except Exception as exc:
 logger.error("ERROR: Asymmetric encryption/decryption test failed: ", exc)
 sys.exit(-1)

if (bytearray(plaintext) == bytearray(msg)):
  logger.debug("Asymmetric encryption/decryption test successful!")
else:
  logger.error("ERROR: Asymmetric encryption/decryption failed.\n")
  exit(-1)

#TEST AES-GCM
try:
 iv = crypto.SKENC_GenerateIV()
except Exception as exc:
 logger.error("ERROR: Symmetric encryption iv generation test failed: ", exc)
 sys.exit(-1)
try:
 key = crypto.SKENC_GenerateKey()
except Exception as exc:
 logger.error("ERROR: Symmetric encryption key generation test failed: ", exc)
 sys.exit(-1)

try:
 crypto.SKENC_EncryptMessage(iv, None, msg)
 logger.error("ERROR: Symmetric encryption invalid key detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric encryption invalid key detection test successful!")
  else:
   logger.error("ERROR: Symmetric encryption invalid key detection test failed: ", exc)
   sys.exit(-1)
try:
 crypto.SKENC_EncryptMessage(None, key, msg)
 logger.error("ERROR: Symmetric encryption invalid iv detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric encryption invalid iv detection test successful!")
  else:
   logger.error("ERROR: Symmetric encryption invalid iv detection test failed: ", exc)
   sys.exit(-1)

try:
 ciphertext = crypto.SKENC_EncryptMessage(key, iv, msg)
 crypto.SKENC_DecryptMessage(key, iv, ciphertext)
except Exception as exc:
 logger.error("ERROR: Symmetric encryption test failed: ", exc)
 sys.exit(-1)

if (bytearray(plaintext) == bytearray(msg)):
  logger.debug("Symmetric encryption/decryption test successful!\n")
else:
  logger.errpr("ERROR:Symmetric encryption/decryption test failed: decrypted text and plaintext mismatch.\n")
  exit(-1)

c = list(ciphertext)
c[0] = (c[0] + 1) % 256 # Make sure it stays a byte or swig might fail find the correct C++ function below
ciphertext = tuple(c)
try:
 crypto.SKENC_DecryptMessage(key, iv, ciphertext)
 logger.error("ERROR: Symmetric decryption ciphertext tampering detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric decryption ciphertext tampering detection test successful!")
  else:
   logger.error("ERROR: Symmetric decryption ciphertext tampering detection test failed: ", exc)
   sys.exit(-1)
try:
 crypto.SKENC_DecryptMessage(iv, iv, ciphertext)
 logger.error("ERROR: Symmetric decryption invalid key detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric decryption invalid key detection test successful!")
  else:
   logger.error("ERROR: Symmetric decryption invalid key detection test failed: ", exc)
   sys.exit(-1)
try:
 crypto.SKENC_DecryptMessage(plaintext, key, ciphertext)
 logger.error("ERROR: Symmetric decryption invalid iv detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric decryption invalid iv detection test successful!")
  else:
   logger.error("ERROR: Symmetric decryption invalid iv detection test failed: ", exc)
   sys.exit(-1)
try:
 crypto.SKENC_EncryptMessage(None, ciphertext)
 logger.error("ERROR: Symmetric encryption invalid key detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric encryption invalid key detection test successful!")
  else:
   logger.error("ERROR: Symmetric encryption invalid key detection test failed: ", exc)
   sys.exit(-1)
try:
 crypto.SKENC_EncryptMessage(None, key, ciphertext)
 logger.error("ERROR: Symmetric encryption invalid iv detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric encryption invalid iv detection test successful!")
  else:
   logger.error("ERROR: Symmetric encryption invalid iv detection test failed: ", exc)
   sys.exit(-1)

#Random IV
try:
 ciphertext = crypto.SKENC_EncryptMessage(key, msg)
 crypto.SKENC_DecryptMessage(key, ciphertext)
except Exception as exc:
 logger.error("ERROR: Symmetric encryption (random IV) test failed: ", exc)
 sys.exit(-1)

if (bytearray(plaintext) == bytearray(msg)):
  logger.debug("Symmetric encryption (random IV)/decryption test successful!\n")
else:
  logger.errpr("ERROR:Symmetric encryption (random IV)/decryption test failed: decrypted text and plaintext mismatch.\n")
  exit(-1)

c = list(ciphertext)
c[0] = (c[0] + 1) % 256 # Make sure it stays a byte or swig might fail find the correct C++ function below
ciphertext = tuple(c)
try:
 crypto.SKENC_DecryptMessage(key, ciphertext)
 logger.error("ERROR: Symmetric decryption (random IV) ciphertext tampering detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric decryption (random IV) ciphertext tampering detection test successful!")
  else:
   logger.error("ERROR: Symmetric decryption (random IV) ciphertext tampering detection test failed: ", exc)
   sys.exit(-1)
try:
 crypto.SKENC_DecryptMessage(iv, ciphertext)
 logger.error("ERROR: Symmetric decryption (random IV) invalid key detection test failed: not detected.")
 sys.exit(-1)
except Exception as exc:
  if (type(exc) == ValueError):
   logger.debug("Symmetric decryption (random IV) invalid key detection test successful!")
  else:
   logger.error("ERROR: Symmetric decryption (random IV) invalid key detection test failed: ", exc)
   sys.exit(-1)
try:
 iv = crypto.SKENC_GenerateIV("A message")
except Exception as exc:
 logger.error("ERROR: Symmetric encryption deterministic iv generation test failed: ", exc)
 sys.exit(-1)
logger.debug("Symmetric encryption deterministic iv generation test successful!")
try:
 rand = crypto.random_bit_string(16)
except Exception as exc:
 logger.error("ERROR: Random number generation failed: ", exc)
 sys.exit(-1)
logger.debug("Random number generation successful!")

hash = crypto.compute_message_hash(rand)
bhash = bytearray(hash)
b64hash = crypto.byte_array_to_base64(bhash)
logger.debug("Hash computed!")
crypto.base64_to_byte_array(b64hash)
logger.debug("SWIG CRYPTO_WRAPPER TEST SUCCESSFUL!")
sys.exit(0)
