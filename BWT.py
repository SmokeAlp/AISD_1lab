def bwt_encode(data):
    if not data:
        return b'', 0

    n = len(data)
    matrix = []
    for i in range(n):
        rotation = data[i:] + data[:i]
        matrix.append(rotation)
    matrix.sort()
    index = matrix.index(data)
    last_column = bytes(row[-1] for row in matrix)

    return last_column, index

def bwt_decode(encoded_data, original_index):
    if not encoded_data:
        return b''

    n = len(encoded_data)
    matrix = [bytearray() for _ in range(n)]
    for _ in range(n):
        for i in range(n):
            matrix[i].insert(0, encoded_data[i])
        matrix.sort()
    result = bytes(matrix[original_index])

    return result

def bwt_decode_extended(encoded_data, original_index):
    if not encoded_data:
        return b''

    n = len(encoded_data)
    counts = [0] * 256
    for byte in encoded_data:
        counts[byte] += 1
    first_column = bytearray()
    for byte in range(256):
        first_column.extend([byte] * counts[byte])
    first_column = bytes(first_column)

    positions = [[] for _ in range(256)]
    for i, byte in enumerate(encoded_data):
        positions[byte].append(i)
    next_index = [0] * n
    pos_counters = [0] * 256
    for i in range(n):
        byte = first_column[i]
        next_index[i] = positions[byte][pos_counters[byte]]
        pos_counters[byte] += 1

    result = bytearray()
    current = original_index
    for _ in range(n):
        current = next_index[current]
        result.append(encoded_data[current])
    return bytes(result)

def counting_sort(data):
    if not data:
        return b''
    counts = [0] * 256
    for byte in data:
        counts[byte] += 1
    result = bytearray()
    for byte in range(256):
        result.extend([byte] * counts[byte])
    return bytes(result)

def bwt_encode_large(data, block_size=4096):
    if not data:
        return b'', [], []
    blocks = []
    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        blocks.append(block)
    encoded_blocks = []
    indexes = []
    block_sizes = []
    for block in blocks:
        encoded, idx = bwt_encode(block)
        encoded_blocks.append(encoded)
        indexes.append(idx)
        block_sizes.append(len(encoded))
    encoded_data = b''.join(encoded_blocks)
    return encoded_data, indexes, block_sizes

def bwt_decode_large(encoded_data, indexes, block_sizes):
    if not encoded_data:
        return b''
    blocks = []
    pos = 0
    for size in block_sizes:
        blocks.append(encoded_data[pos:pos + size])
        pos += size
    decoded_blocks = []
    for i, block in enumerate(blocks):
        decoded = bwt_decode_extended(block, indexes[i])
        decoded_blocks.append(decoded)
    return b''.join(decoded_blocks)

def bwt_encode_large_with_metadata(data, block_size=4096):
    if not data:
        return b'', 0
    blocks = []
    for i in range(0, len(data), block_size):
        block = data[i:i + block_size]
        blocks.append(block)
    encoded_blocks = []
    indexes = []
    for block in blocks:
        encoded, idx = bwt_encode(block)
        encoded_blocks.append(encoded)
        indexes.append(idx)
    num_blocks = len(blocks)
    result = bytearray()
    result.extend(num_blocks.to_bytes(4, 'little'))

    for block in encoded_blocks:
        result.extend(len(block).to_bytes(4, 'little'))

    for idx in indexes:
        result.extend(idx.to_bytes(4, 'little'))

    for block in encoded_blocks:
        result.extend(block)

    return bytes(result), num_blocks

