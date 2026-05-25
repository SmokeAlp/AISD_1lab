import os
import time
from typing import Tuple

from matplotlib import pyplot as plt


class LZ78:
    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size

    def encode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = {}
        dict_size = 1
        result = bytearray()
        current_string = b''
        i = 0
        while i < len(data):
            byte = data[i:i + 1]
            if current_string + byte in dictionary:
                current_string += byte
            else:
                if current_string:
                    index = dictionary[current_string]
                else:
                    index = 0
                new_string = current_string + byte
                if dict_size < self.max_dict_size:
                    dictionary[new_string] = dict_size
                    dict_size += 1
                result.extend(self._encode_pair(index, byte))
                current_string = b''
            i += 1

        if current_string:
            last_byte = current_string[-1:]
            prefix = current_string[:-1]
            if prefix in dictionary:
                index = dictionary[prefix]
            else:
                index = 0
            result.extend(self._encode_pair(index, last_byte))
        return bytes(result)

    def decode(self, encoded_data: bytes) -> bytes:
        if not encoded_data:
            return b''
        dictionary = {}
        dict_size = 1
        result = bytearray()
        pos = 0
        pair_size = 4
        while pos < len(encoded_data):
            if pos + pair_size > len(encoded_data):
                break
            index, byte = self._decode_pair(encoded_data[pos:pos + pair_size])
            pos += pair_size
            if index == 0:
                string = byte
            else:
                if index in dictionary:
                    string = dictionary[index] + byte
                else:
                    continue
            if dict_size < self.max_dict_size:
                dictionary[dict_size] = string
                dict_size += 1
            result.extend(string)
        return bytes(result)

    def _encode_pair(self, index: int, byte: bytes) -> bytes:
        index_bytes = index.to_bytes(3, byteorder='big')
        return index_bytes + byte

    def _decode_pair(self, pair_bytes: bytes) -> Tuple[int, bytes]:
        index = int.from_bytes(pair_bytes[:3], byteorder='big')
        byte = pair_bytes[3:4]
        return index, byte

def lz78_encode(data: bytes, max_dict_size: int = 4096) -> bytes:
    encoder = LZ78(max_dict_size)
    return encoder.encode(data)

def lz78_decode(encoded_data: bytes, max_dict_size: int = 4096) -> bytes:
    decoder = LZ78(max_dict_size)
    return decoder.decode(encoded_data)

class LZW:
    def __init__(self, max_dict_size: int = 4096):
        self.max_dict_size = max_dict_size
        if max_dict_size <= 256:
            self.index_bytes = 1
        else:
            self.index_bytes = (max_dict_size - 1).bit_length() // 8 + 1 if (
                                                                                        max_dict_size - 1).bit_length() % 8 > 0 else (
                                                                                                                                                 max_dict_size - 1).bit_length() // 8
            self.index_bytes = max(1, self.index_bytes)

    def _init_dict(self) -> dict:
        dictionary = {}
        for i in range(256):
            dictionary[bytes([i])] = i
        return dictionary

    def encode(self, data: bytes) -> bytes:
        if not data:
            return b''
        dictionary = self._init_dict()
        next_index = 256
        result = bytearray()
        current_string = b''

        for byte in data:
            current_byte = bytes([byte])
            new_string = current_string + current_byte
            if new_string in dictionary:
                current_string = new_string
            else:
                # Кодируем индекс
                code = dictionary[current_string]
                result.extend(code.to_bytes(self.index_bytes, 'big'))

                if next_index < self.max_dict_size:
                    dictionary[new_string] = next_index
                    next_index += 1
                current_string = current_byte

        if current_string:
            code = dictionary[current_string]
            result.extend(code.to_bytes(self.index_bytes, 'big'))

        return bytes(result)

    def decode(self, encoded_data: bytes) -> bytes:
        if not encoded_data:
            return b''
        step = self.index_bytes
        n = len(encoded_data)

        dictionary = {}
        for i in range(256):
            dictionary[i] = bytes([i])
        next_index = 256

        if n < step:
            return b''

        pos = 0
        prev_index = int.from_bytes(encoded_data[pos:pos + step], 'big')
        pos += step

        if prev_index not in dictionary:
            return b''

        result = bytearray(dictionary[prev_index])

        while pos + step <= n:
            current_index = int.from_bytes(encoded_data[pos:pos + step], 'big')
            pos += step

            if current_index in dictionary:
                current_string = dictionary[current_index]
            elif current_index == next_index:
                current_string = dictionary[prev_index] + bytes([dictionary[prev_index][0]])
            else:
                break

            result.extend(current_string)

            if next_index < self.max_dict_size:
                new_string = dictionary[prev_index] + bytes([current_string[0]])
                dictionary[next_index] = new_string
                next_index += 1

            prev_index = current_index

        return bytes(result)

    def encode_with_stats(self, data: bytes) -> Tuple[bytes, dict]:
        if not data:
            return b'', {}

        dictionary = self._init_dict()
        next_index = 256
        result = bytearray()
        current_string = b''
        stats = {
            'original_size': len(data),
            'dict_size_init': 256,
            'dict_size_final': 256,
            'unique_codes': 0,
            'total_codes': 0,
            'overflow_codes': 0,
            'index_bytes': self.index_bytes
        }

        for byte in data:
            current_byte = bytes([byte])
            new_string = current_string + current_byte

            if new_string in dictionary:
                current_string = new_string
            else:
                code = dictionary[current_string]
                result.extend(code.to_bytes(self.index_bytes, 'big'))
                stats['total_codes'] += 1
                if next_index < self.max_dict_size:
                    dictionary[new_string] = next_index
                    next_index += 1
                    stats['unique_codes'] += 1
                else:
                    stats['overflow_codes'] += 1

                current_string = current_byte

        if current_string:
            code = dictionary[current_string]
            result.extend(code.to_bytes(self.index_bytes, 'big'))
            stats['total_codes'] += 1

        stats['dict_size_final'] = next_index
        stats['compressed_size'] = len(result)
        stats['ratio'] = stats['original_size'] / stats['compressed_size'] if stats['compressed_size'] > 0 else 0
        stats['bits_per_code'] = self.index_bytes * 8
        stats['compression_percentage'] = (1 - stats['compressed_size'] / stats['original_size']) * 100

        return bytes(result), stats

