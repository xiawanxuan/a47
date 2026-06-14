import re
import os
import hashlib
from pathlib import Path


CHINESE_CHAR_RANGE = r"\u4e00-\u9fff\u3400-\u4dbf"

PUNCTUATION_PATTERN = re.compile(
    r"[，。！？、；：\"'（）《》【】「」『』〈〉«»"
    r"\s\u3000-\u303f\uff00-\uffef"
    r",\.;:\'\"()\[\]\{\}<>"
    r"【】〖〗〈〉《》「」『』〔〕"
    r"…—·]"
)

DAMAGED_MARK_PATTERN = re.compile(r"[□■△▲▽▼◇◆○●◎☆★◦◘◙◈◉◊◌◍◐◑◒◓◔◕◖◗❏]")

WHITESPACE_PATTERN = re.compile(r"\s+")

INVALID_CHAR_PATTERN = re.compile(
    r"[^\u4e00-\u9fff\u3400-\u4dbf\u2e80-\u2eff\u31c0-\u31ef\u2f00-\u2fdf]"
)

EXCLUDED_SYMBOLS = set("，。！？、；：\"'（）《》【】「」『』〈〉"
                      "\n\r\t ")


def clean_text(raw_text: str) -> str:
    cleaned = DAMAGED_MARK_PATTERN.sub("", raw_text)
    cleaned = PUNCTUATION_PATTERN.sub("", cleaned)
    cleaned = WHITESPACE_PATTERN.sub("", cleaned)
    cleaned = INVALID_CHAR_PATTERN.sub("", cleaned)
    return cleaned


def read_file(file_path: str, encoding: str = "utf-8") -> str:
    encodings_to_try = [encoding, "utf-8", "gbk", "gb18030", "big5", "utf-16"]
    last_error = None
    for enc in encodings_to_try:
        try:
            with open(file_path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError as e:
            last_error = e
            continue
    raise UnicodeDecodeError(
        "utf-8", b"", 0, 1, f"无法解码失败，尝试编码: {encodings_to_try}"
    )


def get_file_checksum(file_path: str) -> str:
    md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()


def batch_clean_files(input_dir: str, output_dir: str) -> list:
    results = []
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(input_path.glob("*.txt"))
    for txt_file in txt_files:
        try:
            raw_text = read_file(str(txt_file))
            cleaned = clean_text(raw_text)
            checksum = get_file_checksum(str(txt_file))

            output_file = output_path / f"{txt_file.stem}_cleaned.txt"
            with open(str(output_file), "w", encoding="utf-8") as f:
                f.write(cleaned)

            results.append({
                "original_file": str(txt_file),
                "cleaned_file": str(output_file),
                "original_length": len(raw_text),
                "cleaned_length": len(cleaned),
                "checksum": checksum,
                "status": "success"
            })
        except Exception as e:
            results.append({
                "original_file": str(txt_file),
                "cleaned_file": None,
                "original_length": 0,
                "cleaned_length": 0,
                "checksum": None,
                "status": f"error: {str(e)}"
            })
    return results


def extract_chars_from_file(file_path: str) -> list:
    cleaned = clean_text(read_file(file_path))
    return list(cleaned)


def char_count(text: str) -> int:
    return len(clean_text(text))


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import RAW_DATA_DIR, CLEANED_CACHE_DIR, ensure_dirs

    ensure_dirs()
    results = batch_clean_files(RAW_DATA_DIR, CLEANED_CACHE_DIR)
    for r in results:
        print(f"{r['original_file']} -> {r['status']}")