def bwt_decode_large_with_metadata(package):
    if not package:
        return b''
    pos = 0
    num_blocks = int.from_bytes(package[pos:pos + 4], 'little')
    pos += 4
    block_sizes = []
    for _ in range(num_blocks):
        size = int.from_bytes(package[pos:pos + 4], 'little')
        block_sizes.append(size)
        pos += 4
    indexes = []
    for _ in range(num_blocks):
        idx = int.from_bytes(package[pos:pos + 4], 'little')
        indexes.append(idx)
        pos += 4
    encoded_blocks = []
    for size in block_sizes:
        encoded_blocks.append(package[pos:pos + size])
        pos += size
    decoded_blocks = []
    for i, block in enumerate(encoded_blocks):
        decoded = bwt_decode_extended(block, indexes[i])
        decoded_blocks.append(decoded)
    return b''.join(decoded_blocks)

class BWTBlockProcessor:
    DEFAULT_BLOCK_SIZE = 4096
    @staticmethod
    def encode(data, block_size=DEFAULT_BLOCK_SIZE):
        return bwt_encode_large_with_metadata(data, block_size)

    @staticmethod
    def decode(package):
        return bwt_decode_large_with_metadata(package)

###

def suffix_array_to_bwt(data, suffix_array):
    if not data or not suffix_array:
        return b'', 0
    n = len(data)
    last_column = bytearray()
    original_index = None
    for i, pos in enumerate(suffix_array):
        if pos == 0:
            last_byte = data[-1]
        else:
            last_byte = data[pos - 1]
        last_column.append(last_byte)
        if pos == 0:
            original_index = i
    return bytes(last_column), original_index

def build_suffix_array(data):
    if not data:
        return []
    n = len(data)
    rank = [data[i] for i in range(n)]
    k = 1
    tmp = [0] * n
    sa = list(range(n))
    while True:
        sa.sort(key=lambda x: (rank[x], rank[x + k] if x + k < n else -1))
        tmp[sa[0]] = 0
        for i in range(1, n):
            prev, cur = sa[i - 1], sa[i]
            prev_key = (rank[prev], rank[prev + k] if prev + k < n else -1)
            cur_key = (rank[cur], rank[cur + k] if cur + k < n else -1)
            tmp[cur] = tmp[prev] + (prev_key != cur_key)
        rank, tmp = tmp, rank
        if rank[sa[-1]] == n - 1:
            break
        k <<= 1
    return sa

def bwt_encode_efficient(data):
    if not data:
        return b'', 0
    n = len(data)
    extended = data + data
    suffix_array = build_suffix_array(extended)
    last_column = bytearray()
    original_index = None
    valid_indexes = [i for i in suffix_array if i < n]

    for pos in valid_indexes:
        if pos == 0:
            last_byte = data[-1]
        else:
            last_byte = data[pos - 1]
        last_column.append(last_byte)
        if pos == 0:
            original_index = len(last_column) - 1
    return bytes(last_column), original_index

# def bwt_encode_efficient_simple(data):
#     if not data:
#         return b'', 0
#     n = len(data)
#     suffix_array = build_suffix_array(data)
#     last_column, original_index = suffix_array_to_bwt(data, suffix_array)
#     return last_column, original_index

class EfficientBWT:
    @staticmethod
    def build_suffix_array(data):
        return build_suffix_array(data)

    @staticmethod
    def encode(data):
        return bwt_encode_efficient(data)

    @staticmethod
    def encode_large(data, block_size=65536):
        if not data:
            return b'', []
        result_parts = []
        indexes = []
        for i in range(0, len(data), block_size):
            block = data[i:i + block_size]
            encoded, idx = EfficientBWT.encode(block)
            result_parts.append(encoded)
            indexes.append(idx)
        return b''.join(result_parts), indexes

def test_bwt():
    print("---Тестирование преобразования Бароуза Уиллера")
    test_data = bytes([0x62, 0x61, 0x6e, 0x61, 0x6e, 0x61])
    print(f"\nИсходные данные: {test_data}")

    encoded, idx = bwt_encode(test_data)
    print(f"Закодировано: {encoded}")
    print(f"Индекс строки: {idx}")

    decoded = bwt_decode(encoded, idx)
    print(f"Декодировано: {decoded}")

# test_bwt()