class LZWFileHandler:
    MAGIC = b'LZW\x00'

    @staticmethod
    def int_to_bytes(value: int, size: int) -> bytes:
        result = bytearray()
        for i in range(size):
            result.append((value >> (i * 8)) & 0xFF)
        return bytes(result)

    @staticmethod
    def bytes_to_int(data: bytes) -> int:
        result = 0
        for i, byte in enumerate(data):
            result |= (byte << (i * 8))
        return result

    @staticmethod
    def save_compressed(data, filename: str, max_dict_size: int = 4096) -> int:
        if isinstance(data, str):
            data = data.encode('utf-8')
            is_text = True
        else:
            is_text = False
        encoder = LZW(max_dict_size)
        encoded = encoder.encode(data)

        with open(filename, 'wb') as f:
            f.write(LZWFileHandler.MAGIC)
            f.write(bytes([1 if is_text else 0]))
            f.write(LZWFileHandler.int_to_bytes(max_dict_size, 4))
            index_bytes = (max_dict_size.bit_length() + 7) // 8
            f.write(bytes([index_bytes]))
            f.write(LZWFileHandler.int_to_bytes(len(data), 8))
            f.write(LZWFileHandler.int_to_bytes(len(encoded), 8))
            f.write(encoded)

        print(f"Сжатые данные сохранены в: {filename}")
        print(f"Исходный размер: {len(data):,} байт")
        print(f"Сжатый размер: {len(encoded):,} байт")
        print(f"Коэффициент: {len(data) / len(encoded):.2f}x")
        print(f"Размер словаря: {max_dict_size}, индекс: {index_bytes} байт")
        return len(encoded)

    @staticmethod
    def load_compressed(filename: str, decode_as_string: bool = True):
        with open(filename, 'rb') as f:
            magic = f.read(4)
            if magic != LZWFileHandler.MAGIC:
                raise ValueError(f"Неверный формат файла: {magic}")

            is_text = f.read(1)[0] == 1
            max_dict_size_bytes = f.read(4)
            max_dict_size = LZWFileHandler.bytes_to_int(max_dict_size_bytes)
            index_bytes = f.read(1)[0]
            original_size_bytes = f.read(8)
            original_size = LZWFileHandler.bytes_to_int(original_size_bytes)
            encoded_size_bytes = f.read(8)
            encoded_size = LZWFileHandler.bytes_to_int(encoded_size_bytes)
            encoded_data = f.read(encoded_size)
            if len(encoded_data) != encoded_size:
                raise ValueError(f"Неполные данные: ожидалось {encoded_size}, получено {len(encoded_data)}")

        temp_encoder = LZW(max_dict_size)
        decoded = temp_encoder.decode(encoded_data)
        if len(decoded) > original_size:
            decoded = decoded[:original_size]
        if decode_as_string and is_text:
            return decoded.decode('utf-8')
        return decoded

    @staticmethod
    def compress_file(input_file: str, output_file: str, max_dict_size: int = 4096, is_text_file: bool = False) -> float:
        if is_text_file:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = f.read()
        else:
            with open(input_file, 'rb') as f:
                data = f.read()

        encoded_size = LZWFileHandler.save_compressed(data, output_file, max_dict_size)
        original_size = os.path.getsize(input_file)
        ratio = original_size / encoded_size if encoded_size > 0 else 0
        print(f"\nФайл: {input_file}")
        print(f"Исходный размер: {original_size:,} байт")
        print(f"Сжатый размер: {encoded_size:,} байт")
        print(f"Коэффициент сжатия: {ratio:.2f}x")
        return ratio

    @staticmethod
    def decompress_file(input_file: str, output_file: str) -> None:
        decoded = LZWFileHandler.load_compressed(input_file, decode_as_string=False)
        with open(output_file, 'wb') as f:
            f.write(decoded)
        print(f"Распакованные данные сохранены в: {output_file}")
        print(f"Размер: {len(decoded):,} байт")

