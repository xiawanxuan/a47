import csv
import os
from typing import Dict, List, Tuple, Optional


class VariantCharMapper:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.variant_to_standard: Dict[str, str] = {}
        self.standard_to_variants: Dict[str, List[str]] = {}
        self.standard_category: Dict[str, str] = {}
        self._load_mapping()

    def _load_mapping(self):
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"异体字对照表不存在: {self.csv_path}")

        all_rows = []
        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                standard = row["standard"].strip()
                variants_str = row["variants"].strip()
                category = row["category"].strip() if "category" in row else "通用字"

                if not standard:
                    continue

                variants = [v.strip() for v in variants_str.split("|") if v.strip()]
                all_rows.append((standard, variants, category))

        for standard, variants, category in all_rows:
            self.standard_to_variants[standard] = []
            self.standard_category[standard] = category
            self.variant_to_standard[standard] = standard

        for standard, variants, category in all_rows:
            valid_variants = []
            for v in variants:
                if v == standard:
                    continue
                if v in self.standard_to_variants:
                    continue
                if v in self.variant_to_standard and self.variant_to_standard[v] != standard:
                    prev_std = self.variant_to_standard[v]
                    if prev_std in self.standard_to_variants:
                        if v in self.standard_to_variants[prev_std]:
                            self.standard_to_variants[prev_std].remove(v)
                self.variant_to_standard[v] = standard
                valid_variants.append(v)
            self.standard_to_variants[standard] = valid_variants

    def to_standard(self, char: str) -> str:
        return self.variant_to_standard.get(char, char)

    def normalize_text(self, text: str) -> str:
        result = []
        for ch in text:
            result.append(self.to_standard(ch))
        return "".join(result)

    def is_variant(self, char: str) -> bool:
        return char in self.variant_to_standard and char != self.variant_to_standard[char]

    def is_standard(self, char: str) -> bool:
        return char in self.standard_to_variants

    def get_category(self, char: str) -> str:
        standard = self.to_standard(char)
        return self.standard_category.get(standard, "未分类")

    def is_common_char(self, char: str) -> bool:
        return self.get_category(char) == "通用字"

    def is_rare_char(self, char: str) -> bool:
        return self.get_category(char) == "生僻字"

    def get_all_standard_chars(self) -> List[str]:
        return list(self.standard_to_variants.keys())

    def get_variants_of(self, standard_char: str) -> List[str]:
        return self.standard_to_variants.get(standard_char, [])

    def count_variant_occurrences(self, text: str) -> Dict[str, int]:
        from collections import Counter
        counter = Counter()
        for ch in text:
            if self.is_variant(ch):
                counter[ch] += 1
        return dict(counter)

    def map_frequency_dict(self, freq_dict: Dict[str, int]) -> Dict[str, int]:
        from collections import defaultdict
        result = defaultdict(int)
        for char, count in freq_dict.items():
            standard = self.to_standard(char)
            result[standard] += count
        return dict(result)

    def split_by_category(self, freq_dict: Dict[str, int]) -> Tuple[Dict[str, int], Dict[str, int]]:
        mapped = self.map_frequency_dict(freq_dict)
        common = {}
        rare = {}
        for char, count in mapped.items():
            cat = self.standard_category.get(char, "未分类")
            if cat == "通用字":
                common[char] = count
            elif cat == "生僻字":
                rare[char] = count
        return common, rare

    def get_stats(self, text: str = None, freq_dict: Dict[str, int] = None) -> dict:
        if freq_dict is None and text is not None:
            from collections import Counter
            freq_dict = dict(Counter(text))
        elif freq_dict is None:
            freq_dict = {}

        mapped = self.map_frequency_dict(freq_dict)
        common, rare = self.split_by_category(mapped)

        return {
            "total_unique_chars": len(freq_dict),
            "mapped_unique_chars": len(mapped),
            "common_unique_chars": len(common),
            "rare_unique_chars": len(rare),
            "common_count": sum(common.values()),
            "rare_count": sum(rare.values()),
        }


def create_mapper(csv_path: str = None) -> VariantCharMapper:
    if csv_path is None:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config.paths_config import VARIANT_CHARS_FILE
        csv_path = VARIANT_CHARS_FILE
    return VariantCharMapper(csv_path)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import VARIANT_CHARS_FILE

    mapper = VariantCharMapper(VARIANT_CHARS_FILE)

    test_text = "無論是天兲還是地墬，都有其道衟。"
    print(f"原文: {test_text}")
    print(f"归一化: {mapper.normalize_text(test_text)}")
    print(f"统计: {mapper.get_stats(test_text)}")
