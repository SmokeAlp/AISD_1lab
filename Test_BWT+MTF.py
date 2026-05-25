import os
import sys
import matplotlib.pyplot as plt
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from BWT import bwt_encode_efficient
from entropy import mtf_encode, calculate_entropy_mtf


def bwt_mtf_encode_block(block_data):
    if not block_data:
        return b''
    try:
        bwt_result, _ = bwt_encode_efficient(block_data)
    except (NameError, AttributeError):
        from BWT import bwt_encode
        bwt_result, _ = bwt_encode(block_data)

    mtf_result = mtf_encode(bwt_result)

    return mtf_result


def bwt_mtf_decode_block(encoded_data, block_size):
    from entropy import mtf_decode
    mtf_decoded = mtf_decode(encoded_data)

    from BWT import bwt_decode_extended
    try:
        from BWT import bwt_encode
        original_bwt, idx = bwt_encode(mtf_decoded[:len(mtf_decoded)])
        decoded = bwt_decode_extended(original_bwt, idx)
        return decoded
    except:
        return mtf_decoded


def process_file_with_blocks(file_path, block_sizes):
    with open(file_path, 'rb') as f:
        data = f.read()

    original_size = len(data)
    original_entropy = calculate_entropy_mtf(data)

    print(f"\nФайл: {os.path.basename(file_path)}")
    print(f"Размер: {original_size:,} байт")
    print(f"Исходная энтропия: {original_entropy:.4f} бит/байт")
    print("-" * 60)

    results = {}

    for block_size in block_sizes:
        if block_size > original_size:
            blocks = [data]
        else:
            blocks = [data[i:i + block_size] for i in range(0, original_size, block_size)]

        processed_blocks = []
        total_processed_size = 0

        for block in blocks:
            if len(block) < 2:
                processed = block
            else:
                try:
                    processed = bwt_mtf_encode_block(block)
                except Exception as e:
                    from entropy import mtf_encode
                    processed = mtf_encode(block)
            processed_blocks.append(processed)
            total_processed_size += len(processed)

        combined_processed = b''.join(processed_blocks)

        if combined_processed:
            entropy = calculate_entropy_mtf(combined_processed)
            entropy_per_byte = entropy
        else:
            entropy_per_byte = 0
        compression_ratio = original_entropy / entropy_per_byte if entropy_per_byte > 0 else 0

        results[block_size] = {
            'entropy': entropy_per_byte,
            'processed_size': total_processed_size,
            'num_blocks': len(blocks),
            'compression_ratio': compression_ratio
        }

        print(f"Блок {block_size:8d} байт: {len(blocks):4d} блоков, "
              f"энтропия: {entropy_per_byte:.4f} бит/байт, "
              f"улучшение: {compression_ratio:.3f}x")

    return results, original_entropy, original_size

def plot_entropy_comparison(all_results, all_original_entropies, block_sizes):
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()

    colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown']

    for idx, (file_name, results) in enumerate(all_results.items()):
        if idx >= 4:
            break

        ax = axes[idx]

        block_sizes_list = list(results.keys())
        entropies = [results[bs]['entropy'] for bs in block_sizes_list]
        ratios = [results[bs]['compression_ratio'] for bs in block_sizes_list]

        original_entropy = all_original_entropies[file_name]

        ax.plot(block_sizes_list, entropies, 'o-', color=colors[idx], linewidth=2, markersize=6, label='После BWT+MTF')
        ax.axhline(y=original_entropy, color='red', linestyle='--', linewidth=2, label='Исходная энтропия')

        ax.set_xlabel('Размер блока (байт)', fontsize=10)
        ax.set_ylabel('Энтропия (бит/байт)', fontsize=10)
        ax.set_title(f'{file_name}\n(размер: {len(block_sizes_list)} блоков)', fontsize=11)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        best_idx = entropies.index(min(entropies))
        best_block = block_sizes_list[best_idx]
        best_entropy = entropies[best_idx]
        ax.annotate(f'лучший: {best_block}',
                    xy=(best_block, best_entropy),
                    xytext=(5, 5), textcoords='offset points',
                    fontsize=8, color='green')
    for idx in range(len(all_results), 4):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.suptitle('Зависимость энтропии от размера блока для BWT+MTF', fontsize=14, y=1.02)
    plt.show()

    return fig


