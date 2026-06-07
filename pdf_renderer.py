import json
from html import escape
from io import BytesIO


SECTION_TITLES = {
    "self_summary": "个人总结",
    "skills": "技能清单",
    "projects": "项目经历",
    "experience": "工作 / 实习经历",
    "education": "教育经历",
}

SECTION_ORDER = [
    "self_summary",
    "skills",
    "projects",
    "experience",
    "education",
]


def format_value(value):
    """把不同类型的内容整理成适合 PDF 展示的文本。"""
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            if item:
                parts.append(f"{key}：{format_value(item)}")
        return "；".join(parts)

    if isinstance(value, list):
        return "；".join(format_value(item) for item in value if item)

    return str(value).strip()


def add_section(story, styles, title, content):
    """向 PDF 中添加一个简历 section。"""
    from reportlab.platypus import Paragraph, Spacer

    if not content:
        return

    story.append(Spacer(1, 8))
    story.append(Paragraph(escape(title), styles["section_title"]))

    if isinstance(content, list):
        for item in content:
            item_text = format_value(item)
            if item_text:
                story.append(Paragraph(f"- {escape(item_text)}", styles["body"]))
    else:
        content_text = format_value(content)
        if content_text:
            story.append(Paragraph(escape(content_text), styles["body"]))


def render_resume_pdf(resume_content):
    """把结构化新版简历内容渲染成 PDF bytes。"""
    if not isinstance(resume_content, dict):
        raise RuntimeError("PDF 生成失败：新版简历内容格式不正确。")

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as error:
        raise RuntimeError("PDF 生成失败：当前环境缺少 reportlab，请先安装 requirements.txt 中的依赖。") from error

    buffer = BytesIO()

    # 使用内置中文字体，避免中文内容在 PDF 中显示为乱码。
    font_name = "STSong-Light"
    pdfmetrics.registerFont(UnicodeCIDFont(font_name))

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="resume_title",
            fontName=font_name,
            fontSize=18,
            leading=24,
            textColor=colors.HexColor("#222222"),
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="section_title",
            fontName=font_name,
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#111111"),
            borderWidth=0,
            borderColor=colors.HexColor("#DDDDDD"),
            borderPadding=0,
            spaceBefore=8,
            spaceAfter=4,
        )
    )
    styles.add(
        ParagraphStyle(
            name="body",
            fontName=font_name,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#333333"),
            spaceAfter=3,
        )
    )

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    story = []
    basic_info = resume_content.get("basic_info", {})
    name = basic_info.get("name") if isinstance(basic_info, dict) else ""

    story.append(Paragraph(escape(name or "新版简历"), styles["resume_title"]))

    if isinstance(basic_info, dict):
        contact_text = " | ".join(
            str(value).strip()
            for value in basic_info.values()
            if value and str(value).strip() != name
        )
        if contact_text:
            story.append(Paragraph(escape(contact_text), styles["body"]))

    story.append(Spacer(1, 6))

    for section_key in SECTION_ORDER:
        add_section(
            story,
            styles,
            SECTION_TITLES.get(section_key, section_key),
            resume_content.get(section_key),
        )

    # 如果后续新增字段，这里保留一个简单兜底，方便初学者扩展。
    known_keys = {"basic_info", *SECTION_ORDER}
    for section_key, content in resume_content.items():
        if section_key not in known_keys:
            add_section(story, styles, section_key, content)

    try:
        doc.build(story)
    except Exception as error:
        debug_text = json.dumps(resume_content, ensure_ascii=False)[:200]
        raise RuntimeError(f"PDF 生成失败，请检查新版简历内容格式。问题内容片段：{debug_text}") from error

    buffer.seek(0)
    return buffer.getvalue()
