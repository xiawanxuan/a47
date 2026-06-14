#!/usr/bin/env python3
import argparse
import os
import sys


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from config.paths_config import (
    ensure_dirs,
    RAW_DATA_DIR,
    CLEANED_CACHE_DIR,
    EXCEL_OUTPUT_DIR,
    PDF_OUTPUT_DIR,
    FIGURES_OUTPUT_DIR,
)
from modules.text_cleaner import batch_clean_files
from modules.variant_mapper import create_mapper
from modules.frequency_counter import create_counter
from modules.visualization import create_visualizer
from modules.report_generator import create_report_generator


def cmd_clean(args):
    print("=" * 50)
    print("古籍文本清洗任务")
    print("=" * 50)

    input_dir = args.input or RAW_DATA_DIR
    output_dir = args.output or CLEANED_CACHE_DIR

    results = batch_clean_files(input_dir, output_dir)

    success = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]

    print(f"\n处理完成：成功 {len(success)} 个，失败 {len(failed)} 个")
    for r in success:
        print(f"  [OK] {os.path.basename(r['original_file'])}: "
              f"{r['original_length']} -> {r['cleaned_length']} 字")
    for r in failed:
        print(f"  [FAIL] {os.path.basename(r['original_file'])}: {r['status']}")


def cmd_stats(args):
    print("=" * 50)
    print("字频统计任务")
    print("=" * 50)

    counter = create_counter()

    if args.clear_cache:
        counter.clear_cache()
        print("已清除历史缓存")

    input_dir = args.input or RAW_DATA_DIR
    result = counter.add_directory(input_dir)

    print(f"\n统计完成：总计 {result['total']} 个文件")
    print(f"  新增: {result['added']}")
    print(f"  跳过(缓存): {result['skipped']}")
    print(f"  错误: {result['errors']}")

    summary = counter.get_summary()
    print("\n各朝代统计摘要：")
    for dynasty, s in summary.items():
        print(f"  {dynasty}: {s['file_count']} 文件, "
              f"{s['total_chars']:,} 总字, {s['unique_chars']:,} 不重复字")

    if args.top:
        for dynasty in counter.get_sorted_dynasties():
            top_chars = counter.get_top_chars(dynasty, top_n=args.top)
            if top_chars:
                print(f"\n  {dynasty} Top{args.top}: "
                      f"{', '.join([f'{c}({n})' for c, n in top_chars[:10]])}")


def cmd_plot(args):
    print("=" * 50)
    print("可视化任务")
    print("=" * 50)

    counter = create_counter()
    visualizer = create_visualizer(counter=counter)

    charts = {}

    if args.all:
        charts = visualizer.generate_all_charts(args.chars)
    elif args.chars:
        for char in args.chars:
            path = visualizer.plot_char_trend(char, use_ratio=not args.count)
            charts[char] = path
        if len(args.chars) >= 2:
            charts["multi"] = visualizer.plot_multiple_chars_trend(
                args.chars, use_ratio=not args.count
            )
    else:
        charts["distribution"] = visualizer.plot_dynasty_distribution()
        charts["category"] = visualizer.plot_category_comparison()

    print(f"\n生成图表 {len(charts)} 个：")
    for name, path in charts.items():
        if path:
            print(f"  {name}: {os.path.basename(path)}")


def cmd_report(args):
    print("=" * 50)
    print("研究报告生成任务")
    print("=" * 50)

    counter = create_counter()

    input_dir = args.input or RAW_DATA_DIR
    counter.add_directory(input_dir)

    generator = create_report_generator(counter=counter)

    if args.excel:
        excel_path = generator.generate_excel_report()
        print(f"\nExcel 报告已生成: {excel_path}")

    if args.pdf:
        pdf_path = generator.generate_pdf_report(target_chars=args.chars)
        print(f"PDF 报告已生成: {pdf_path}")

    if not args.excel and not args.pdf:
        results = generator.generate_full_report(target_chars=args.chars)
        print(f"\n报告生成完成：")
        print(f"  Excel: {results['excel']}")
        print(f"  PDF: {results['pdf']}")


