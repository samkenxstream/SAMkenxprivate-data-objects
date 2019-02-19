/* Copyright 2019 Intel Corporation
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

#include "state.h"

#if _UNTRUSTED_
#define THROW_EXCEPTION_ON_STACK_FULL(p)
#else
extern "C" {
bool is_stack_addr(void* p, size_t size);
}

#define FAILURE_STACK_ZONE_BYTES 0x3000

#define THROW_EXCEPTION_ON_STACK_FULL(p)                               \
    {                                                                  \
        if (!is_stack_addr((uint8_t*)p - FAILURE_STACK_ZONE_BYTES, 1)) \
        {                                                              \
            throw pdo::error::RuntimeError("stack full");              \
        }                                                              \
    }
#endif

namespace pstate = pdo::state;

unsigned int pstate::trie_node::shared_prefix_length(
    const uint8_t* stored_chunk, size_t sc_length, const uint8_t* key_chunk, size_t kc_length)
{
    unsigned int spl = 0;
    while (spl < sc_length && spl < kc_length && stored_chunk[spl] == key_chunk[spl])
    {
        spl++;
    }
    return spl;
}

void pstate::trie_node::delete_trie_node_childless(data_node_io& dn_io,
    trie_node& node)
{
    block_offset bo_child(node.node.child_offset);
    if(bo_child.is_empty())
    {
        //release space of trie node
        dn_io.free_space_collector_.collect(node.location.block_offset_, trie_node::new_trie_node_size());

        // mark node as deleted
        node.node.hdr.isDeleted = 1;
        node.modified = true;

        //TRICK: write immediately the deleted node and update its location to be its next offset;
        //       this allows previous/upper node to correctly update their next/child offset
        write_trie_node(dn_io, node);
        node.location.block_offset_ = node.node.next_offset;
    }
}

void pstate::trie_node::do_operate_trie_child(data_node_io& dn_io,
    trie_node& node,
    const kv_operation_e operation,
    const unsigned int depth,
    const ByteArray& kvkey,
    const ByteArray& in_value,
    ByteArray& value)
{
    trie_node child_node;
    child_node.location.block_offset_ = node.node.child_offset;

    // operate on child node
    operate_trie(dn_io, child_node, operation,
        depth + node.node.hdr.keyChunkSize,  // all key chunk was matched
        kvkey, in_value, value);

    //if child node location has changed, updated it
    if(node.node.child_offset != child_node.location.block_offset_)
    {
        node.node.child_offset = child_node.location.block_offset_;
        node.modified = true;
    }
}

void pstate::trie_node::do_operate_trie_next(data_node_io& dn_io,
    trie_node& node,
    const kv_operation_e operation,
    const unsigned int depth,
    const ByteArray& kvkey,
    const ByteArray& in_value,
    ByteArray& value)
{
    trie_node next_node;
    next_node.location.block_offset_ = node.node.next_offset;

    // operate on next node
    operate_trie(dn_io, next_node, operation,
        depth,  // same depth
        kvkey, in_value, value);

    //if next node location has changed, updated it
    if(node.node.next_offset != next_node.location.block_offset_)
    {
        node.node.next_offset = next_node.location.block_offset_;
        node.modified = true;
    }
}

void pstate::trie_node::do_write_value(data_node_io& dn_io,
    trie_node& node,
    const ByteArray& value)
{
    {
        //if overwriting, delete the current value
        block_offset current_child_bo(node.node.child_offset);
        if (! current_child_bo.is_empty())
        {
            do_delete_value(dn_io, node);
        }
    }

    unsigned int space_required = sizeof(trie_node_header_t) + sizeof(size_t) + value.size();

    //grab the offset where data is going to be written
    if(! dn_io.free_space_collector_.allocate(space_required, node.node.child_offset))
    {
        //search for reusable space failed, so append value
        dn_io.block_offset_for_appending(node.node.child_offset);
    }

    //conservatively mark node as modified -- it would be unmodified only when the freed space is immediately reused
    node.modified = true;

    //initialize the cursor for the write
    block_offset_t bo = node.node.child_offset;

    // write trie node first
    ByteArray ba_trie_node(sizeof(trie_node_header_t), 0);
    trie_node_header_t* h = (trie_node_header_t*)ba_trie_node.data();
    *h = empty_trie_header;
    h->isValue = 1;
    dn_io.write_across_data_nodes(ba_trie_node, 0, bo);
    data_node::advance_block_offset(bo, ba_trie_node.size());
    space_required -= ba_trie_node.size();

    // write buffer size second
    size_t value_size = value.size();
    ByteArray ba_value_size(
        (uint8_t*)&value_size, (uint8_t*)&value_size + sizeof(size_t));
    dn_io.write_across_data_nodes(ba_value_size, 0, bo);
    data_node::advance_block_offset(bo, ba_value_size.size());
    space_required -= ba_value_size.size();

    // write value
    dn_io.write_across_data_nodes(value, 0, bo);
    space_required -= value.size();
    pdo::error::ThrowIf<pdo::error::RuntimeError>(
        space_required != 0, "space estimated does not match space written");
}

void pstate::trie_node::do_read_value_info(data_node_io& dn_io,
        block_offset_t& bo_at, ByteArray& ba_header, size_t& value_size)
{
    //read trie node header
    dn_io.read_across_data_nodes(bo_at, sizeof(trie_node_header_t), ba_header);
    data_node::advance_block_offset(bo_at, sizeof(trie_node_header_t));
    //check header
    trie_node_header_t* h = (trie_node_header_t*)ba_header.data();
    pdo::error::ThrowIf<pdo::error::RuntimeError>(
        !h->isValue, "read value, header read is not for value");

    //read value size
    ByteArray ba_value_size;
    dn_io.read_across_data_nodes(bo_at, sizeof(size_t), ba_value_size);
    data_node::advance_block_offset(bo_at, sizeof(size_t));
    value_size = *((size_t*)ba_value_size.data());
}

void pstate::trie_node::do_read_value(
    data_node_io& dn_io, const trie_node& node, ByteArray& value)
{
    block_offset current_child_bo(node.node.child_offset);
    pdo::error::ThrowIf<pdo::error::RuntimeError>(
        current_child_bo.is_empty(), "read value, value is absent");

    block_offset_t bo = current_child_bo.block_offset_;
    ByteArray ba_header;
    size_t value_size;

    //read value info
    do_read_value_info(dn_io, bo, ba_header, value_size);

    // read value
    unsigned int vs = value_size;
    try
    {
        value.reserve(vs);
    }
    catch (const std::exception& e)
    {
        SAFE_LOG_EXCEPTION("no space for reading value");
        throw;
    }
    dn_io.read_across_data_nodes(bo, vs, value);
}

void pstate::trie_node::do_delete_value(data_node_io& dn_io, trie_node& node)
{
    block_offset_t bo = node.node.child_offset;
    ByteArray ba_header;
    size_t value_size;

    //read value info
    do_read_value_info(dn_io, bo, ba_header, value_size);

    // mark trie node header (1 byte) as deleted
    trie_node_header_t* h = (trie_node_header_t*)(ba_header.data());
    h->isDeleted = 1;

    //overwrite stored header
    dn_io.write_across_data_nodes(ba_header, 0, bo);

    //recover space
    unsigned int freed_bytes = ba_header.size() + sizeof(value_size) + value_size;
    dn_io.free_space_collector_.collect(node.node.child_offset, freed_bytes);

    //delete value from trie
    node.node.child_offset = empty_block_offset;
    node.modified = true;
}

void pstate::trie_node::do_split_trie_node(
    data_node_io& dn_io, trie_node& node, unsigned int spl)
{
    pdo::error::ThrowIf<pdo::error::RuntimeError>(
        !(node.node.hdr.keyChunkSize > 0 && spl < node.node.hdr.keyChunkSize),
        "split node, wrong key chunk size and/or spl");
    dn_io.consume_add_and_init_append_data_node_cond(
        trie_node::new_trie_node_size() > dn_io.append_dn_->free_bytes());

    ByteArray second_chunk(
        node.node.key_chunk + spl, node.node.key_chunk + node.node.hdr.keyChunkSize);

    // make new node with second part of key chunk and same child offset and no next offset
    trie_node second_node;
    create_node(second_chunk, 0, second_chunk.size(), second_node);
    // adjust second node
    second_node.node.next_offset = empty_block_offset;
    second_node.node.child_offset = node.node.child_offset;
    second_node.modified = true;
    // write second node
    write_trie_node(dn_io, second_node);

    // adjust first (i.e., original) header, with original next offset, and new node as child
    node.node.hdr.keyChunkSize = spl;
    node.node.child_offset = second_node.location.block_offset_;
    node.modified = true;
}

size_t pstate::trie_node::new_trie_node_size()
{
    return sizeof(trie_node_h_with_nc_t) + MAX_KEY_CHUNK_BYTE_SIZE;
}

void pstate::trie_node::create_node(const ByteArray& key, unsigned int keyChunkBegin, unsigned int keyChunkEnd, trie_node& out_node)
{
    out_node.node.hdr.hasNext = 1;
    out_node.node.hdr.hasChild = 1;
    out_node.node.next_offset = empty_block_offset;
    out_node.node.child_offset = empty_block_offset;
    // compute key chunk length that can be copied
    size_t kcl = keyChunkEnd - keyChunkBegin;
    // recall that returnHeader->keyChunkSize has limits
    out_node.node.hdr.keyChunkSize = (kcl > MAX_KEY_CHUNK_BYTE_SIZE ? MAX_KEY_CHUNK_BYTE_SIZE : kcl);
    // copy only what can be written, aligned at the beginning of key chunk
    std::copy(key.begin() + keyChunkBegin, key.begin() + keyChunkBegin + out_node.node.hdr.keyChunkSize,
        out_node.node.key_chunk);

    //it is a new node, so mark it as modified to be later written
    out_node.modified = true;

    out_node.initialized = true;
}

void pstate::trie_node::read_trie_node(data_node_io& dn_io, block_offset_t& in_block_offset, trie_node& out_trie_node)
{
    ByteArray ba_node;
    dn_io.read_across_data_nodes(in_block_offset, sizeof(trie_node_h_with_ncc_t), ba_node);
    pdo::error::ThrowIf<pdo::error::RuntimeError>(
        ba_node.size() != sizeof(trie_node_h_with_ncc_t), "unable to read trie node");

    //copy the node in the structure
    out_trie_node.node = *((trie_node_h_with_ncc_t*)ba_node.data());
    out_trie_node.location.block_offset_ = in_block_offset;
    out_trie_node.modified = false;
    out_trie_node.initialized = true;
}

void pstate::trie_node::write_trie_node(data_node_io& dn_io, trie_node& in_trie_node)
{
    // conventions:
    //  1. write to the same location (if available), otherwhise
    //  2. reuse free space (if possible), otherwise
    //  3. append

    if(in_trie_node.location.is_empty())
    {
        if(! dn_io.free_space_collector_.allocate(new_trie_node_size(), in_trie_node.location.block_offset_))
        {
            //search for reusable space failed, so append value
            dn_io.block_offset_for_appending(in_trie_node.location.block_offset_);
        }
    }

    ByteArray ba_node(sizeof(trie_node_h_with_ncc_t), 0);
    *((trie_node_h_with_ncc_t*)ba_node.data()) = in_trie_node.node;
    //write node
    dn_io.write_across_data_nodes(ba_node, 0, in_trie_node.location.block_offset_);
    in_trie_node.modified = false;
}

void pstate::trie_node::operate_trie(data_node_io& dn_io,
    trie_node& node,
    const kv_operation_e operation,
    const unsigned int depth,
    const ByteArray& kvkey,
    const ByteArray& in_value,
    ByteArray& out_value)
{
#if !_UNTRUSTED_
    int stack_check_var;
    THROW_EXCEPTION_ON_STACK_FULL(&stack_check_var)
#endif

    // first, create the node if necessary, or fail
    if(! node.initialized)
    {
        if(node.location.is_empty())
        {
            if (operation == PUT_OP)
            {
                // in put operation, always create a trie node
                create_node(kvkey, depth, kvkey.size(), node);
            }
            else
            {
                // no trie node to proceed with delete or get
                return;
            }
        }
        else
        {
            //load the node
            read_trie_node(dn_io, node.location.block_offset_, node);
        }
    }

    // operate on trie node
    unsigned int spl = shared_prefix_length((uint8_t*)node.node.key_chunk, node.node.hdr.keyChunkSize,
        kvkey.data() + depth, kvkey.size() - depth);

    if (spl == 0)
    {  // no match, so either go next or EOS matched
        //if right depth has not been reached OR (it has been reached but) the current trie is not EOS, go next
        if (depth < kvkey.size() || node.node.hdr.keyChunkSize > 0)
        {  // no match, go next
            do_operate_trie_next(
                dn_io, node, operation, depth, kvkey, in_value, out_value);
        }
        else
        {  // match EOS, do op
            switch (operation)
            {
                case PUT_OP:
                {
                    do_write_value(dn_io, node, in_value);
                    break;
                }
                case GET_OP:
                {
                    do_read_value(dn_io, node, out_value);
                    break;
                }
                case DEL_OP:
                {
                    do_delete_value(dn_io, node);
                    break;
                }
                default:
                {
                    throw error::ValueError("invalid kv/trie operation");
                }
            }
        }
    }
    else
    {  // some match, so either partial or full
        if (spl == node.node.hdr.keyChunkSize)
        {  // full match
            do_operate_trie_child(
                dn_io, node, operation, depth, kvkey, in_value, out_value);
        }
        else
        {  // partial match, continue only on PUT op
            if (operation == PUT_OP)
            {
                // split chunk and redo operate
                do_split_trie_node(dn_io, node, spl);

                // notice: current_tnh remains the same because: 1) chunk is just shorter; 2) its
                // next (if any) is removed; 3) it had and keeps having a child

                operate_trie(dn_io, node, operation, depth, kvkey, in_value, out_value);
            }
        }
    }

    if (operation == DEL_OP)
    {
        // check whether we should delete this trie node, while going bottom up
        delete_trie_node_childless(dn_io, node);
    }

    if(node.modified)
    {
        write_trie_node(dn_io, node);
    }
}  // operate_trie

void pstate::trie_node::init_trie_root(data_node_io& dn_io)
{
    //initialize root node
    trie_node root;
    root.location.block_offset_ = {dn_io.block_warehouse_.get_root_block_num(), data_node::data_begin_index()};
    ByteArray emptyKey;
    create_node(emptyKey, 0, 0, root);

    //store root node
    write_trie_node(dn_io, root);
}

void pstate::trie_node::operate_trie_root(
    data_node_io& dn_io, const kv_operation_e operation, const ByteArray& kvkey, const ByteArray& in_value, ByteArray& value)
{
    unsigned int depth = 0;
    // the first entry of the first data node is the trie root
    // if the trie contains data then the root has a next node
    // if the trie is empty then the next node is null/empty
    trie_node root;
    root.location.block_offset_ = {dn_io.block_warehouse_.get_root_block_num(), data_node::data_begin_index()};
    trie_node::read_trie_node(dn_io, root.location.block_offset_, root);

    do_operate_trie_next(dn_io, root, operation, depth, kvkey, in_value, value);

    // check modifications
    if(root.modified)
    {
        write_trie_node(dn_io, root);
    }
    // NOTICE: we do NOT sync the cache here, so modifications are not reflected in the block store;
    //         in the case of failure, any modification is discarded, the transaction in progress will not succeed,
    //         no new state is generated, and the request processing can (and will) start over from the last state
}