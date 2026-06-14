import json
import os
import re
import pickle
from pathlib import Path
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Optional

import pandas as pd

from .text_cleaner import clean_text, read_file, batch_clean_files, get_file_checksum
from .variant_mapper import VariantCharMapper, create_mapper


class DynastyFrequencyCounter:
    def __init__(self, dynasty_config_path: str, variant_mapper: VariantCharMapper,
                 cleaned_cache_dir: str, frequency_cache_file: str):
        self.dynasty_config_path = dynasty_config_path
        self.variant_mapper = variant_mapper
        self.cleaned_cache_dir = cleaned_cache_dir
        self.frequency_cache_file = frequency_cache_file

        self.dynasties: List[dict] = []
        self.dynasty_order: Dict[str, int] = {}
        self.dynasty_extract_regex: str = ""
        self.unknown_dynasty_name: str = "未知"

        self._load_dynasty_config()

        self.dynasty_freqs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.dynasty_total_chars: Dict[str, int] = defaultdict(int)
        self.dynasty_file_checksums: Dict[str, Dict[str, str]] = defaultdict(dict)
        self.dynasty_file_info: Dict[str, List[dict]] = defaultdict(list)

        self._load_cache()

    def _load_dynasty_config(self):
        with open(self.dynasty_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.dynasties = config.get("dynasties", [])
        for d in self.dynasties:
            self.dynasty_order[d["name"]] = d["order"]

        patterns = config.get("file_patterns", {})
        self.dynasty_extract_regex = patterns.get("dynasty_extract_regex", r"^(.*?)_")
        self.unknown_dynasty_name = config.get("unknown_dynasty_name", "未知")

    def _load_cache(self):
        if os.path.exists(self.frequency_cache_file):
            try:
                with open(self.frequency_cache_file, "rb") as f:
                    cache = pickle.load(f)
                self.dynasty_freqs = defaultdict(lambda: defaultdict(int), cache.get("freqs", {}))
                self.dynasty_total_chars = defaultdict(int, cache.get("total_chars", {}))
                self.dynasty_file_checksums = defaultdict(dict, cache.get("checksums", {}))
                self.dynasty_file_info = defaultdict(list, cache.get("file_info", {}))
            except Exception:
                pass

    def _save_cache(self):
        cache = {
            "freqs": dict(self.dynasty_freqs),
            "total_chars": dict(self.dynasty_total_chars),
            "checksums": dict(self.dynasty_file_checksums),
            "file_info": dict(self.dynasty_file_info),
        }
        os.makedirs(os.path.dirname(self.frequency_cache_file), exist_ok=True)
        with open(self.frequency_cache_file, "wb") as f:
            pickle.dump(cache, f)

    def extract_dynasty_from_filename(self, filename: str) -> str:
        match = re.match(self.dynasty_extract_regex, os.path.basename(filename))
        if match:
            dynasty_name = match.group(1)
            if dynasty_name in self.dynasty_order:
                return dynasty_name
        return self.unknown_dynasty_name

    def count_file(self, file_path: str, use_cleaned_cache: bool = True) -> Tuple[str, Dict[str, int], int]:
        dynasty = self.extract_dynasty_from_filename(file_path)
        checksum = get_file_checksum(file_path)

        if use_cleaned_cache:
            cleaned_file = os.path.join(
                self.cleaned_cache_dir,
                f"{os.path.splitext(os.path.basename(file_path))[0]}_cleaned.txt"
            )
            if os.path.exists(cleaned_file):
                with open(cleaned_file, "r", encoding="utf-8") as f:
                    text = f.read()
            else:
                raw_text = read_file(file_path)
                text = clean_text(raw_text)
                os.makedirs(self.cleaned_cache_dir, exist_ok=True)
                with open(cleaned_file, "w", encoding="utf-8") as f:
                    f.write(text)
        else:
            raw_text = read_file(file_path)
            text = clean_text(raw_text)

        normalized = self.variant_mapper.normalize_text(text)
        char_counts = Counter(normalized)

        return dynasty, dict(char_counts), len(normalized)

    def add_file(self, file_path: str, use_cleaned_cache: bool = True) -> bool:
        file_basename = os.path.basename(file_path)
        checksum = get_file_checksum(file_path)

        dynasty = self.extract_dynasty_from_filename(file_path)

        if file_basename in self.dynasty_file_checksums[dynasty]:
            if self.dynasty_file_checksums[dynasty][file_basename] == checksum:
                return False

        dynasty, char_counts, total = self.count_file(file_path, use_cleaned_cache)

        if file_basename in self.dynasty_file_checksums[dynasty]:
            old_checksum = self.dynasty_file_checksums[dynasty][file_basename]
            if old_checksum != checksum:
                self._remove_file_stats(dynasty, file_basename)

        for char, count in char_counts.items():
            self.dynasty_freqs[dynasty][char] += count
        self.dynasty_total_chars[dynasty] += total

        self.dynasty_file_checksums[dynasty][file_basename] = checksum
        self.dynasty_file_info[dynasty].append({
            "filename": file_basename,
            "checksum": checksum,
            "total_chars": total,
            "unique_chars": len(char_counts),
            "char_counts": char_counts
        })

        return True

    def _remove_file_stats(self, dynasty: str, filename: str):
        if dynasty not in self.dynasty_file_info:
            return

        found_info = None
        for info in self.dynasty_file_info[dynasty]:
            if info["filename"] == filename:
                found_info = info
                self.dynasty_total_chars[dynasty] -= info["total_chars"]
                self.dynasty_file_info[dynasty].remove(info)
                break

        if found_info and "char_counts" in found_info:
            char_counts = found_info["char_counts"]
            for char, count in char_counts.items():
                if char in self.dynasty_freqs[dynasty]:
                    self.dynasty_freqs[dynasty][char] -= count
                    if self.dynasty_freqs[dynasty][char] <= 0:
                        del self.dynasty_freqs[dynasty][char]

        if filename in self.dynasty_file_checksums[dynasty]:
            del self.dynasty_file_checksums[dynasty][filename]

    def add_directory(self, dir_path: str, use_cleaned_cache: bool = True) -> dict:
        dir_path = Path(dir_path)
        txt_files = sorted(dir_path.glob("*.txt"))

        added = 0
        skipped = 0
        errors = 0

        for txt_file in txt_files:
            try:
                is_new = self.add_file(str(txt_file), use_cleaned_cache)
                if is_new:
                    added += 1
                else:
                    skipped += 1
            except Exception as e:
                errors += 1
                print(f"处理文件 {txt_file} 失败: {e}")

        self._save_cache()

        return {
            "total": len(txt_files),
            "added": added,
            "skipped": skipped,
            "errors": errors
        }

    def get_dynasty_frequency(self, dynasty: str, char: str) -> int:
        return self.dynasty_freqs.get(dynasty, {}).get(char, 0)

    def get_dynasty_total(self, dynasty: str) -> int:
        return self.dynasty_total_chars.get(dynasty, 0)

    def get_char_frequency_across_dynasties(self, char: str) -> Dict[str, int]:
        result = {}
        for dynasty in self.get_sorted_dynasties():
            result[dynasty] = self.get_dynasty_frequency(dynasty, char)
        return result

    def get_char_frequency_ratio(self, char: str, dynasty: str) -> float:
        total = self.get_dynasty_total(dynasty)
        if total == 0:
            return 0.0
        return self.get_dynasty_frequency(dynasty, char) / total

    def get_char_ratio_across_dynasties(self, char: str) -> Dict[str, float]:
        result = {}
        for dynasty in self.get_sorted_dynasties():
            result[dynasty] = self.get_char_frequency_ratio(char, dynasty)
        return result

    def get_sorted_dynasties(self) -> List[str]:
        existing = [d for d in self.dynasty_order.keys() if d in self.dynasty_freqs]
        existing.sort(key=lambda d: self.dynasty_order.get(d, 999))
        return existing

    def get_all_dynasties(self) -> List[str]:
        all_dynasties = list(self.dynasty_order.keys())
        all_dynasties.sort(key=lambda d: self.dynasty_order.get(d, 999))
        return all_dynasties

    def get_top_chars(self, dynasty: str, top_n: int = 100,
                      category: str = None) -> List[Tuple[str, int]]:
        if dynasty not in self.dynasty_freqs:
            return []

        freqs = self.dynasty_freqs[dynasty]

        if category:
            filtered = {}
            for char, count in freqs.items():
                if self.variant_mapper.get_category(char) == category:
                    filtered[char] = count
            freqs = filtered

        sorted_chars = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
        return sorted_chars[:top_n]

    def to_dataframe(self) -> pd.DataFrame:
        dynasties = self.get_sorted_dynasties()
        all_chars = set()
        for d in dynasties:
            all_chars.update(self.dynasty_freqs[d].keys())

        data = {"char": sorted(all_chars)}
        for d in dynasties:
            data[d] = [self.dynasty_freqs[d].get(c, 0) for c in data["char"]]

        df = pd.DataFrame(data)
        return df

    def to_frequency_dataframe(self) -> pd.DataFrame:
        df = self.to_dataframe()
        freq_df = df.copy()
        dynasties = self.get_sorted_dynasties()
        for d in dynasties:
            total = self.dynasty_total_chars.get(d, 0)
            if total > 0:
                freq_df[d] = freq_df[d] / total
            else:
                freq_df[d] = 0.0
        return freq_df

    def get_summary(self) -> dict:
        dynasties = self.get_sorted_dynasties()
        summary = {}
        for d in dynasties:
            total = self.dynasty_total_chars.get(d, 0)
            unique = len(self.dynasty_freqs.get(d, {}))
            file_count = len(self.dynasty_file_info.get(d, []))

            freqs = self.dynasty_freqs.get(d, {})
            common_count = 0
            rare_count = 0
            for char, cnt in freqs.items():
                if self.variant_mapper.is_common_char(char):
                    common_count += cnt
                elif self.variant_mapper.is_rare_char(char):
                    rare_count += cnt

            summary[d] = {
                "total_chars": total,
                "unique_chars": unique,
                "file_count": file_count,
                "common_count": common_count,
                "rare_count": rare_count,
            }
        return summary

    def save_cache(self):
        self._save_cache()

    def clear_cache(self):
        self.dynasty_freqs.clear()
        self.dynasty_total_chars.clear()
        self.dynasty_file_checksums.clear()
        self.dynasty_file_info.clear()
        if os.path.exists(self.frequency_cache_file):
            os.remove(self.frequency_cache_file)


def create_counter(
    dynasty_config_path: str = None,
    variant_mapper: VariantCharMapper = None,
    cleaned_cache_dir: str = None,
    frequency_cache_file: str = None,
) -> DynastyFrequencyCounter:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import (
        DYNASTY_CONFIG_FILE,
        VARIANT_CHARS_FILE,
        CLEANED_CACHE_DIR,
        FREQUENCY_CACHE_FILE,
    )

    if dynasty_config_path is None:
        dynasty_config_path = DYNASTY_CONFIG_FILE
    if variant_mapper is None:
        variant_mapper = create_mapper(VARIANT_CHARS_FILE)
    if cleaned_cache_dir is None:
        cleaned_cache_dir = CLEANED_CACHE_DIR
    if frequency_cache_file is None:
        frequency_cache_file = FREQUENCY_CACHE_FILE

    return DynastyFrequencyCounter(
        dynasty_config_path, variant_mapper, cleaned_cache_dir, frequency_cache_file
    )


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import RAW_DATA_DIR, ensure_dirs

    ensure_dirs()
    counter = create_counter()
    result = counter.add_directory(RAW_DATA_DIR)
    print(f"统计结果: {result}")
    print(f"摘要: {counter.get_summary()}")
