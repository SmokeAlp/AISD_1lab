import os
from collections import defaultdict


class HuffmanNode:
    def __init__(self, symbol=None, freq=0, left=None, right=None):
        self.symbol = symbol
        self.freq = freq
        self.left = left
        self.right = right

class HuffmanCoder:
    @staticmethod
    def build_huffman_tree(frequencies):
        nodes = []
        for symbol, freq in frequencies.items():
            nodes.append(HuffmanNode(symbol=symbol, freq=freq))
        nodes.sort(key=lambda x: x.freq)

        while len(nodes) > 1:
            left = nodes.pop(0)
            right = nodes.pop(0)
            parent = HuffmanNode(
                freq=left.freq + right.freq,
                left=left,
                right=right
            )
            nodes.append(parent)
            nodes.sort(key=lambda x: x.freq)
        return nodes[0] if nodes else None

    @staticmethod
    def get_code_lengths(node, depth=0, lengths=None):
        if lengths is None:
            lengths = {}
        if node.symbol is not None:
            lengths[node.symbol] = depth
        else:
            if node.left:
                HuffmanCoder.get_code_lengths(node.left, depth + 1, lengths)
            if node.right:
                HuffmanCoder.get_code_lengths(node.right, depth + 1, lengths)
        return lengths

    @staticmethod
    def build_canonical_codes(code_lengths):
        symbols_by_length = defaultdict(list)
        for symbol, length in code_lengths.items():
            symbols_by_length[length].append(symbol)
        for length in symbols_by_length:
            symbols_by_length[length].sort()
        canonical_codes = {}
        code = 0
        prev_length = 0

        for length in sorted(symbols_by_length.keys()):
            code <<= (length - prev_length)
            prev_length = length
            for symbol in symbols_by_length[length]:
                code_str = bin(code)[2:].zfill(length)
                canonical_codes[symbol] = code_str
                code += 1

        decode_info = {}
        for length, symbols in symbols_by_length.items():
            first_symbol = symbols[0]
            first_code_str = canonical_codes[first_symbol]
            first_code = int(first_code_str, 2)
            decode_info[length] = (first_code, len(symbols))
        return canonical_codes, decode_info

    @staticmethod
    def encode(data, probabilities=None):
        if not data:
            return b'', {}, {}

        frequencies = {}
        for byte in data:
            frequencies[byte] = frequencies.get(byte, 0) + 1
        if probabilities is not None:
            total = sum(probabilities.values())
            frequencies = {sym: int(prob * total) for sym, prob in probabilities.items()}
            for byte in data:
                if byte not in frequencies:
                    frequencies[byte] = 1

        tree = HuffmanCoder.build_huffman_tree(frequencies)
        code_lengths = HuffmanCoder.get_code_lengths(tree)
        canonical_codes, decode_info = HuffmanCoder.build_canonical_codes(code_lengths)
        encoded_bits = ''.join(canonical_codes[byte] for byte in data)
        padding = (8 - len(encoded_bits) % 8) % 8
        encoded_bits += '0' * padding
        encoded_bytes = bytearray()
        for i in range(0, len(encoded_bits), 8):
            byte_bits = encoded_bits[i:i + 8]
            encoded_bytes.append(int(byte_bits, 2))
        return bytes(encoded_bytes), code_lengths, frequencies

    @staticmethod
    def decode(encoded_data, code_lengths):
        if not encoded_data:
            return b''

        symbols_by_length = defaultdict(list)
        for symbol, length in code_lengths.items():
            symbols_by_length[length].append(symbol)
        for length in symbols_by_length:
            symbols_by_length[length].sort()

        first_codes = {}
        code = 0
        prev_length = 0
        for length in sorted(symbols_by_length.keys()):
            code <<= (length - prev_length)
            first_codes[length] = code
            code += len(symbols_by_length[length])
            prev_length = length
        bits = []
        for byte in encoded_data:
            bits.append(f'{byte:08b}')
        bits_str = ''.join(bits)
        result = bytearray()
        pos = 0
        n = len(bits_str)
        while pos < n:
            for length in sorted(symbols_by_length.keys()):
                if pos + length > n:
                    continue
                current_code = int(bits_str[pos:pos + length], 2)
                first_code = first_codes[length]
                num_symbols = len(symbols_by_length[length])
                if first_code <= current_code < first_code + num_symbols:
                    index = current_code - first_code
                    symbol = symbols_by_length[length][index]
                    result.append(symbol)
                    pos += length
                    break
            else:
                break
        return bytes(result)

