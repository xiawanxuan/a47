import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("开始测试...")
print(f"Python 版本: {sys.version}")

try:
    import pandas as pd
    print(f"✓ pandas: {pd.__version__}")
except ImportError as e:
    print(f"✗ pandas: {e}")

try:
    import matplotlib
    print(f"✓ matplotlib: {matplotlib.__version__}")
except ImportError as e:
    print(f"✗ matplotlib: {e}")

try:
    import openpyxl
    print(f"✓ openpyxl: {openpyxl.__version__}")
except ImportError as e:
    print(f"✗ openpyxl: {e}")

try:
    import reportlab
    print(f"✓ reportlab: {reportlab.__version__}")
except ImportError as e:
    print(f"✗ reportlab: {e}")

try:
    from PIL import Image
    print(f"✓ Pillow 可用")
except ImportError as e:
    print(f"✗ Pillow: {e}")

print("\n导入模块测试...")
try:
    from config.paths_config import ensure_dirs, RAW_DATA_DIR
    ensure_dirs()
    print(f"✓ 路径配置模块加载成功，原始数据目录: {RAW_DATA_DIR}")
except Exception as e:
    print(f"✗ 路径配置模块: {e}")

try:
    from modules.text_cleaner import clean_text, read_file
    test_text = "你好，世界！这是测试。"
    cleaned = clean_text(test_text)
    print(f"✓ 文本清洗模块: '{test_text}' -> '{cleaned}'")
except Exception as e:
    print(f"✗ 文本清洗模块: {e}")

try:
    from modules.variant_mapper import create_mapper
    mapper = create_mapper()
    test = "無論天兲"
    result = mapper.normalize_text(test)
    print(f"✓ 异体字映射模块: '{test}' -> '{result}'")
except Exception as e:
    print(f"✗ 异体字映射模块: {e}")
    import traceback
    traceback.print_exc()

try:
    from modules.frequency_counter import create_counter
    counter = create_counter()
    result = counter.add_directory(RAW_DATA_DIR)
    print(f"✓ 字频统计模块: {result}")
    summary = counter.get_summary()
    print(f"  朝代数: {len(summary)}")
    for d, s in list(summary.items())[:3]:
        print(f"    {d}: {s['total_chars']} 字")
except Exception as e:
    print(f"✗ 字频统计模块: {e}")
    import traceback
    traceback.print_exc()

try:
    from modules.visualization import create_visualizer
    visualizer = create_visualizer(counter=counter)
    charts = visualizer.generate_all_charts(["之", "乎", "者", "也"])
    print(f"✓ 可视化模块: 生成 {len(charts)} 张图表")
except Exception as e:
    print(f"✗ 可视化模块: {e}")
    import traceback
    traceback.print_exc()

try:
    from modules.report_generator import create_report_generator
    generator = create_report_generator(counter=counter, visualizer=visualizer)
    excel_path = generator.generate_excel_report()
    print(f"✓ 报告模块 Excel: {excel_path}")
except Exception as e:
    print(f"✗ 报告模块 Excel: {e}")
    import traceback
    traceback.print_exc()

try:
    pdf_path = generator.generate_pdf_report(target_chars=["之", "乎", "者", "也"])
    print(f"✓ 报告模块 PDF: {pdf_path}")
except Exception as e:
    print(f"✗ 报告模块 PDF: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("测试完成！")
print("=" * 50)
