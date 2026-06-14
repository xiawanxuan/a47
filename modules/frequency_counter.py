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
                 cleaned_cache_dir: str, frequency_cache_file: str,
                 region_config_path: str = None):
        self.dynasty_config_path = dynasty_config_path
        self.region_config_path = region_config_path
        self.variant_mapper = variant_mapper
        self.cleaned_cache_dir = cleaned_cache_dir
        self.frequency_cache_file = frequency_cache_file

        self.dynasties: List[dict] = []
        self.dynasty_order: Dict[str, int] = {}
        self.dynasty_extract_regex: str = ""
        self.unknown_dynasty_name: str = "未知"

        self.regions: List[dict] = []
        self.region_order: Dict[str, int] = {}
        self.region_area: Dict[str, str] = {}
        self.areas: List[str] = []
        self.region_extract_regex: str = ""
        self.legacy_extract_regex: str = ""
        self.unknown_region_name: str = "未知"

        self._load_dynasty_config()
        if region_config_path:
            self._load_region_config()

        self.dynasty_freqs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.dynasty_total_chars: Dict[str, int] = defaultdict(int)
        self.dynasty_file_checksums: Dict[str, Dict[str, str]] = defaultdict(dict)
        self.dynasty_file_info: Dict[str, List[dict]] = defaultdict(list)

        self.region_freqs: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.region_total_chars: Dict[str, int] = defaultdict(int)
        self.dynasty_region_freqs: Dict[Tuple[str, str], Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.dynasty_region_total: Dict[Tuple[str, str], int] = defaultdict(int)

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

    def _load_region_config(self):
        if not self.region_config_path or not os.path.exists(self.region_config_path):
            return

        with open(self.region_config_path, "r", encoding="utf-8") as f:
            config = json.load(f)

        self.regions = config.get("regions", [])
        for r in self.regions:
            self.region_order[r["name"]] = r["order"]
            self.region_area[r["name"]] = r["area"]

        self.areas = config.get("areas", [])
        self.unknown_region_name = config.get("unknown_region_name", "未知")

        patterns = config.get("file_patterns", {})
        self.region_extract_regex = patterns.get("region_extract_regex", r"^([^_]+)_([^_]+)_(.+)$")
        self.legacy_extract_regex = patterns.get("legacy_extract_regex", r"^([^_]+)_(.+)$")

    def extract_metadata_from_filename(self, filename: str) -> Tuple[str, str]:
        basename = os.path.basename(filename)
        match = re.match(self.region_extract_regex, basename)
        if match:
            dynasty_name = match.group(1)
            region_name = match.group(2)
            if dynasty_name in self.dynasty_order and region_name in self.region_order:
                return dynasty_name, region_name

        match = re.match(self.legacy_extract_regex, basename)
        if match:
            dynasty_name = match.group(1)
            if dynasty_name in self.dynasty_order:
                return dynasty_name, self.unknown_region_name

        return self.unknown_dynasty_name, self.unknown_region_name

    def _load_cache(self):
        if os.path.exists(self.frequency_cache_file):
            try:
                with open(self.frequency_cache_file, "rb") as f:
                    cache = pickle.load(f)
                raw_freqs = cache.get("freqs", {})
                normalized_freqs = {}
                for dynasty, char_dict in raw_freqs.items():
                    normalized = self.variant_mapper.map_frequency_dict(dict(char_dict))
                    normalized_freqs[dynasty] = defaultdict(int, normalized)
                self.dynasty_freqs = defaultdict(lambda: defaultdict(int), normalized_freqs)
                self.dynasty_total_chars = defaultdict(int, cache.get("total_chars", {}))
                self.dynasty_file_checksums = defaultdict(dict, cache.get("checksums", {}))
                self.dynasty_file_info = defaultdict(list, cache.get("file_info", {}))

                region_freqs_raw = cache.get("region_freqs", {})
                normalized_region = {}
                for region, char_dict in region_freqs_raw.items():
                    normalized = self.variant_mapper.map_frequency_dict(dict(char_dict))
                    normalized_region[region] = defaultdict(int, normalized)
                self.region_freqs = defaultdict(lambda: defaultdict(int), normalized_region)
                self.region_total_chars = defaultdict(int, cache.get("region_total_chars", {}))

                dr_freqs_raw = cache.get("dynasty_region_freqs", {})
                normalized_dr = {}
                for key_str, char_dict in dr_freqs_raw.items():
                    dynasty, region = eval(key_str)
                    normalized = self.variant_mapper.map_frequency_dict(dict(char_dict))
                    normalized_dr[(dynasty, region)] = defaultdict(int, normalized)
                self.dynasty_region_freqs = defaultdict(lambda: defaultdict(int), normalized_dr)
                dr_total_raw = cache.get("dynasty_region_total", {})
                normalized_dr_total = {}
                for key_str, val in dr_total_raw.items():
                    dynasty, region = eval(key_str)
                    normalized_dr_total[(dynasty, region)] = val
                self.dynasty_region_total = defaultdict(int, normalized_dr_total)
            except Exception:
                pass

    def _save_cache(self):
        dr_freqs_serializable = {}
        for (d, r), v in self.dynasty_region_freqs.items():
            dr_freqs_serializable[str((d, r))] = dict(v)
        dr_total_serializable = {}
        for (d, r), v in self.dynasty_region_total.items():
            dr_total_serializable[str((d, r))] = v

        cache = {
            "freqs": dict(self.dynasty_freqs),
            "total_chars": dict(self.dynasty_total_chars),
            "checksums": dict(self.dynasty_file_checksums),
            "file_info": dict(self.dynasty_file_info),
            "region_freqs": dict(self.region_freqs),
            "region_total_chars": dict(self.region_total_chars),
            "dynasty_region_freqs": dr_freqs_serializable,
            "dynasty_region_total": dr_total_serializable,
        }
        os.makedirs(os.path.dirname(self.frequency_cache_file), exist_ok=True)
        with open(self.frequency_cache_file, "wb") as f:
            pickle.dump(cache, f)

    def extract_dynasty_from_filename(self, filename: str) -> str:
        dynasty, _ = self.extract_metadata_from_filename(filename)
        return dynasty

    def extract_region_from_filename(self, filename: str) -> str:
        _, region = self.extract_metadata_from_filename(filename)
        return region

    def count_file(self, file_path: str, use_cleaned_cache: bool = True) -> Tuple[str, str, Dict[str, int], int]:
        dynasty, region = self.extract_metadata_from_filename(file_path)
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
        raw_counts = Counter(normalized)
        char_counts = self.variant_mapper.map_frequency_dict(dict(raw_counts))

        return dynasty, region, char_counts, len(normalized)

    def add_file(self, file_path: str, use_cleaned_cache: bool = True) -> bool:
        file_basename = os.path.basename(file_path)
        checksum = get_file_checksum(file_path)

        dynasty, region = self.extract_metadata_from_filename(file_path)

        if file_basename in self.dynasty_file_checksums[dynasty]:
            if self.dynasty_file_checksums[dynasty][file_basename] == checksum:
                return False

        dynasty, region, char_counts, total = self.count_file(file_path, use_cleaned_cache)

        if file_basename in self.dynasty_file_checksums[dynasty]:
            old_checksum = self.dynasty_file_checksums[dynasty][file_basename]
            if old_checksum != checksum:
                self._remove_file_stats(dynasty, file_basename)

        for char, count in char_counts.items():
            self.dynasty_freqs[dynasty][char] += count
            self.region_freqs[region][char] += count
            self.dynasty_region_freqs[(dynasty, region)][char] += count
        self.dynasty_total_chars[dynasty] += total
        self.region_total_chars[region] += total
        self.dynasty_region_total[(dynasty, region)] += total

        self.dynasty_file_checksums[dynasty][file_basename] = checksum
        self.dynasty_file_info[dynasty].append({
            "filename": file_basename,
            "checksum": checksum,
            "region": region,
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
                region = info.get("region", self.unknown_region_name)
                self.region_total_chars[region] -= info["total_chars"]
                self.dynasty_region_total[(dynasty, region)] -= info["total_chars"]
                self.dynasty_file_info[dynasty].remove(info)
                break

        if found_info and "char_counts" in found_info:
            char_counts = found_info["char_counts"]
            region = found_info.get("region", self.unknown_region_name)
            for char, count in char_counts.items():
                if char in self.dynasty_freqs[dynasty]:
                    self.dynasty_freqs[dynasty][char] -= count
                    if self.dynasty_freqs[dynasty][char] <= 0:
                        del self.dynasty_freqs[dynasty][char]
                if char in self.region_freqs[region]:
                    self.region_freqs[region][char] -= count
                    if self.region_freqs[region][char] <= 0:
                        del self.region_freqs[region][char]
                key = (dynasty, region)
                if char in self.dynasty_region_freqs[key]:
                    self.dynasty_region_freqs[key][char] -= count
                    if self.dynasty_region_freqs[key][char] <= 0:
                        del self.dynasty_region_freqs[key][char]

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
        standard = self.variant_mapper.to_standard(char)
        return self.dynasty_freqs.get(dynasty, {}).get(standard, 0)

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

        freqs = self.variant_mapper.map_frequency_dict(dict(self.dynasty_freqs[dynasty]))

        if category:
            filtered = {}
            for char, count in freqs.items():
                if self.variant_mapper.standard_category.get(char, "未分类") == category:
                    filtered[char] = count
            freqs = filtered

        sorted_chars = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
        return sorted_chars[:top_n]

    def to_dataframe(self) -> pd.DataFrame:
        dynasties = self.get_sorted_dynasties()
        normalized_per_dynasty = {}
        all_chars = set()
        for d in dynasties:
            norm = self.variant_mapper.map_frequency_dict(dict(self.dynasty_freqs.get(d, {})))
            normalized_per_dynasty[d] = norm
            all_chars.update(norm.keys())

        data = {"char": sorted(all_chars)}
        for d in dynasties:
            data[d] = [normalized_per_dynasty[d].get(c, 0) for c in data["char"]]

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
            raw_freqs = dict(self.dynasty_freqs.get(d, {}))
            freqs = self.variant_mapper.map_frequency_dict(raw_freqs)
            unique = len(freqs)
            file_count = len(self.dynasty_file_info.get(d, []))

            common, rare = self.variant_mapper.split_by_category(freqs)
            common_count = sum(common.values())
            rare_count = sum(rare.values())

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
        self.region_freqs.clear()
        self.region_total_chars.clear()
        self.dynasty_region_freqs.clear()
        self.dynasty_region_total.clear()
        if os.path.exists(self.frequency_cache_file):
            os.remove(self.frequency_cache_file)

    def get_sorted_regions(self) -> List[str]:
        existing = [r for r in self.region_order.keys() if r in self.region_freqs]
        existing.sort(key=lambda r: self.region_order.get(r, 999))
        return existing

    def get_all_regions(self) -> List[str]:
        all_regions = list(self.region_order.keys())
        all_regions.sort(key=lambda r: self.region_order.get(r, 999))
        return all_regions

    def get_regions_by_area(self) -> Dict[str, List[str]]:
        result = defaultdict(list)
        for region in self.get_sorted_regions():
            area = self.region_area.get(region, "未知")
            result[area].append(region)
        return dict(result)

    def get_region_frequency(self, region: str, char: str) -> int:
        standard = self.variant_mapper.to_standard(char)
        return self.region_freqs.get(region, {}).get(standard, 0)

    def get_region_total(self, region: str) -> int:
        return self.region_total_chars.get(region, 0)

    def get_dynasty_region_frequency(self, dynasty: str, region: str, char: str) -> int:
        standard = self.variant_mapper.to_standard(char)
        return self.dynasty_region_freqs.get((dynasty, region), {}).get(standard, 0)

    def get_dynasty_region_total(self, dynasty: str, region: str) -> int:
        return self.dynasty_region_total.get((dynasty, region), 0)

    def get_char_frequency_across_regions(self, char: str) -> Dict[str, int]:
        result = {}
        for region in self.get_sorted_regions():
            result[region] = self.get_region_frequency(region, char)
        return result

    def get_char_ratio_across_regions(self, char: str) -> Dict[str, float]:
        result = {}
        for region in self.get_sorted_regions():
            total = self.get_region_total(region)
            if total == 0:
                result[region] = 0.0
            else:
                result[region] = self.get_region_frequency(region, char) / total
        return result

    def get_region_top_chars(self, region: str, top_n: int = 100,
                             category: str = None) -> List[Tuple[str, int]]:
        if region not in self.region_freqs:
            return []

        freqs = self.variant_mapper.map_frequency_dict(dict(self.region_freqs[region]))

        if category:
            filtered = {}
            for char, count in freqs.items():
                if self.variant_mapper.standard_category.get(char, "未分类") == category:
                    filtered[char] = count
            freqs = filtered

        sorted_chars = sorted(freqs.items(), key=lambda x: x[1], reverse=True)
        return sorted_chars[:top_n]

    def get_region_summary(self) -> dict:
        regions = self.get_sorted_regions()
        summary = {}
        for r in regions:
            total = self.region_total_chars.get(r, 0)
            raw_freqs = dict(self.region_freqs.get(r, {}))
            freqs = self.variant_mapper.map_frequency_dict(raw_freqs)
            unique = len(freqs)
            file_count = sum(
                1 for d in self.dynasty_file_info
                for info in self.dynasty_file_info[d]
                if info.get("region") == r
            )

            common, rare = self.variant_mapper.split_by_category(freqs)
            common_count = sum(common.values())
            rare_count = sum(rare.values())

            summary[r] = {
                "total_chars": total,
                "unique_chars": unique,
                "file_count": file_count,
                "area": self.region_area.get(r, "未知"),
                "common_count": common_count,
                "rare_count": rare_count,
            }
        return summary

    def get_dynasty_region_combined(self) -> List[Tuple[str, str]]:
        keys = [k for k in self.dynasty_region_freqs.keys() if self.dynasty_region_total[k] > 0]
        keys.sort(key=lambda x: (self.dynasty_order.get(x[0], 999), self.region_order.get(x[1], 999)))
        return keys

    def to_region_dataframe(self) -> pd.DataFrame:
        regions = self.get_sorted_regions()
        normalized_per_region = {}
        all_chars = set()
        for r in regions:
            norm = self.variant_mapper.map_frequency_dict(dict(self.region_freqs.get(r, {})))
            normalized_per_region[r] = norm
            all_chars.update(norm.keys())

        data = {"char": sorted(all_chars)}
        for r in regions:
            data[r] = [normalized_per_region[r].get(c, 0) for c in data["char"]]

        df = pd.DataFrame(data)
        return df

    def to_region_frequency_dataframe(self) -> pd.DataFrame:
        df = self.to_region_dataframe()
        freq_df = df.copy()
        regions = self.get_sorted_regions()
        for r in regions:
            total = self.region_total_chars.get(r, 0)
            if total > 0:
                freq_df[r] = freq_df[r] / total
            else:
                freq_df[r] = 0.0
        return freq_df

    def to_dynasty_region_heatmap_data(self, char: str) -> pd.DataFrame:
        dynasties = self.get_sorted_dynasties()
        regions = self.get_sorted_regions()

        data = []
        for d in dynasties:
            row = {}
            row["dynasty"] = d
            for r in regions:
                total = self.get_dynasty_region_total(d, r)
                if total == 0:
                    row[r] = 0.0
                else:
                    row[r] = self.get_dynasty_region_frequency(d, r, char) / total
            data.append(row)

        df = pd.DataFrame(data).set_index("dynasty")
        return df

    def to_region_heatmap_data(self, char: str) -> pd.DataFrame:
        regions = self.get_sorted_regions()
        data = []
        for r in regions:
            total = self.get_region_total(r)
            freq = self.get_region_frequency(r, char)
            ratio = freq / total if total > 0 else 0.0
            data.append({
                "region": r,
                "area": self.region_area.get(r, "未知"),
                "frequency": freq,
                "total": total,
                "ratio": ratio
            })
        df = pd.DataFrame(data).set_index("region")
        return df

    def has_region_data(self) -> bool:
        return len(self.region_freqs) > 0


def create_counter(
    dynasty_config_path: str = None,
    variant_mapper: VariantCharMapper = None,
    cleaned_cache_dir: str = None,
    frequency_cache_file: str = None,
    region_config_path: str = None,
) -> DynastyFrequencyCounter:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import (
        DYNASTY_CONFIG_FILE,
        VARIANT_CHARS_FILE,
        CLEANED_CACHE_DIR,
        FREQUENCY_CACHE_FILE,
        REGION_CONFIG_FILE,
    )

    if dynasty_config_path is None:
        dynasty_config_path = DYNASTY_CONFIG_FILE
    if variant_mapper is None:
        variant_mapper = create_mapper(VARIANT_CHARS_FILE)
    if cleaned_cache_dir is None:
        cleaned_cache_dir = CLEANED_CACHE_DIR
    if frequency_cache_file is None:
        frequency_cache_file = FREQUENCY_CACHE_FILE
    if region_config_path is None:
        region_config_path = REGION_CONFIG_FILE

    return DynastyFrequencyCounter(
        dynasty_config_path, variant_mapper, cleaned_cache_dir,
        frequency_cache_file, region_config_path
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
    if counter.has_region_data():
        print(f"地域摘要: {counter.get_region_summary()}")

