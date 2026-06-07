from pypdf import PdfReader


def extract_text_from_pdf(uploaded_file):
    """从上传的 PDF 文件中提取文本。"""
    try:
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
    except Exception as error:
        raise RuntimeError("PDF 读取失败，请确认文件是正常的 PDF 简历。") from error

    return "\n".join(text_parts).strip()
