# -*- coding: utf-8 -*-
import os
import sys
import argparse
from typing import List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.paths_config import (
    RAW_DATA_DIR,
    CLEANED_CACHE_DIR,
    ensure_dirs,
)
from modules.text_cleaner import batch_clean_files
from modules.frequency_counter import create_counter
from modules.variant_mapper import create_mapper
from modules.visualization import create_visualizer
from modules.report_generator import create_report_generator


def cmd_clean(args):
    print("=== 古籍文本清洗 ===")
    result = batch_clean_files(RAW_DATA_DIR, CLEANED_CACHE_DIR)
    print(f"清洗完成: {result}")


def cmd_stats(args):
    print("=== 字频统计 ===")
    ensure_dirs()
    counter = create_counter()

    if args.clear_cache:
        counter.clear_cache()
        print("已清除旧缓存")

    result = counter.add_directory(RAW_DATA_DIR)
    print(f"加载文件: {result}")

    print("\n--- 朝代维度统计摘要 ---")
    summary = counter.get_summary()
    for d, s in summary.items():
        print(f"  {d}: {s['file_count']} 文件, {s['total_chars']} 总字, {s['unique_chars']} 不重复字, "
              f"通用字 {s['common_count']}, 生僻字 {s['rare_count']}")

    if counter.has_region_data():
        print("\n--- 地域维度统计摘要 ---")
        region_summary = counter.get_region_summary()
        for r, s in region_summary.items():
            print(f"  {r}({s['area']}): {s['file_count']} 文件, {s['total_chars']} 总字, "
                  f"{s['unique_chars']} 不重复字, 通用字 {s['common_count']}, 生僻字 {s['rare_count']}")

    top_n = args.top or 10
    print(f"\n--- 各朝代Top{top_n}高频字 ---")
    for d in counter.get_sorted_dynasties():
        top_chars = counter.get_top_chars(d, top_n=top_n)
        print(f"  {d}: {top_chars}")

    if counter.has_region_data():
        print(f"\n--- 各地域Top{top_n}高频字 ---")
        for r in counter.get_sorted_regions():
            top_chars = counter.get_region_top_chars(r, top_n=top_n)
            print(f"  {r}: {top_chars}")


def cmd_plot(args):
    print("=== 可视化图表生成 ===")
    ensure_dirs()
    counter = create_counter()
    counter.add_directory(RAW_DATA_DIR)
    visualizer = create_visualizer(counter=counter)

    target_chars = args.chars or ["之", "乎", "者", "也"]
    charts = visualizer.generate_all_charts(target_chars=target_chars)

    print(f"生成图表 {len(charts)} 张:")
    for name, path in charts.items():
        print(f"  {name}: {os.path.basename(path)}")


def cmd_report(args):
    print("=== 分析报告生成 ===")
    ensure_dirs()
    counter = create_counter()
    counter.add_directory(RAW_DATA_DIR)
    mapper = create_mapper()
    visualizer = create_visualizer(counter=counter)
    generator = create_report_generator(counter=counter, mapper=mapper, visualizer=visualizer)

    target_chars = args.chars or ["之", "乎", "者", "也"]
    generated = {}

    if args.excel or not (args.excel or args.pdf):
        excel_path = generator.generate_excel_report()
        generated["excel"] = excel_path
        print(f"Excel 报告: {os.path.basename(excel_path)}")

    if args.pdf or not (args.excel or args.pdf):
        pdf_path = generator.generate_pdf_report(target_chars=target_chars)
        generated["pdf"] = pdf_path
        print(f"PDF 报告: {os.path.basename(pdf_path)}")

    print(f"\n报告目录: {os.path.dirname(list(generated.values())[0])}")