class HuffmanFile:
    MAGIC = b'HA\x00'
    @staticmethod
    def int_to_bytes(value, size):
        result = bytearray()
        for i in range(size):
            result.append((value >> (i * 8)) & 0xFF)
        return bytes(result)

    @staticmethod
    def bytes_to_int(data):
        result = 0
        for i, byte in enumerate(data):
            result |= (byte << (i * 8))
        return result

    @staticmethod
    def save_compressed(data, filename, probabilities=None):
        if isinstance(data, str):
            data = data.encode('utf-8')
            is_text = True
        else:
            is_text = False

        encoded, code_lengths, frequencies = HuffmanCoder.encode(data, probabilities)
        non_zero_lengths = {sym: length for sym, length in code_lengths.items() if length > 0}

        with open(filename, 'wb') as f:
            f.write(HuffmanFile.MAGIC)
            f.write(bytes([1 if is_text else 0]))
            f.write(HuffmanFile.int_to_bytes(len(non_zero_lengths), 2))
            for symbol, length in non_zero_lengths.items():
                f.write(bytes([symbol]))
                f.write(bytes([length]))
            f.write(HuffmanFile.int_to_bytes(len(data), 8))
            padding = (8 - len(''.join(f'{b:08b}' for b in encoded)) % 8) % 8
            f.write(bytes([padding]))
            f.write(HuffmanFile.int_to_bytes(len(encoded), 8))
            f.write(encoded)
        print(f"Сжатые данные сохранены в: {filename}")
        print(f"Исходный размер: {len(data):,} байт")
        print(f"Сжатый размер: {len(encoded):,} байт")
        print(f"Коэффициент: {len(data) / len(encoded):.2f}x")
        return len(encoded)

    @staticmethod
    def load_compressed(filename, decode_as_string=True, compressor = False):
        with open(filename, 'rb') as f:
            magic = f.read(3)
            if magic != HuffmanFile.MAGIC:
                print(magic, "     ", HuffmanFile.MAGIC)
                raise ValueError(f"Неверный формат файла: {magic}")
            is_text = f.read(1)[0] == 1
            num_symbols = HuffmanFile.bytes_to_int(f.read(2))
            code_lengths = {}
            for _ in range(num_symbols):
                symbol = f.read(1)[0]
                length = f.read(1)[0]
                code_lengths[symbol] = length
            if not compressor:
                original_size = HuffmanFile.bytes_to_int(f.read(8))
                padding = f.read(1)[0]
                compressed_size = HuffmanFile.bytes_to_int(f.read(8))
            encoded_data = f.read(compressed_size)
            if len(encoded_data) != compressed_size:
                raise ValueError(f"Неполные данные")

        decoded = HuffmanCoder.decode(encoded_data, code_lengths)
        if len(decoded) > original_size:
            decoded = decoded[:original_size]
        if decode_as_string and is_text:
            return decoded.decode('utf-8')
        return decoded

    @staticmethod
    def compress_file(input_file, output_file, probabilities=None):
        is_text_file = False
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                f.read(1024)
            is_text_file = True
        except UnicodeDecodeError:
            is_text_file = False
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()
        else:
            with open(input_file, 'rb') as f:
                data = f.read()
        compressed_size = HuffmanFile.save_compressed(data, output_file, probabilities)
        original_size = os.path.getsize(input_file)
        ratio = original_size / compressed_size if compressed_size > 0 else 0
        print(f"\nФайл: {input_file}")
        print(f"Исходный размер: {original_size:,} байт")
        print(f"Сжатый размер: {compressed_size:,} байт")
        print(f"Коэффициент сжатия: {ratio:.2f}x")
        return ratio

    @staticmethod
    def decompress_file(input_file, output_file=None, decode_as_string=True):
        decoded = HuffmanFile.load_compressed(input_file, decode_as_string)
        if output_file:
            if isinstance(decoded, str):
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(decoded)
            else:
                with open(output_file, 'wb') as f:
                    f.write(decoded)
            print(f"Распакованные данные сохранены в: {output_file}")
        return decoded
