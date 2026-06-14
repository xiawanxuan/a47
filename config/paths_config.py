import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RAW_DATA_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DATA_DIR = os.path.join(BASE_DIR, "data", "processed")

OUTPUT_DIR = os.path.join(BASE_DIR, "output")
EXCEL_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "excel")
PDF_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "pdf")
FIGURES_OUTPUT_DIR = os.path.join(OUTPUT_DIR, "figures")

CONFIG_DIR = os.path.join(BASE_DIR, "config")
VARIANT_CHARS_FILE = os.path.join(CONFIG_DIR, "variant_chars.csv")
DYNASTY_CONFIG_FILE = os.path.join(CONFIG_DIR, "dynasty_config.json")

FREQUENCY_CACHE_FILE = os.path.join(PROCESSED_DATA_DIR, "frequency_cache.pkl")
CLEANED_CACHE_DIR = os.path.join(PROCESSED_DATA_DIR, "cleaned")


def ensure_dirs():
    for d in [
        RAW_DATA_DIR,
        PROCESSED_DATA_DIR,
        EXCEL_OUTPUT_DIR,
        PDF_OUTPUT_DIR,
        FIGURES_OUTPUT_DIR,
        CLEANED_CACHE_DIR,
    ]:
        os.makedirs(d, exist_ok=True)