def cmd_all(args):
    print("=== 全流程处理 ===")
    ensure_dirs()

    if args.clear_cache:
        counter = create_counter()
        counter.clear_cache()
        print("已清除旧缓存")

    print("\n--- 步骤1: 文本清洗 ---")
    clean_result = batch_clean_files(RAW_DATA_DIR, CLEANED_CACHE_DIR)
    print(f"  {clean_result}")

    print("\n--- 步骤2: 字频统计 ---")
    counter = create_counter()
    stats_result = counter.add_directory(RAW_DATA_DIR)
    print(f"  {stats_result}")
    print(f"  总文件: {stats_result['total']}, 新增: {stats_result['added']}, "
          f"跳过: {stats_result['skipped']}, 错误: {stats_result['errors']}")

    print("\n--- 步骤3: 可视化图表 ---")
    target_chars = args.chars or ["之", "乎", "者", "也"]
    visualizer = create_visualizer(counter=counter)
    charts = visualizer.generate_all_charts(target_chars=target_chars)
    print(f"  生成图表 {len(charts)} 张")

    print("\n--- 步骤4: 生成报告 ---")
    mapper = create_mapper()
    generator = create_report_generator(counter=counter, mapper=mapper, visualizer=visualizer)
    excel_path = generator.generate_excel_report()
    pdf_path = generator.generate_pdf_report(target_chars=target_chars)
    print(f"  Excel: {os.path.basename(excel_path)}")
    print(f"  PDF: {os.path.basename(pdf_path)}")

    print("\n=== 全流程完成 ===")


def cmd_region(args):
    print("=== 地域维度分析 ===")
    ensure_dirs()
    counter = create_counter()
    counter.add_directory(RAW_DATA_DIR)

    if not counter.has_region_data():
        print("未检测到地域维度数据。请使用「朝代_省份_书名.txt」格式的文件名。")
        print("示例: 宋_湖北_赤壁赋选篇.txt, 唐_陕西_唐诗选集.txt")
        return

    print("\n--- 已识别的出土地域 ---")
    regions = counter.get_sorted_regions()
    by_area = counter.get_regions_by_area()
    for area, area_regions in by_area.items():
        print(f"  {area}: {', '.join(area_regions)}")

    print("\n--- 地域字频汇总 ---")
    region_summary = counter.get_region_summary()
    for r, s in region_summary.items():
        print(f"  {r}({s['area']}): {s['file_count']} 文件, {s['total_chars']} 总字, "
              f"{s['unique_chars']} 不重复字")

    if args.chars:
        visualizer = create_visualizer(counter=counter)
        print(f"\n--- 生成指定汉字地域分析图表 ---")
        for char in args.chars:
            heatmap = visualizer.plot_dynasty_region_heatmap(char)
            combined = visualizer.plot_char_dynasty_region_combined(char)
            region_trend = visualizer.plot_char_region_trend(char)
            if heatmap:
                print(f"  「{char}」朝代×地域热力图: {os.path.basename(heatmap)}")
            if combined:
                print(f"  「{char}」时序-地域联动图: {os.path.basename(combined)}")
            if region_trend:
                print(f"  「{char}」地域分布: {os.path.basename(region_trend)}")

            region_freqs = counter.get_char_frequency_across_regions(char)
            print(f"  「{char}」各地频次: {dict(region_freqs)}")

            region_ratios = counter.get_char_ratio_across_regions(char)
            print(f"  「{char}」各地频率: { {k: f'{v:.4f}' for k, v in region_ratios.items()} }")


def main():
    parser = argparse.ArgumentParser(description="古籍文本字频分析系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    parser_clean = subparsers.add_parser("clean", help="批量清洗古籍文本")
    parser_clean.set_defaults(func=cmd_clean)

    parser_stats = subparsers.add_parser("stats", help="字频统计")
    parser_stats.add_argument("--top", type=int, default=10, help="显示Top N高频字")
    parser_stats.add_argument("--clear-cache", action="store_true", help="清除旧缓存")
    parser_stats.set_defaults(func=cmd_stats)

    parser_plot = subparsers.add_parser("plot", help="生成可视化图表")
    parser_plot.add_argument("--chars", nargs="+", help="要分析的汉字列表")
    parser_plot.set_defaults(func=cmd_plot)

    parser_report = subparsers.add_parser("report", help="生成分析报告")
    parser_report.add_argument("--excel", action="store_true", help="仅生成Excel")
    parser_report.add_argument("--pdf", action="store_true", help="仅生成PDF")
    parser_report.add_argument("--chars", nargs="+", help="要分析的汉字列表")
    parser_report.set_defaults(func=cmd_report)

    parser_all = subparsers.add_parser("all", help="一键全流程处理")
    parser_all.add_argument("--chars", nargs="+", help="要分析的汉字列表")
    parser_all.add_argument("--clear-cache", action="store_true", help="清除旧缓存")
    parser_all.set_defaults(func=cmd_all)

    parser_region = subparsers.add_parser("region", help="地域维度分析")
    parser_region.add_argument("--chars", nargs="+", help="要分析的汉字列表")
    parser_region.set_defaults(func=cmd_region)

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
