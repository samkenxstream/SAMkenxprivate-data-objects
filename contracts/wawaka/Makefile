# Copyright 2019 Intel Corporation
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

ifndef PDO_INSTALL_ROOT
$(error Incomplete configuration, PDO_INSTALL_ROOT is not defined)
endif

ifndef PDO_HOME
$(error Incomplete configuration, PDO_HOME is not defined)
endif

ifndef PDO_SOURCE_ROOT
$(error Incomplete configuration, PDO_SOURCE_ROOT is not defined)
endif

SCRIPTDIR ?= $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
DSTDIR ?= $(PDO_INSTALL_ROOT)

WAMR_ROOT=$(PDO_SOURCE_ROOT)/interpreters/wasm-micro-runtime
WAMR_TOOLCHAIN=$(WAMR_ROOT)/wamr-sdk/app/wasi_toolchain.cmake

PLUGIN_INSTALL_DIR ?= $(PDO_HOME)/contracts/plugins
PLUGIN_SOURCE=$(wildcard $(SCRIPTDIR)/*/plugins/*.py)

SCRIPT_INSTALL_DIR ?= $(PDO_HOME)/bin
SCRIPT_SOURCE=$(wildcard $(SCRIPTDIR)/*/scripts/*.psh)

DATA_DIR ?= $(PDO_HOME)/data

TEST_LOG_LEVEL ?= warn
TEST_LOG_FILE ?= __screen__

## This would point you to the WAMR version of the built in libraries
## WAMR_TOOLCHAIN=$(WAMR_ROOT)/wamr-sdk/app/wamr_toolchain.cmake

all : build
	@cd build && make all

clean :
	@echo Remove build directory
	@rm -rf build

debug :
	@echo No debug build defined

# this is the unit test target, these tests can run without eservice running
test : install interface-test interpreter-test memory-test mock-contract-test

# this is the system test target, these tests require an eservice
system-test : install attestation-test kv-test

interface-test:
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && pdo-test-contract --no-ledger \
		--loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE) \
		--contract $@ \
		--expressions ${SCRIPTDIR}/$@/test-short.json

interpreter-test:
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && pdo-test-contract --no-ledger \
		--loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE) \
		--contract $@ \
		--expressions ${SCRIPTDIR}/$@/test-short.json

memory-test:
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && pdo-test-contract --no-ledger \
		--loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE) \
		--contract $@ \
		--expressions ${SCRIPTDIR}/$@/test-short.json

mock-contract-test :
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && pdo-test-contract --no-ledger \
		--loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE) \
		--contract mock-contract \
		--expressions ${SCRIPTDIR}/mock-contract/test-short.json

attestation-test:
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && \
		cd attestation-test && \
		scripts/attestation-test.psh --loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE) \
			-m test_data $(SCRIPTDIR)/attestation-test/scripts

interp-test: interpreter-test/scripts/interpreter-test.psh
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && \
		cd interpreter-test && \
		scripts/interpreter-test.psh --loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE)

interf-test: interface-test/scripts/interface-test.psh
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && \
		cd interface-test && \
		scripts/interface-test.psh --loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE)

kv-test: kv-test/plugins/kv-test.py kv-test/scripts/kv-test.psh
	@echo run test: $@
	@ . $(abspath $(DSTDIR)/bin/activate) && \
		cd kv-test && \
		scripts/kv-test.psh --loglevel $(TEST_LOG_LEVEL) --logfile $(TEST_LOG_FILE)

install : build $(PLUGIN_SOURCE) $(SCRIPT_SOURCE)
	@echo install contracts
	@cd build && make install
	@mkdir -p $(PLUGIN_INSTALL_DIR); cp $(PLUGIN_SOURCE) $(PLUGIN_INSTALL_DIR)
	@mkdir -p $(SCRIPT_INSTALL_DIR); cp $(SCRIPT_SOURCE) $(SCRIPT_INSTALL_DIR)

build :
	mkdir -p $@
	cd $@ && cmake .. -DCMAKE_TOOLCHAIN_FILE=$(WAMR_TOOLCHAIN)

.PHONY: test interface-test mock-contract-test interpreter-test memory-test
.PHONY: system-test eservice-db attestation-test kv-test
.PHONY : all clean debug install test

# Note: build is NOT a phony in this case; we make the directory and
# then build the makefile using cmake. This only needs to be re-done
# if build goes away.
