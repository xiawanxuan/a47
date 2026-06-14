import os
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from .frequency_counter import DynastyFrequencyCounter
from .variant_mapper import VariantCharMapper
from .visualization import CharVisualizer


class ReportGenerator:
    def __init__(self, counter: DynastyFrequencyCounter, mapper: VariantCharMapper,
                 visualizer: CharVisualizer, excel_output_dir: str,
                 pdf_output_dir: str):
        self.counter = counter
        self.mapper = mapper
        self.visualizer = visualizer
        self.excel_output_dir = excel_output_dir
        self.pdf_output_dir = pdf_output_dir
        os.makedirs(excel_output_dir, exist_ok=True)
        os.makedirs(pdf_output_dir, exist_ok=True)

    def generate_excel_report(self, filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"字频统计报告_{timestamp}.xlsx"

        output_path = os.path.join(self.excel_output_dir, filename)

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            self._write_summary_sheet(writer)
            self._write_frequency_sheet(writer)
            self._write_category_sheet(writer)
            self._write_top_chars_sheet(writer)
            if self.counter.has_region_data():
                self._write_region_summary_sheet(writer)
                self._write_region_frequency_sheet(writer)
                self._write_region_top_chars_sheet(writer)
            self._write_files_info_sheet(writer)

        return output_path

    def _write_region_summary_sheet(self, writer: pd.ExcelWriter):
        summary = self.counter.get_region_summary()
        regions = self.counter.get_sorted_regions()

        data = []
        for r in regions:
            s = summary[r]
            data.append({
                "省份": r,
                "所属区域": s["area"],
                "文件数量": s["file_count"],
                "总字数": s["total_chars"],
                "不重复字数": s["unique_chars"],
                "通用字数量": s["common_count"],
                "生僻字数量": s["rare_count"],
            })

        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name="地域统计概览", index=False)

        worksheet = writer.sheets["地域统计概览"]
        for idx, col in enumerate(df.columns):
            worksheet.column_dimensions[chr(65 + idx)].width = 15

    def _write_region_frequency_sheet(self, writer: pd.ExcelWriter):
        df = self.counter.to_region_dataframe()
        df.to_excel(writer, sheet_name="地域字频明细", index=False)

        worksheet = writer.sheets["地域字频明细"]
        worksheet.column_dimensions["A"].width = 10

    def _write_region_top_chars_sheet(self, writer: pd.ExcelWriter):
        regions = self.counter.get_sorted_regions()
        top_n = 50

        all_data = []
        for r in regions:
            top_chars = self.counter.get_region_top_chars(r, top_n=top_n)
            for i, (char, count) in enumerate(top_chars):
                area = self.counter.region_area.get(r, "未知")
                all_data.append({
                    "省份": r,
                    "所属区域": area,
                    "排名": i + 1,
                    "汉字": char,
                    "频次": count,
                    "类别": self.mapper.get_category(char),
                })

        if all_data:
            df = pd.DataFrame(all_data)
            df.to_excel(writer, sheet_name=f"各地Top{top_n}", index=False)

    def _write_summary_sheet(self, writer: pd.ExcelWriter):
        summary = self.counter.get_summary()
        dynasties = self.counter.get_sorted_dynasties()

        data = []
        for d in dynasties:
            s = summary[d]
            data.append({
                "朝代": d,
                "文件数量": s["file_count"],
                "总字数": s["total_chars"],
                "不重复字数": s["unique_chars"],
                "通用字数量": s["common_count"],
                "生僻字数量": s["rare_count"],
            })

        df = pd.DataFrame(data)
        df.to_excel(writer, sheet_name="统计概览", index=False)

        worksheet = writer.sheets["统计概览"]
        for idx, col in enumerate(df.columns):
            worksheet.column_dimensions[chr(65 + idx)].width = 15

    def _write_frequency_sheet(self, writer: pd.ExcelWriter):
        df = self.counter.to_dataframe()
        df.to_excel(writer, sheet_name="字频明细", index=False)

        worksheet = writer.sheets["字频明细"]
        worksheet.column_dimensions["A"].width = 10

    def _write_category_sheet(self, writer: pd.ExcelWriter):
        dynasties = self.counter.get_sorted_dynasties()

        all_common = set()
        all_rare = set()

        for d in dynasties:
            freqs = self.counter.dynasty_freqs.get(d, {})
            for char in freqs:
                if self.mapper.is_common_char(char):
                    all_common.add(char)
                elif self.mapper.is_rare_char(char):
                    all_rare.add(char)

        common_data = {"通用字": sorted(all_common)}
        for d in dynasties:
            common_data[d] = [self.counter.get_dynasty_frequency(d, c) for c in sorted(all_common)]

        if common_data["通用字"]:
            df_common = pd.DataFrame(common_data)
            df_common.to_excel(writer, sheet_name="通用字统计", index=False)

        rare_data = {"生僻字": sorted(all_rare)}
        for d in dynasties:
            rare_data[d] = [self.counter.get_dynasty_frequency(d, c) for c in sorted(all_rare)]

        if rare_data["生僻字"]:
            df_rare = pd.DataFrame(rare_data)
            df_rare.to_excel(writer, sheet_name="生僻字统计", index=False)

    def _write_top_chars_sheet(self, writer: pd.ExcelWriter):
        dynasties = self.counter.get_sorted_dynasties()
        top_n = 50

        all_data = []
        for d in dynasties:
            top_chars = self.counter.get_top_chars(d, top_n=top_n)
            for i, (char, count) in enumerate(top_chars):
                all_data.append({
                    "朝代": d,
                    "排名": i + 1,
                    "汉字": char,
                    "频次": count,
                    "类别": self.mapper.get_category(char),
                })

        if all_data:
            df = pd.DataFrame(all_data)
            df.to_excel(writer, sheet_name=f"各代Top{top_n}", index=False)

    def _write_files_info_sheet(self, writer: pd.ExcelWriter):
        all_files = []
        for dynasty, files in self.counter.dynasty_file_info.items():
            for f in files:
                all_files.append({
                    "朝代": dynasty,
                    "出土地域": f.get("region", "未知"),
                    "文件名": f["filename"],
                    "总字数": f["total_chars"],
                    "不重复字数": f["unique_chars"],
                    "校验码": f["checksum"],
                })

        if all_files:
            df = pd.DataFrame(all_files)
            df.to_excel(writer, sheet_name="文件清单", index=False)

    def generate_pdf_report(self, target_chars: List[str] = None,
                           filename: str = None) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"古籍字频分析报告_{timestamp}.pdf"

        output_path = os.path.join(self.pdf_output_dir, filename)

        try:
            self._generate_pdf_with_reportlab(output_path, target_chars)
        except ImportError:
            self._generate_pdf_with_matplotlib(output_path, target_chars)

        return output_path

    def _generate_pdf_with_reportlab(self, output_path: str,
                                     target_chars: List[str] = None):
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle,
            PageBreak,
        )
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont

        self._register_chinese_font()

        doc = SimpleDocTemplate(
            output_path, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ChineseTitle", parent=styles["Title"],
            fontName="STSong-Light", fontSize=20, leading=28,
            spaceAfter=20,
        )
        h2_style = ParagraphStyle(
            "ChineseH2", parent=styles["Heading2"],
            fontName="STSong-Light", fontSize=14, leading=20,
            spaceBefore=15, spaceAfter=10,
        )
        body_style = ParagraphStyle(
            "ChineseBody", parent=styles["BodyText"],
            fontName="STSong-Light", fontSize=10, leading=16,
        )

        story = []

        story.append(Paragraph("古籍文本字频分析研究报告", title_style))
        story.append(Paragraph(f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}", body_style))
        story.append(Spacer(1, 1 * cm))

        story.append(Paragraph("一、统计概览", h2_style))
        summary = self.counter.get_summary()
        dynasties = self.counter.get_sorted_dynasties()

        table_data = [["朝代", "文件数", "总字数", "不重复字数", "通用字", "生僻字"]]
        for d in dynasties:
            s = summary[d]
            table_data.append([
                d, str(s["file_count"]),
                f"{s['total_chars']:,}",
                f"{s['unique_chars']:,}",
                f"{s['common_count']:,}",
                f"{s['rare_count']:,}",
            ])

        table = Table(table_data, colWidths=[2.5 * cm, 2 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.8 * cm))

        story.append(Paragraph("二、各朝代总字数分布", h2_style))
        dist_img = self.visualizer.plot_dynasty_distribution()
        if dist_img and os.path.exists(dist_img):
            img = Image(dist_img, width=15 * cm, height=9 * cm)
            story.append(img)
            story.append(Spacer(1, 0.5 * cm))

        story.append(Paragraph("三、通用字与生僻字对比", h2_style))
        cat_img = self.visualizer.plot_category_comparison()
        if cat_img and os.path.exists(cat_img):
            img = Image(cat_img, width=15 * cm, height=9 * cm)
            story.append(img)
            story.append(Spacer(1, 0.5 * cm))

        if self.counter.has_region_data():
            story.append(PageBreak())
            story.append(Paragraph("四、地域维度统计", h2_style))

            region_summary = self.counter.get_region_summary()
            regions = self.counter.get_sorted_regions()

            region_table_data = [["省份", "区域", "文件数", "总字数", "不重复字数", "通用字", "生僻字"]]
            for r in regions:
                s = region_summary[r]
                region_table_data.append([
                    r, s["area"], str(s["file_count"]),
                    f"{s['total_chars']:,}",
                    f"{s['unique_chars']:,}",
                    f"{s['common_count']:,}",
                    f"{s['rare_count']:,}",
                ])

            region_table = Table(region_table_data,
                                 colWidths=[2 * cm, 1.5 * cm, 1.5 * cm,
                                            2 * cm, 2.5 * cm, 2 * cm, 2 * cm])
            region_table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.gray),
                ("ALIGN", (2, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(region_table)
            story.append(Spacer(1, 0.8 * cm))

            region_dist_img = self.visualizer.plot_region_distribution()
            if region_dist_img and os.path.exists(region_dist_img):
                story.append(Paragraph("各省份出土古籍总字数分布", h2_style))
                img = Image(region_dist_img, width=15 * cm, height=9 * cm)
                story.append(img)
                story.append(Spacer(1, 0.5 * cm))

        next_section = 5 if not self.counter.has_region_data() else 6
        if target_chars:
            story.append(PageBreak())
            story.append(Paragraph(f"{next_section}、重点汉字演变趋势", h2_style))

            if len(target_chars) >= 2:
                multi_img = self.visualizer.plot_multiple_chars_trend(target_chars)
                if multi_img and os.path.exists(multi_img):
                    img = Image(multi_img, width=15 * cm, height=9 * cm)
                    story.append(img)
                    story.append(Spacer(1, 0.5 * cm))

            for char in target_chars:
                story.append(Paragraph(f"「{char}」字使用频率演变", h2_style))
                char_img = self.visualizer.plot_char_trend(char)
                if char_img and os.path.exists(char_img):
                    img = Image(char_img, width=15 * cm, height=9 * cm)
                    story.append(img)
                    story.append(Spacer(1, 0.3 * cm))

                if self.counter.has_region_data():
                    combined_img = self.visualizer.plot_char_dynasty_region_combined(char)
                    if combined_img and os.path.exists(combined_img):
                        story.append(Paragraph(f"「{char}」字时序-地域联动分析", h2_style))
                        img = Image(combined_img, width=15 * cm, height=7 * cm)
                        story.append(img)
                        story.append(Spacer(1, 0.3 * cm))

                    heatmap_img = self.visualizer.plot_dynasty_region_heatmap(char)
                    if heatmap_img and os.path.exists(heatmap_img):
                        story.append(Paragraph(f"「{char}」字朝代×地域热力图", h2_style))
                        img = Image(heatmap_img, width=15 * cm, height=9 * cm)
                        story.append(img)
                        story.append(Spacer(1, 0.3 * cm))

        next_section = next_section + 1
        story.append(PageBreak())
        story.append(Paragraph(f"{next_section}、各朝代高频字排行", h2_style))

        for i, dynasty in enumerate(dynasties):
            story.append(Paragraph(f"{dynasty}代高频字 Top 15", h2_style))
            top_img = self.visualizer.plot_dynasty_top_chars(dynasty, top_n=15)
            if top_img and os.path.exists(top_img):
                img = Image(top_img, width=14 * cm, height=8.5 * cm)
                story.append(img)
                story.append(Spacer(1, 0.3 * cm))
            if (i + 1) % 2 == 0 and i < len(dynasties) - 1:
                story.append(PageBreak())

        if self.counter.has_region_data():
            story.append(PageBreak())
            next_section += 1
            story.append(Paragraph(f"{next_section}、各地域高频字排行", h2_style))
            for i, region in enumerate(regions):
                story.append(Paragraph(f"{region}出土古籍高频字 Top 15", h2_style))
                top_img = self.visualizer.plot_region_top_chars(region, top_n=15)
                if top_img and os.path.exists(top_img):
                    img = Image(top_img, width=14 * cm, height=8.5 * cm)
                    story.append(img)
                    story.append(Spacer(1, 0.3 * cm))
                if (i + 1) % 2 == 0 and i < len(regions) - 1:
                    story.append(PageBreak())

        next_section += 1
        story.append(PageBreak())
        story.append(Paragraph(f"{next_section}、研究说明", h2_style))
        study_text = (
            "本报告基于古籍文本批量处理系统生成，主要功能包括："
            "（1）古籍文本清洗与脱敏，去除标点、空白及破损字符；"
            "（2）异体字归一化映射，将异体字统一为标准字形；"
            "（3）按朝代分组统计字频，区分通用字与生僻字；"
            "（4）可视化展示汉字使用频率的历史演变规律。"
        )
        if self.counter.has_region_data():
            study_text += (
                "（5）按出土地域分组统计，生成地域-字频热力图与时序-地域联动分析，"
                "支持汉字使用的时空二维研究。"
            )
        study_text += "本系统支持增量数据源追加，可随古籍数据库扩充重新计算。"
        story.append(Paragraph(study_text, body_style))

        doc.build(story)

    def _register_chinese_font(self):
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont

        try:
            pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
        except Exception:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont("STHeiti-Light"))
            except Exception:
                pass

    def _generate_pdf_with_matplotlib(self, output_path: str,
                                      target_chars: List[str] = None):
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams["axes.unicode_minus"] = False

        with PdfPages(output_path) as pdf:
            self._pdf_cover_page(pdf)

            summary = self.counter.get_summary()
            self._pdf_summary_page(pdf, summary)

            dist_img = self.visualizer.plot_dynasty_distribution()
            if dist_img:
                self._pdf_image_page(pdf, dist_img, "各朝代总字数分布")

            cat_img = self.visualizer.plot_category_comparison()
            if cat_img:
                self._pdf_image_page(pdf, cat_img, "通用字与生僻字对比")

            if self.counter.has_region_data():
                region_dist_img = self.visualizer.plot_region_distribution()
                if region_dist_img:
                    self._pdf_image_page(pdf, region_dist_img, "各省份出土古籍总字数分布")

            if target_chars and len(target_chars) >= 2:
                multi_img = self.visualizer.plot_multiple_chars_trend(target_chars)
                if multi_img:
                    self._pdf_image_page(pdf, multi_img, "重点汉字演变趋势对比")

            if target_chars:
                for char in target_chars:
                    char_img = self.visualizer.plot_char_trend(char)
                    if char_img:
                        self._pdf_image_page(pdf, char_img, f"「{char}」字使用频率演变")

                    if self.counter.has_region_data():
                        combined_img = self.visualizer.plot_char_dynasty_region_combined(char)
                        if combined_img:
                            self._pdf_image_page(pdf, combined_img, f"「{char}」字时序-地域联动")
                        heatmap_img = self.visualizer.plot_dynasty_region_heatmap(char)
                        if heatmap_img:
                            self._pdf_image_page(pdf, heatmap_img, f"「{char}」字朝代×地域热力图")

            dynasties = self.counter.get_sorted_dynasties()
            for dynasty in dynasties:
                top_img = self.visualizer.plot_dynasty_top_chars(dynasty, top_n=15)
                if top_img:
                    self._pdf_image_page(pdf, top_img, f"{dynasty}代高频字 Top 15")

            if self.counter.has_region_data():
                regions = self.counter.get_sorted_regions()
                for region in regions:
                    top_img = self.visualizer.plot_region_top_chars(region, top_n=15)
                    if top_img:
                        self._pdf_image_page(pdf, top_img, f"{region}出土古籍高频字 Top 15")

    def _pdf_cover_page(self, pdf):
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.5, 0.7, "古籍文本字频分析研究报告",
                 ha="center", fontsize=24, fontweight="bold")
        fig.text(0.5, 0.6,
                 f"生成时间：{datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
                 ha="center", fontsize=12)
        fig.text(0.5, 0.5, "汉语言文字研究所", ha="center", fontsize=14)
        pdf.savefig(fig)
        plt.close(fig)

    def _pdf_summary_page(self, pdf, summary):
        import matplotlib
        matplotlib.rcParams["axes.unicode_minus"] = False

        fig, ax = plt.subplots(figsize=(8.27, 11.69))
        ax.axis("off")

        dynasties = self.counter.get_sorted_dynasties()
        table_data = [["朝代", "文件数", "总字数", "不重复字数"]]
        for d in dynasties:
            s = summary[d]
            table_data.append([d, str(s["file_count"]),
                             f"{s['total_chars']:,}", f"{s['unique_chars']:,}"])

        table = ax.table(cellText=table_data, loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)

        ax.set_title("一、统计概览", fontsize=16, fontweight="bold", y=0.8)
        pdf.savefig(fig)
        plt.close(fig)

    def _pdf_image_page(self, pdf, image_path, title):
        from PIL import Image
        import matplotlib
        matplotlib.rcParams["axes.unicode_minus"] = False

        fig = plt.figure(figsize=(8.27, 11.69))
        fig.suptitle(title, fontsize=14, fontweight="bold")

        img = Image.open(image_path)
        ax = fig.add_subplot(111)
        ax.imshow(img)
        ax.axis("off")

        pdf.savefig(fig)
        plt.close(fig)

    def generate_full_report(self, target_chars: List[str] = None) -> Dict[str, str]:
        results = {}
        results["excel"] = self.generate_excel_report()
        results["pdf"] = self.generate_pdf_report(target_chars=target_chars)
        return results


def create_report_generator(counter: DynastyFrequencyCounter = None,
                            mapper: VariantCharMapper = None,
                            visualizer: CharVisualizer = None,
                            excel_output_dir: str = None,
                            pdf_output_dir: str = None) -> ReportGenerator:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import EXCEL_OUTPUT_DIR, PDF_OUTPUT_DIR

    if counter is None:
        from .frequency_counter import create_counter
        counter = create_counter()
    if mapper is None:
        from .variant_mapper import create_mapper
        mapper = create_mapper()
    if visualizer is None:
        from .visualization import create_visualizer
        visualizer = create_visualizer(counter=counter)
    if excel_output_dir is None:
        excel_output_dir = EXCEL_OUTPUT_DIR
    if pdf_output_dir is None:
        pdf_output_dir = PDF_OUTPUT_DIR

    return ReportGenerator(counter, mapper, visualizer,
                           excel_output_dir, pdf_output_dir)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config.paths_config import ensure_dirs

    ensure_dirs()
    generator = create_report_generator()
    results = generator.generate_full_report(target_chars=["之", "乎", "者", "也"])
    print(f"生成报告: {results}")