def cmd_all(args):
    print("=" * 50)
    print("一键全流程分析")
    print("=" * 50)

    ensure_dirs()

    print("\n[1/4] 文本清洗...")
    batch_clean_files(RAW_DATA_DIR, CLEANED_CACHE_DIR)

    print("\n[2/4] 字频统计...")
    counter = create_counter()
    if args.clear_cache:
        counter.clear_cache()
    stats = counter.add_directory(RAW_DATA_DIR)
    print(f"  新增 {stats['added']} 个文件，跳过 {stats['skipped']} 个")

    print("\n[3/4] 可视化生成...")
    visualizer = create_visualizer(counter=counter)
    charts = visualizer.generate_all_charts(args.chars)
    print(f"  生成 {len(charts)} 张图表")

    print("\n[4/4] 报告生成...")
    generator = create_report_generator(counter=counter, visualizer=visualizer)
    results = generator.generate_full_report(target_chars=args.chars)

    print("\n" + "=" * 50)
    print("全部任务完成！")
    print("=" * 50)
    print(f"\nExcel 报告: {results['excel']}")
    print(f"PDF 报告:   {results['pdf']}")
    print(f"图表目录:   {FIGURES_OUTPUT_DIR}")

    summary = counter.get_summary()
    print(f"\n统计总览：")
    total_chars = sum(s["total_chars"] for s in summary.values())
    total_files = sum(s["file_count"] for s in summary.values())
    print(f"  朝代数: {len(summary)}")
    print(f"  文件数: {total_files}")
    print(f"  总字数: {total_chars:,}")


def main():
    parser = argparse.ArgumentParser(
        description="古籍文本字频分析系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py all                           # 一键执行全流程
  python main.py clean                         # 仅执行文本清洗
  python main.py stats --top 10                # 字频统计并显示 Top10
  python main.py plot --chars 之 乎 者 也       # 绘制指定汉字趋势图
  python main.py report --excel --pdf          # 生成 Excel 和 PDF 报告
  python main.py all --chars 之 乎 者 也        # 全流程并分析指定汉字
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="子命令")

    parser_clean = subparsers.add_parser("clean", help="文本清洗")
    parser_clean.add_argument("--input", help="输入目录")
    parser_clean.add_argument("--output", help="输出目录")
    parser_clean.set_defaults(func=cmd_clean)

    parser_stats = subparsers.add_parser("stats", help="字频统计")
    parser_stats.add_argument("--input", help="输入目录")
    parser_stats.add_argument("--top", type=int, default=0, help="显示Top N字")
    parser_stats.add_argument("--clear-cache", action="store_true",
                              help="清除缓存重新计算")
    parser_stats.set_defaults(func=cmd_stats)

    parser_plot = subparsers.add_parser("plot", help="可视化")
    parser_plot.add_argument("--chars", nargs="+", help="要分析的汉字列表")
    parser_plot.add_argument("--all", action="store_true", help="生成所有图表")
    parser_plot.add_argument("--count", action="store_true",
                             help="使用绝对频次而非频率")
    parser_plot.set_defaults(func=cmd_plot)

    parser_report = subparsers.add_parser("report", help="生成报告")
    parser_report.add_argument("--input", help="输入目录")
    parser_report.add_argument("--excel", action="store_true", help="生成Excel报告")
    parser_report.add_argument("--pdf", action="store_true", help="生成PDF报告")
    parser_report.add_argument("--chars", nargs="+", help="重点分析汉字")
    parser_report.set_defaults(func=cmd_report)

    parser_all = subparsers.add_parser("all", help="一键全流程")
    parser_all.add_argument("--chars", nargs="+", help="重点分析汉字")
    parser_all.add_argument("--clear-cache", action="store_true",
                            help="清除缓存重新计算")
    parser_all.set_defaults(func=cmd_all)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    ensure_dirs()
    args.func(args)


if __name__ == "__main__":
    main()