def analyze_lzw_dict_size_impact(test_file, dict_sizes=None, output_plot='Результаты/LZW_график.png'):
    if dict_sizes is None:
        dict_sizes = [256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]

    is_text = test_file.lower().endswith('.txt')

    if is_text:
        with open(test_file, 'r', encoding='utf-8') as f:
            data = f.read().encode('utf-8')
    else:
        with open(test_file, 'rb') as f:
            data = f.read()

    original_size = len(data)
    ratios = []
    compressed_sizes = []
    encode_times = []
    decode_times = []
    dict_final_sizes = []
    total_codes_list = []
    valid_dict_sizes = []

    print(f"Исследование влияния размера словаря на сжатие LZW")
    print(f"Файл: {test_file}")
    print(f"Исходный размер: {original_size:,} байт")
    print(
        f"{'Словарь':<10} {'Сжато':<12} {'Коэфф':<8} {'Кодов':<10} {'Словарь':<10} {'Время enc':<10} {'Время dec':<10}")

    for ds in dict_sizes:
        if ds < 256:
            continue

        try:
            encoder = LZW(max_dict_size=ds)
            start_time = time.time()
            encoded, stats = encoder.encode_with_stats(data)
            encode_time = time.time() - start_time
            start_time = time.time()
            decoded = encoder.decode(encoded)
            decode_time = time.time() - start_time

            if decoded != data:
                print(f"Словарь: {ds:>6} | ОШИБКА: декодированные данные не совпадают")
                continue

            compressed_size = len(encoded)
            ratio = original_size / compressed_size if compressed_size > 0 else 0

            ratios.append(ratio)
            compressed_sizes.append(compressed_size)
            encode_times.append(encode_time)
            decode_times.append(decode_time)
            dict_final_sizes.append(stats['dict_size_final'])
            total_codes_list.append(stats['total_codes'])
            valid_dict_sizes.append(ds)

            print(f"{ds:<10} {compressed_size:<12,} {ratio:<8.2f}x {stats['total_codes']:<10} "
                  f"{stats['dict_size_final']:<10} {encode_time:<10.3f} {decode_time:<10.3f}")

        except Exception as e:
            print(f"Словарь: {ds:>6} | ОШИБКА: {str(e)}")
            continue

    if not ratios:
        print("\nНет успешных результатов для построения графика")
        return [], [], [], [], []


    fig, axes = plt.subplots(3, 2, figsize=(16, 14))
    fig.suptitle(f'Влияние размера словаря на сжатие LZW\nФайл: {os.path.basename(test_file)}',
                 fontsize=14, fontweight='bold')

    ax1 = axes[0, 0]
    ax1.plot(valid_dict_sizes, ratios, 'b-o', linewidth=2, markersize=8, label='Коэфф. сжатия')
    ax1.set_xlabel('Максимальный размер словаря')
    ax1.set_ylabel('Коэффициент сжатия')
    ax1.set_title('Коэффициент сжатия vs Размер словаря')
    ax1.grid(True, alpha=0.3)
    ax1.set_xscale('log', base=2)
    ax1.axhline(y=1.0, color='r', linestyle='--', alpha=0.5, label='Без сжатия')

    for i, (x, y) in enumerate(zip(valid_dict_sizes, ratios)):
            ax1.annotate(f'{y:.2f}x', (x, y), textcoords="offset points",
                         xytext=(0, 10), ha='center', fontsize=8)
    ax1.legend()

    ax2 = axes[0, 1]
    ax2.plot(valid_dict_sizes, compressed_sizes, 'g-s', linewidth=2, markersize=8)
    ax2.set_xlabel('Максимальный размер словаря')
    ax2.set_ylabel('Размер сжатых данных (байт)')
    ax2.set_title('Размер сжатых данных vs Размер словаря')
    ax2.grid(True, alpha=0.3)
    ax2.set_xscale('log', base=2)
    ax2.axhline(y=original_size, color='r', linestyle='--', alpha=0.5, label=f'Исходный: {original_size:,}')
    ax2.legend()

    ax3 = axes[1, 0]
    ax3.plot(valid_dict_sizes, encode_times, 'r-^', linewidth=2, markersize=8, label='Кодирование')
    ax3.plot(valid_dict_sizes, decode_times, 'm-v', linewidth=2, markersize=8, label='Декодирование')
    ax3.set_xlabel('Максимальный размер словаря')
    ax3.set_ylabel('Время (сек)')
    ax3.set_title('Время обработки vs Размер словаря')
    ax3.grid(True, alpha=0.3)
    ax3.set_xscale('log', base=2)
    ax3.legend()

    ax4 = axes[1, 1]
    ax4.plot(valid_dict_sizes, dict_final_sizes, 'c-D', linewidth=2, markersize=8, label='Финальный размер')
    ax4.plot(valid_dict_sizes, valid_dict_sizes, 'k--', alpha=0.5, label='Максимальный размер')
    ax4.set_xlabel('Максимальный размер словаря')
    ax4.set_ylabel('Реальный размер словаря')
    ax4.set_title('Использование словаря vs Максимальный размер')
    ax4.grid(True, alpha=0.3)
    ax4.set_xscale('log', base=2)
    ax4.legend()

    ax5 = axes[2, 0]
    ax5.plot(valid_dict_sizes, total_codes_list, 'y-o', linewidth=2, markersize=8)
    ax5.set_xlabel('Максимальный размер словаря')
    ax5.set_ylabel('Количество сгенерированных кодов')
    ax5.set_title('Количество кодов vs Размер словаря')
    ax5.grid(True, alpha=0.3)
    ax5.set_xscale('log', base=2)

    ax6 = axes[2, 1]
    compression_ratio_improvement = []
    for i in range(len(ratios)):
        if i == 0:
            compression_ratio_improvement.append(0)
        else:
            improvement = ((ratios[i] - ratios[i - 1]) / ratios[i - 1]) * 100
            compression_ratio_improvement.append(improvement)

    ax6.bar(range(len(valid_dict_sizes)), compression_ratio_improvement,
            color=['g' if x > 0 else 'r' for x in compression_ratio_improvement], alpha=0.7)
    ax6.set_xlabel('Переход между размерами словаря')
    ax6.set_ylabel('Улучшение сжатия (%)')
    ax6.set_title('Прирост эффективности при увеличении словаря')
    ax6.set_xticks(range(len(valid_dict_sizes)))
    ax6.set_xticklabels([f'{valid_dict_sizes[i - 1]}→{valid_dict_sizes[i]}' if i > 0 else 'базовый'
                         for i in range(len(valid_dict_sizes))], rotation=45, ha='right')
    ax6.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_plot, dpi=150, bbox_inches='tight')
    plt.show()

    best_idx = ratios.index(max(ratios))
    best_dict = valid_dict_sizes[best_idx]
    saturation_idx = None
    for i in range(1, len(compression_ratio_improvement)):
        if compression_ratio_improvement[i] < 1.0:
            saturation_idx = i
            break

    print(f"Оптимальный размер словаря (макс. сжатие): {best_dict:,}")
    print(f"Максимальный коэффициент сжатия: {ratios[best_idx]:.2f}x")
    print(f"Размер сжатых данных: {compressed_sizes[best_idx]:,} байт")
    print(
        f"Экономия: {original_size - compressed_sizes[best_idx]:,} байт ({(1 - compressed_sizes[best_idx] / original_size) * 100:.1f}%)")
    print(f"Время кодирования: {encode_times[best_idx]:.3f} сек")
    print(f"Время декодирования: {decode_times[best_idx]:.3f} сек")

    if saturation_idx:
        saturation_dict = valid_dict_sizes[saturation_idx]
        print(f"\nТочка насыщения: размер словаря {saturation_dict:,}")
        print(f"После этого размера прирост сжатия менее 1%")
    efficiency_scores = [r / (et + dt) if (et + dt) > 0 else 0
                         for r, et, dt in zip(ratios, encode_times, decode_times)]
    best_eff_idx = efficiency_scores.index(max(efficiency_scores))
    best_eff_dict = valid_dict_sizes[best_eff_idx]

    print(f"\nОптимальный размер словаря (баланс скорость/сжатие): {best_eff_dict:,}")
    print(f"Коэффициент сжатия: {ratios[best_eff_idx]:.2f}x")
    print(f"Эффективность: {efficiency_scores[best_eff_idx]:.2f}")
    print(f"График сохранён в: {output_plot}")

    return valid_dict_sizes, ratios, compressed_sizes, encode_times, dict_final_sizes

# analyze_lzw_dict_size_impact("Тестовые данные/Chehov_Anton__Bezotcovshina_www.Litmir.net_72436.txt")