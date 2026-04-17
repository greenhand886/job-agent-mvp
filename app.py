import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from llm_service import analyze_job_match


HISTORY_FILE = Path("data/history.json")
MAX_HISTORY_COUNT = 5


def init_history_file():
    """如果历史文件不存在，就自动创建一个空列表文件。"""
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")


def load_history():
    """读取本地历史记录，文件异常时返回空列表。"""
    init_history_file()
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if isinstance(history, list):
        return history
    return []


def save_history(history):
    """把历史记录保存到本地 JSON 文件。"""
    init_history_file()
    HISTORY_FILE.write_text(
        json.dumps(history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def make_jd_summary(jd_text, max_length=60):
    """截取岗位 JD 前若干字，作为历史记录摘要。"""
    clean_text = " ".join(jd_text.split())
    if len(clean_text) <= max_length:
        return clean_text
    return clean_text[:max_length] + "..."


def add_history_record(jd_text, result):
    """分析成功后追加一条历史记录。"""
    history = load_history()
    record = {
        "时间戳": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "岗位摘要": make_jd_summary(jd_text),
        "匹配分数": result.get("匹配分数", "暂无分数"),
        "一句话结论": result.get("一句话结论", "暂无结论"),
    }
    history.insert(0, record)
    save_history(history)


def show_list_block(title, value):
    """把列表或普通文本统一展示成清晰分块。"""
    with st.container(border=True):
        st.subheader(title)
        if isinstance(value, list):
            for item in value:
                st.write(f"- {item}")
        elif value:
            st.write(value)
        else:
            st.write("暂无内容")


def show_history():
    """展示最近几条分析历史。"""
    st.divider()
    st.header("历史记录")

    history = load_history()
    if not history:
        st.info("暂无历史记录。完成一次分析后，这里会显示最近的分析结果。")
        return

    for record in history[:MAX_HISTORY_COUNT]:
        with st.container(border=True):
            st.write(f"时间：{record.get('时间戳', '未知时间')}")
            st.write(f"岗位摘要：{record.get('岗位摘要', '暂无摘要')}")
            st.write(f"匹配分数：{record.get('匹配分数', '暂无分数')}")
            st.write(f"一句话结论：{record.get('一句话结论', '暂无结论')}")


st.set_page_config(
    page_title="Job Agent MVP",
    page_icon="💼",
    layout="wide",
)

with st.sidebar:
    st.header("项目状态")
    st.write("当前阶段：第 1 天")
    st.write("当前目标：先把页面骨架搭好")
    st.divider()
    st.write("当前模型：qwen-plus")

st.title("Job Agent MVP")
st.write("输入岗位 JD 和基础简历后，系统会调用阿里云百炼大模型，生成一份简明的岗位匹配分析。")

left_column, right_column = st.columns(2)

with left_column:
    jd_text = st.text_area(
        "岗位 JD",
        height=300,
        placeholder="请把岗位描述粘贴到这里。",
    )

with right_column:
    resume_text = st.text_area(
        "基础简历",
        height=300,
        placeholder="请把你的基础简历粘贴到这里。",
    )

if st.button("开始分析", type="primary", use_container_width=True):
    if not jd_text.strip() or not resume_text.strip():
        st.warning("请先填写岗位 JD 和基础简历。")
    else:
        try:
            with st.spinner("正在调用阿里云百炼大模型分析，请稍候。"):
                result = analyze_job_match(jd_text, resume_text)
        except RuntimeError as error:
            st.error(str(error))
        except ValueError as error:
            st.error(str(error))
        else:
            add_history_record(jd_text, result)
            score = result.get("匹配分数", "暂无分数")

            st.divider()
            st.header("分析结果")
            st.metric("匹配分数", score)

            show_list_block("岗位关键词", result.get("岗位关键词"))
            show_list_block("你的优势", result.get("你的优势"))
            show_list_block("你的缺口", result.get("你的缺口"))
            show_list_block("一句话结论", result.get("一句话结论"))

show_history()