def plot_compression_ratio(all_results, block_sizes):
    fig, ax = plt.subplots(figsize=(12, 6))

    colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown']

    for idx, (file_name, results) in enumerate(all_results.items()):
        if idx >= 5:
            break

        ratios = [results[bs]['compression_ratio'] for bs in block_sizes if bs in results]
        ax.plot(block_sizes[:len(ratios)], ratios, 'o-', color=colors[idx % len(colors)],
                linewidth=2, markersize=6, label=file_name)

    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, label='Без улучшения (1.0)')
    ax.set_xlabel('Размер блока (байт)', fontsize=12)
    ax.set_ylabel('Коэффициент улучшения энтропии\n(исходная / после BWT+MTF)', fontsize=12)
    ax.set_title('Улучшение энтропии после BWT+MTF для разных размеров блоков', fontsize=14)
    ax.legend(loc='best', fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    return fig


def plot_entropy_summary(all_results, all_original_entropies, block_sizes):
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(block_sizes))
    width = 0.12

    colors = ['blue', 'red', 'green', 'purple', 'orange', 'brown']

    for idx, (file_name, results) in enumerate(all_results.items()):
        if idx >= 6:
            break

        entropies = [results[bs]['entropy'] for bs in block_sizes if bs in results]
        normalized_entropies = [e / all_original_entropies[file_name] for e in entropies]

        ax.bar(x + idx * width, normalized_entropies, width,
               label=file_name, color=colors[idx % len(colors)], alpha=0.7)

    ax.axhline(y=1.0, color='black', linestyle='--', linewidth=1, label='Исходная энтропия')
    ax.set_xlabel('Размер блока (байт)', fontsize=12)
    ax.set_ylabel('Нормированная энтропия (после/до)', fontsize=12)
    ax.set_title('Нормированная энтропия после BWT+MTF для разных размеров блоков', fontsize=14)
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels([str(bs) for bs in block_sizes])
    ax.legend(loc='best', fontsize=8)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.show()

    return fig

def test_single_file(file_path, block_sizes=None):
    if block_sizes is None:
        block_sizes = [64, 128, 256, 512, 1024, 2048, 4096, 8192]

    if not os.path.exists(file_path):
        print(f"Файл не найден: {file_path}")
        return None

    results, original_entropy, file_size = process_file_with_blocks(file_path, block_sizes)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    block_sizes_list = list(results.keys())
    entropies = [results[bs]['entropy'] for bs in block_sizes_list]
    ratios = [results[bs]['compression_ratio'] for bs in block_sizes_list]

    ax1.plot(block_sizes_list, entropies, 'bo-', linewidth=2, markersize=8)
    ax1.axhline(y=original_entropy, color='red', linestyle='--', linewidth=2, label='Исходная энтропия')
    ax1.set_xlabel('Размер блока (байт)', fontsize=12)
    ax1.set_ylabel('Энтропия (бит/байт)', fontsize=12)
    ax1.set_title(f'Энтропия после BWT+MTF\n{os.path.basename(file_path)}', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    ax2.plot(block_sizes_list, ratios, 'go-', linewidth=2, markersize=8)
    ax2.axhline(y=1.0, color='red', linestyle='--', linewidth=1)
    ax2.set_xlabel('Размер блока (байт)', fontsize=12)
    ax2.set_ylabel('Коэффициент улучшения', fontsize=12)
    ax2.set_title('Улучшение относительно исходной энтропии', fontsize=12)
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

    best_block = block_sizes_list[entropies.index(min(entropies))]
    print(f"\nОптимальный размер блока для {os.path.basename(file_path)}: {best_block} байт")
    print(f"Энтропия: {original_entropy:.4f} → {min(entropies):.4f} бит/байт")
    print(f"Улучшение: {original_entropy / min(entropies):.3f}x")

    return results


# test_single_file("Тестовые данные/Chehov_Anton__Bezotcovshina_www.Litmir.net_72436.txt", [64, 128, 256, 512, 1024])