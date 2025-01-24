# Copyright 2017 Intel Corporation
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
# ------------------------------------------------------------------------------

DOCKER_BUILD_OPTS=
DOCKER_COMPOSE_COMMAND=docker-compose
DOCKER_COMPOSE_FILES=
DOCKER_COMPOSE_OPTS=

# optionally allow local overriding defaults
-include make.loc

DOCKER_COMPOSE_FILES += ccf-pdo.yaml ccf-pdo.local-code.yaml
DOCKER_COMPOSE_FILES_CCF_ONLY += ccf.yaml ccf.local-code.yaml

ifeq ($(SGX_MODE),HW)
   DOCKER_COMPOSE_FILES += pdo.sgx.yaml
   DOCKER_COMPOSE_FILES_CCF_ONLY += pdo.sgx.yaml
   SGX_DEVICE_PATH=$(shell if [ -e "/dev/isgx" ]; then echo "/dev/isgx"; elif [ -e "/dev/sgx/enclave" ]; then echo "/dev/sgx/enclave"; else echo "ERROR: NO SGX DEVICE FOUND"; fi)
   DOCKER_COMPOSE_COMMAND := env SGX_DEVICE_PATH=${SGX_DEVICE_PATH} ${DOCKER_COMPOSE_COMMAND}
endif
ifdef http_proxy
   DO_PROXY = 1
endif
ifdef https_proxy
   DO_PROXY = 1
endif
ifdef ftp_proxy
   DO_PROXY = 1
endif
ifdef no_proxy
   DO_PROXY = 1
endif
ifdef DO_PROXY
   DOCKER_COMPOSE_FILES += ccf-pdo.proxy.yaml
   DOCKER_COMPOSE_FILES_CCF_ONLY += ccf.proxy.yaml
endif

DOCKER_COMPOSE_OPTS += $(foreach cf, $(DOCKER_COMPOSE_FILES), -f $(cf))
DOCKER_COMPOSE_OPTS_CCF_ONLY += $(foreach cf, $(DOCKER_COMPOSE_FILES_CCF_ONLY), -f $(cf))

all:

pdo-dev-image:
	# unconditionally build, count on docker caching to not rebuild if not necessary
	@echo "Building pdo-dev docker image"
	docker build $(DOCKER_BUILD_OPTS) -f Dockerfile.pdo-dev -t pdo-dev .

pdo-composition: pdo-dev-image
	@echo "Running PDO docker composition for CCF"
	env PDO_REPO_BRANCH=$$(git rev-parse --abbrev-ref HEAD) $(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS) build
	# Note:
	# - using `ccf-pdo.local-code.yaml` in above will cause the docker context to be `../`.
	#   To make sure that we do not pull in (too much) unnecessary stuff, we explicitly excludes
	#   various files/dirs in `../.dockerignore`.
	#   There are two negative effect for not excluding enough
	#   - if some non-essential file changed (e.g., build artificats on host which are
	#     all not needed in docker), docker caching might not work well and docker will rebuild
	#     layers even though it could have cached (and hence run faster).
	#   - the the build-time layer will become unecessarily big (note: as we do multi-stage, the size of
	#     of the built container image should not be affected). This is in particular an issue with lmdb
	#     files which are created by tests in default location ../build/_dev. These files are
	#     sparse but docker expands to them to their nominal size (several gb) and could cause
	#     running out of disk space during the build...

ccf-only:
	env PDO_REPO_BRANCH=$$(git rev-parse --abbrev-ref HEAD) $(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS_CCF_ONLY) build

test: pdo-composition test-with-no-build

test-env-setup: pdo-composition test-env-setup-with-no-build
test-env-setup-ccf-only: ccf-only test-env-setup-with-no-build-ccf-only

test-env-setup-with-no-build-ccf-only:
	# just to be on safe side, make sure environment is not still up (e.g.,from previous failed attempt)
	-$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS_CCF_ONLY) down
	# - start services
	$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS_CCF_ONLY) up -d

test-env-setup-with-no-build:
	@echo "Bringing up environment for tests with CCF"
	# just to be on safe side, make sure environment is not still up (e.g.,from previous failed attempt)
	-$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS) down
	# - start services
	$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS) up -d
	# Before registration, it must be ensured that CCF is up and configured.
	# Otherwise, the registration can encounter two possible scenarios:
	# 1) CCF is not up, so the registration times out
	# 2) CCF is up but not configured, so the registration fails with "not a known member"
	# A wait of a few seconds appears to be enough.
	@echo "Waiting a few seconds for CCF to be up and configured..."
	sleep 20
	$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS) \
		exec -T pdo-build bash -c 'source /etc/bash.bashrc && export PDO_SGX_KEY_ROOT=/project/pdo/build/opt/pdo/etc/keys/sgx/ && unset PDO_SPID PDO_SPID_API_KEY PDO_HOSTNAME && source /project/pdo/src/private-data-objects/build/common-config.sh && /project/pdo/build/opt/pdo/etc/keys/ledger/check-for-ccf-keys.sh && make -C /project/pdo/src/private-data-objects/build force-config register'

test-with-no-build: test-env-setup-with-no-build
	# - run automated tests
	@echo "Running PDO tests with CCF"
	# the pdo container must add the ip address of the pdo-tp-ccf container to its no proxy list (if behind a proxy)
	if [ ! -z "$(no_proxy)" ]; then \
	   $(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS)  exec -T pdo-build bash -i -c "source /set_no_proxy.sh && /project/pdo/build/opt/pdo/etc/keys/ledger/check-for-ccf-keys.sh && unset PDO_HOSTNAME && source /project/pdo/src/private-data-objects/build/common-config.sh && /project/pdo/src/private-data-objects/build/__tools__/run-tests.sh"; \
	else \
	   $(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS)  exec -T pdo-build bash -i -c "/project/pdo/build/opt/pdo/etc/keys/ledger/check-for-ccf-keys.sh && unset PDO_HOSTNAME && source /project/pdo/src/private-data-objects/build/common-config.sh && /project/pdo/src/private-data-objects/build/__tools__/run-tests.sh"; \
	fi

	# remove ccf keys from local folder
	rm ccf_keys/networkcert.pem

	# - teardown
	$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS) down

# target to run docker-compose with same files on arbitrary docker-compose command passed as ARGS...
# to pass multiple arguments, you will have to pass it as env-variablse, e.g., "env ARGS='arg1 arg2 arg3' make run"
run-ccf:
	$(DOCKER_COMPOSE_COMMAND) $(DOCKER_COMPOSE_OPTS) $(ARGS)
