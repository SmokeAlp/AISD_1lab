import math
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np


def calculate_entropy(data, Ms=1):
    if len(data) % Ms != 0:
        raise ValueError(f"Длина данных ({len(data)}) не кратна Ms ({Ms})")

    symbols = []
    for i in range(0, len(data), Ms):
        symbol = data[i:i + Ms]
        symbols.append(symbol)
    symbol_counts = Counter(symbols)
    total_symbols = len(symbols)
    entropy = 0.0
    for count in symbol_counts.values():
        probability = count / total_symbols
        entropy -= probability * math.log2(probability)

    return entropy

def analyze_entropy_for_text(text, max_ms=4):
    filtered_text = ''.join(char for char in text if ord(char) <= 127)

    print(f"Исходный текст: {len(text)} символов")
    print(f"Отфильтрованный текст: {len(filtered_text)} символов")
    data = filtered_text.encode('ascii')
    results = {}

    print("Результаты расчета энтропии:")

    for Ms in range(1, max_ms + 1):
        try:
            entropy = calculate_entropy(data, Ms)
            total_symbols = len(data) // Ms
            total_entropy = entropy * total_symbols

            results[Ms] = {
                'entropy': entropy,
                'total_symbols': total_symbols,
                'total_entropy': total_entropy,
                'data_size': len(data)
            }

            print(f"Ms (байт): {Ms}; Символов: {total_symbols}; Энтропия (бит/символ): {entropy:.4f}; Всего бит: {total_entropy:.2f}")
        except ValueError as e:
            print(f"Ms (байт): {Ms}; {e}")
            results[Ms] = None

    return results, filtered_text, data

def plot_entropy_dependence(results, title="Зависимость энтропии от длины символа"):
    ms_values = []
    entropy_values = []
    total_entropy_values = []

    for Ms, data in results.items():
        if data is not None:
            ms_values.append(Ms)
            entropy_values.append(data['entropy'])
            total_entropy_values.append(data['total_entropy'])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    ax1.plot(ms_values, entropy_values, 'bo-', linewidth=2, markersize=8)
    ax1.set_xlabel('Длина символа Ms (байт)', fontsize=12)
    ax1.set_ylabel('Энтропия (бит/символ)', fontsize=12)
    ax1.set_title('Энтропия на символ', fontsize=14)
    ax1.grid(True, alpha=0.3)

    for Ms, ent in zip(ms_values, entropy_values):
        ax1.annotate(f'{ent:.2f}', xy=(Ms, ent), xytext=(5, 5),
                     textcoords='offset points', fontsize=9)

    ax2.plot(ms_values, total_entropy_values, 'rs-', linewidth=2, markersize=8)
    ax2.set_xlabel('Длина символа Ms (байт)', fontsize=12)
    ax2.set_ylabel('Общая энтропия (бит)', fontsize=12)
    ax2.set_title('Суммарная энтропия сообщения', fontsize=14)
    ax2.grid(True, alpha=0.3)

    for Ms, tent in zip(ms_values, total_entropy_values):
        ax2.annotate(f'{tent:.0f}', xy=(Ms, tent), xytext=(5, 5),
                     textcoords='offset points', fontsize=9)

    plt.tight_layout()
    plt.suptitle(title, fontsize=16, y=1.02)
    plt.show()

    return fig

def analyze_real_text():
    text = """It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of
    foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the
    season of Darkness, it was the spring of hope, it was the winter of despair, we had a everything before us, we had
    nothing before us, we were all going direct to Heaven, we were all going direct the other way - in short, the
    period was so far like present period, that some of its noisiest authorities insisted on its being received,
    for good or for evil, in the superlative degree of comparison only.
    """
    print("Анализ энтропии английского теквста")
    results, filtered_text, data = analyze_entropy_for_text(text, max_ms=4)
    plot_entropy_dependence(results, "Зависимость энтропии от длины символа (английский текст)")
    return results, filtered_text


def mtf_encode(data):
    dictionary = list(range(256))
    result = bytearray()
    for byte in data:
        position = dictionary.index(byte)
        result.append(position)
        dictionary.pop(position)
        dictionary.insert(0, byte)
    return bytes(result)

def mtf_decode(encoded_data):
    dictionary = list(range(256))
    result = bytearray()
    for index in encoded_data:
        byte = dictionary[index]
        result.append(byte)
        dictionary.pop(index)
        dictionary.insert(0, byte)
    return bytes(result)

def mtf_encode_utf8(text):
    unique_chars = sorted(set(text))
    dictionary = list(unique_chars)
    result = bytearray()
    for char in text:
        position = dictionary.index(char)
        if position > 255:
            result.extend(position.to_bytes(2, 'big'))
        else:
            result.append(position)
        dictionary.pop(position)
        dictionary.insert(0, char)
    return bytes(result), unique_chars

def mtf_decode_utf8(encoded_data, dictionary):
    working_dict = list(dictionary)
    result = []
    i = 0
    data_len = len(encoded_data)
    while i < data_len:
        if i + 1 < data_len and encoded_data[i] > 127:
            index = int.from_bytes(encoded_data[i:i + 2], 'big')
            i += 2
        else:
            index = encoded_data[i]
            i += 1
        char = working_dict[index]
        result.append(char)
        working_dict.pop(index)
        working_dict.insert(0, char)
    return ''.join(result)

def calculate_entropy_mtf(data):
    if not data:
        return 0.0
    counter = Counter(data)
    total = len(data)
    entropy = 0.0
    for count in counter.values():
        prob = count / total
        entropy -= prob * math.log2(prob)
    return entropy

def analyze_mtf_effect():
    print("\nАнализ текста")
    text = """It was the best of times, it was the worst of times, it was the age of wisdom, it was the age of
        foolishness, it was the epoch of belief, it was the epoch of incredulity, it was the season of Light, it was the
        season of Darkness, it was the spring of hope, it was the winter of despair, we had a everything before us, we had
        nothing before us, we were all going direct to Heaven, we were all going direct the other way - in short, the
        period was so far like present period, that some of its noisiest authorities insisted on its being received,
        for good or for evil, in the superlative degree of comparison only.
        """
    data = text.encode('ascii')
    mtf_encoded = mtf_encode(data)
    entropy_original = calculate_entropy_mtf(data)
    entropy_mtf = calculate_entropy_mtf(mtf_encoded)
    unique_original = len(set(data))
    unique_mtf = len(set(mtf_encoded))

    print(f"Исходная энтропия: {entropy_original:.4f} бит/символ")
    print(f"MTF энтропия: {entropy_mtf:.4f} бит/символ")
    print(f"Уникальных байт (исходный): {unique_original}")
    print(f"Уникальных байт (MTF): {unique_mtf}")
    return entropy_original, entropy_mtf

# энтропия
analyze_real_text()

# mtf
analyze_mtf_effect()