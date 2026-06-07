from datetime import datetime
from html import escape

import streamlit as st

from agent_loop import (
    generate_match_and_rewrite_plan,
    generate_section_rewrite,
    parse_jd_structure,
    parse_resume_structure,
    run_review_loop,
)
from llm_service import extract_jd_from_image
from pdf_reader import extract_text_from_pdf
from pdf_renderer import render_resume_pdf


MATCH_THRESHOLD = 75

ANALYSIS_STEPS = [
    "解析简历 PDF",
    "提取 JD 内容",
    "结构化简历",
    "结构化 JD",
    "匹配分析",
]

OPTIMIZE_STEPS = [
    "生成改写计划",
    "按 section 改写",
    "检查与修正 loop",
    "生成新版 PDF",
]


def inject_css():
    """注入页面样式，把 Streamlit 页面塑造成浅色 AI SaaS 工作台。"""
    st.markdown(
        """
        <style>
        :root {
            --bg: #020617;
            --panel: rgba(15, 23, 42, 0.70);
            --panel-strong: rgba(15, 23, 42, 0.88);
            --line: rgba(255, 255, 255, 0.10);
            --line-strong: rgba(103, 232, 249, 0.24);
            --text: #f8fafc;
            --muted: #94a3b8;
            --muted-2: #64748b;
            --cyan: #67e8f9;
            --blue: #60a5fa;
            --violet: #8b5cf6;
            --green: #34d399;
            --amber: #fbbf24;
        }

        html, body, #root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background: #020617 !important;
        }

        [data-testid="stHeader"] {
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
            background: transparent !important;
        }

        [data-testid="stToolbar"] {
            display: none !important;
        }

        [data-testid="stDecoration"] {
            display: none !important;
        }

        [data-testid="stStatusWidget"] {
            display: none !important;
        }

        .stApp > header {
            display: none !important;
            height: 0 !important;
            visibility: hidden !important;
            background: transparent !important;
        }

        .main {
            padding-top: 0 !important;
        }

        .stApp {
            background:
                radial-gradient(circle at -8% -12%, rgba(34, 211, 238, 0.16), transparent 34rem),
                radial-gradient(circle at 105% 8%, rgba(139, 92, 246, 0.16), transparent 32rem),
                radial-gradient(circle at 48% 115%, rgba(37, 99, 235, 0.14), transparent 30rem),
                linear-gradient(180deg, #020617 0%, #050816 52%, #020617 100%);
            color: var(--text);
        }

        .stApp:before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
            background-size: 48px 48px;
            mask-image: radial-gradient(circle at center, black, transparent 78%);
            opacity: 0.75;
            z-index: 0;
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 1560px;
            padding-top: 0.75rem !important;
            padding-bottom: 3.6rem;
        }

        h1, h2, h3, p {
            letter-spacing: 0;
        }

        [data-testid="stSidebar"] {
            background: rgba(2, 6, 23, 0.92);
            border-right: 1px solid rgba(255,255,255,0.08);
        }

        [data-testid="stSidebar"] * {
            color: #e2e8f0;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--line) !important;
            border-radius: 24px !important;
            background: rgba(15, 23, 42, 0.56) !important;
            backdrop-filter: blur(22px);
            box-shadow: 0 24px 80px rgba(0, 0, 0, 0.34);
        }

        .maobu-shell {
            display: grid;
            grid-template-columns: 300px minmax(0, 1fr);
            gap: 1.35rem;
            align-items: start;
        }

        .control-center {
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
            width: 300px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 1.35rem;
            border-right: 1px solid rgba(255,255,255,0.10);
            background:
                linear-gradient(180deg, rgba(15,23,42,0.96), rgba(2,6,23,0.98)),
                radial-gradient(circle at 10% 0%, rgba(103,232,249,0.08), transparent 18rem);
            backdrop-filter: blur(26px);
            box-shadow: 20px 0 70px rgba(0,0,0,0.25);
            z-index: 10;
        }

        .brand-row {
            display: flex;
            align-items: center;
            gap: 0.8rem;
            margin-bottom: 1.7rem;
        }

        .brand-icon {
            width: 2.85rem;
            height: 2.85rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 18px;
            background: linear-gradient(135deg, var(--cyan), var(--violet));
            color: #020617;
            font-size: 1.25rem;
            box-shadow: 0 18px 42px rgba(34, 211, 238, 0.18);
        }

        .brand-sub {
            color: var(--muted);
            font-size: 0.78rem;
            line-height: 1.3;
        }

        .brand-title {
            color: #ffffff;
            font-size: 1.04rem;
            font-weight: 760;
        }

        .side-item {
            padding: 0.95rem;
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 18px;
            background: rgba(255,255,255,0.035);
            margin-bottom: 0.65rem;
        }

        .side-label {
            color: #64748b;
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 0.28rem;
        }

        .side-value {
            color: #e2e8f0;
            font-size: 0.88rem;
            line-height: 1.55;
        }

        .agent-note {
            padding: 1rem;
            border: 1px solid rgba(103, 232, 249, 0.15);
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(103, 232, 249, 0.10), rgba(139, 92, 246, 0.08));
            color: #cbd5e1;
            line-height: 1.65;
            font-size: 0.86rem;
        }

        .main-workspace {
            margin-left: 322px;
            padding-top: 1.2rem;
        }

        .section-block {
            padding: 1.2rem 0 1.45rem;
            border-top: 1px solid rgba(255,255,255,0.08);
        }

        .section-block.first {
            border-top: 0;
            padding-top: 0;
        }

        .hero-card {
            overflow: hidden;
            position: relative;
            padding: 2.35rem;
            border: 1px solid var(--line);
            border-radius: 32px;
            background: rgba(15, 23, 42, 0.58);
            backdrop-filter: blur(24px);
            box-shadow: 0 24px 80px rgba(0,0,0,0.34);
            margin-bottom: 1.1rem;
        }

        .hero-card:after {
            content: "";
            position: absolute;
            right: -9rem;
            top: -10rem;
            width: 26rem;
            height: 26rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(103,232,249,0.17), transparent 66%);
            pointer-events: none;
        }

        .hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: 1.25fr 0.75fr;
            gap: 2rem;
            align-items: end;
        }

        .hero-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.48rem 0.82rem;
            border-radius: 999px;
            border: 1px solid rgba(103,232,249,0.16);
            background: rgba(103,232,249,0.10);
            color: var(--cyan);
            font-size: 0.73rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 1rem;
        }

        .hero-title {
            max-width: 850px;
            color: #ffffff;
            font-size: 4rem;
            line-height: 1.04;
            font-weight: 820;
            letter-spacing: -0.035em;
            margin: 0;
        }

        .hero-subtitle {
            max-width: 760px;
            color: #cbd5e1;
            font-size: 1.05rem;
            line-height: 1.7;
            margin: 1rem 0 1.1rem;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.65rem;
        }

        .chip {
            display: inline-flex;
            padding: 0.52rem 0.78rem;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.055);
            color: #e2e8f0;
            font-size: 0.84rem;
        }

        .hero-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.78rem;
        }

        .stat-pill {
            padding: 0.95rem;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 20px;
            background: rgba(255,255,255,0.045);
        }

        .stat-label {
            color: #94a3b8;
            font-size: 0.7rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            margin-bottom: 0.45rem;
        }

        .stat-value {
            color: #ffffff;
            font-size: 1rem;
            font-weight: 740;
        }

        .section-label {
            color: rgba(103, 232, 249, 0.82);
            font-size: 0.72rem;
            font-weight: 820;
            text-transform: uppercase;
            letter-spacing: 0.24em;
            margin-bottom: 0.4rem;
        }

        .section-title {
            color: #ffffff;
            font-size: 1.55rem;
            font-weight: 760;
            margin-bottom: 0.35rem;
        }

        .section-desc {
            max-width: 780px;
            color: #94a3b8;
            font-size: 0.92rem;
            line-height: 1.75;
            margin-bottom: 0.8rem;
        }

        .input-title {
            color: #ffffff;
            font-size: 1.25rem;
            font-weight: 760;
            margin-bottom: 0.2rem;
        }

        .input-desc {
            color: #94a3b8;
            font-size: 0.86rem;
            line-height: 1.65;
            margin-bottom: 0.7rem;
        }

        .status-note {
            padding: 0.92rem 1rem;
            border-radius: 18px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(255,255,255,0.04);
            color: #cbd5e1;
            font-size: 0.9rem;
            line-height: 1.7;
        }

        .result-card {
            min-height: 136px;
            padding: 1.15rem;
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 24px;
            background: rgba(255,255,255,0.045);
            box-shadow: 0 18px 55px rgba(0,0,0,0.22);
        }

        .result-card.good {
            border-color: rgba(52,211,153,0.16);
            background: linear-gradient(135deg, rgba(52,211,153,0.10), rgba(255,255,255,0.035));
        }

        .result-card.warn {
            border-color: rgba(251,191,36,0.18);
            background: linear-gradient(135deg, rgba(251,191,36,0.10), rgba(255,255,255,0.035));
        }

        .result-label {
            color: #94a3b8;
            font-size: 0.78rem;
            font-weight: 820;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            margin-bottom: 0.68rem;
        }

        .result-text {
            color: #e2e8f0;
            font-size: 0.93rem;
            line-height: 1.78;
        }

        .score-card {
            padding: 1.25rem;
            border: 1px solid rgba(103,232,249,0.16);
            border-radius: 28px;
            background: linear-gradient(135deg, rgba(103,232,249,0.10), rgba(139,92,246,0.08));
            box-shadow: 0 22px 68px rgba(0,0,0,0.30);
        }

        .score-row {
            display: flex;
            align-items: center;
            gap: 1.25rem;
        }

        .score-ring {
            width: 8.7rem;
            height: 8.7rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background:
                radial-gradient(circle at center, #020617 58%, transparent 59%),
                conic-gradient(from 180deg, var(--cyan), var(--violet), rgba(255,255,255,0.10));
        }

        .score-value {
            color: #ffffff;
            font-size: 2.7rem;
            font-weight: 840;
            line-height: 1;
        }

        .score-foot {
            color: #94a3b8;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            margin-top: 0.3rem;
        }

        .download-shell {
            padding: 1rem;
            border-radius: 24px;
            border: 1px solid rgba(103,232,249,0.18);
            background: linear-gradient(135deg, rgba(103,232,249,0.12), rgba(139,92,246,0.08));
            color: #e2e8f0;
            line-height: 1.7;
            margin: 1rem 0 0.8rem;
        }

        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 18px !important;
            border: 1px solid rgba(103,232,249,0.22) !important;
            background: linear-gradient(135deg, #67e8f9 0%, #8b5cf6 100%) !important;
            color: #020617 !important;
            font-weight: 800 !important;
            min-height: 3rem;
            box-shadow: 0 18px 42px rgba(34, 211, 238, 0.17);
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            transform: translateY(-1px);
            border-color: rgba(255,255,255,0.35) !important;
        }

        [data-testid="stFileUploader"] {
            padding: 0.75rem;
            border-radius: 18px;
            border: 1px solid rgba(226,232,240,0.95);
            background: #f8fafc;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.85), 0 10px 24px rgba(0,0,0,0.12);
        }

        [data-testid="stFileUploader"] * {
            color: #0f172a !important;
        }

        [data-testid="stFileUploader"] section {
            border: 0 !important;
            background: #ffffff !important;
            border-radius: 14px !important;
            padding: 1rem !important;
        }

        [data-testid="stFileUploader"] button {
            border-radius: 12px !important;
            background: #0f172a !important;
            color: #ffffff !important;
            border: 1px solid #0f172a !important;
        }

        textarea, input {
            border-radius: 18px !important;
            background: rgba(2,6,23,0.52) !important;
            color: #f8fafc !important;
        }

        .stTextArea textarea {
            border-color: rgba(255,255,255,0.12) !important;
        }

        [data-testid="stExpander"] {
            border: 1px solid rgba(255,255,255,0.10);
            border-radius: 20px;
            background: rgba(15,23,42,0.42);
        }

        @media (max-width: 1180px) {
            .control-center {
                position: relative;
                width: auto;
                min-height: auto;
                padding: 1rem;
                border-right: 1px solid rgba(255,255,255,0.10);
                border-radius: 24px;
                margin-bottom: 1rem;
            }
            .main-workspace {
                margin-left: 0;
                padding-top: 0;
            }
            .hero-grid {
                grid-template-columns: 1fr;
            }
            .hero-title {
                font-size: 2.55rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <style>
        html, body, #root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background: #ffffff !important;
        }

        .stApp {
            background:
                radial-gradient(circle at -8% -12%, rgba(37, 99, 235, 0.10), transparent 34rem),
                radial-gradient(circle at 105% 8%, rgba(79, 70, 229, 0.08), transparent 32rem),
                linear-gradient(180deg, #ffffff 0%, #f8fafc 58%, #ffffff 100%) !important;
            color: #0f172a !important;
        }

        .stApp:before {
            background-image:
                linear-gradient(rgba(15,23,42,0.035) 1px, transparent 1px),
                linear-gradient(90deg, rgba(15,23,42,0.035) 1px, transparent 1px) !important;
            opacity: 0.55 !important;
        }

        [data-testid="stSidebar"] {
            background: #ffffff !important;
            border-right: 1px solid rgba(15,23,42,0.08) !important;
        }

        [data-testid="stSidebar"] * {
            color: #0f172a !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255,255,255,0.94) !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            box-shadow: 0 18px 50px rgba(15,23,42,0.08) !important;
        }

        .control-center {
            background:
                linear-gradient(180deg, rgba(255,255,255,0.98), rgba(248,250,252,0.98)),
                radial-gradient(circle at 10% 0%, rgba(37,99,235,0.08), transparent 18rem) !important;
            border-right: 1px solid rgba(15,23,42,0.10) !important;
            box-shadow: 18px 0 50px rgba(15,23,42,0.06) !important;
        }

        .brand-title,
        .hero-title,
        .section-title,
        .input-title,
        .stat-value,
        .score-value {
            color: #0f172a !important;
        }

        .brand-sub,
        .hero-subtitle,
        .section-desc,
        .input-desc,
        .side-label,
        .stat-label,
        .result-label,
        .score-foot {
            color: #64748b !important;
        }

        .side-value,
        .result-text,
        .status-note,
        .download-shell,
        .agent-note {
            color: #334155 !important;
        }

        .hero-card {
            background: rgba(255,255,255,0.94) !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            box-shadow: 0 24px 70px rgba(15,23,42,0.10) !important;
        }

        .hero-card:after {
            background: radial-gradient(circle, rgba(37,99,235,0.12), transparent 66%) !important;
        }

        .hero-pill {
            background: rgba(37,99,235,0.08) !important;
            border: 1px solid rgba(37,99,235,0.16) !important;
            color: #2563eb !important;
        }

        .chip,
        .stat-pill,
        .side-item,
        .status-note {
            background: #f8fafc !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            color: #334155 !important;
        }

        .result-card {
            background: #ffffff !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
            box-shadow: 0 16px 45px rgba(15,23,42,0.08) !important;
        }

        .result-card.good {
            background: linear-gradient(135deg, rgba(5,150,105,0.08), #ffffff) !important;
            border-color: rgba(5,150,105,0.18) !important;
        }

        .result-card.warn {
            background: linear-gradient(135deg, rgba(180,83,9,0.08), #ffffff) !important;
            border-color: rgba(180,83,9,0.18) !important;
        }

        .score-card,
        .download-shell,
        .agent-note {
            background: linear-gradient(135deg, rgba(37,99,235,0.08), rgba(79,70,229,0.05)) !important;
            border: 1px solid rgba(37,99,235,0.16) !important;
            box-shadow: 0 18px 45px rgba(15,23,42,0.08) !important;
        }

        .score-ring {
            background:
                radial-gradient(circle at center, #ffffff 58%, transparent 59%),
                conic-gradient(from 180deg, #2563eb, #4f46e5, rgba(15,23,42,0.10)) !important;
        }

        .brand-icon,
        div.stButton > button,
        div.stDownloadButton > button {
            background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 16px 34px rgba(37,99,235,0.18) !important;
        }

        [data-testid="stFileUploader"] {
            background: #f8fafc !important;
            border: 1px solid rgba(15,23,42,0.12) !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.85), 0 10px 24px rgba(15,23,42,0.08) !important;
        }

        [data-testid="stFileUploader"] * {
            color: #0f172a !important;
        }

        [data-testid="stFileUploader"] section {
            background: #ffffff !important;
            border: 0 !important;
        }

        [data-testid="stFileUploader"] button {
            background: #0f172a !important;
            color: #ffffff !important;
        }

        textarea, input {
            background: #ffffff !important;
            color: #0f172a !important;
            border-color: rgba(15,23,42,0.12) !important;
        }

        [data-testid="stExpander"] {
            background: #ffffff !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
        }

        /* 浅色版微调：保留上一版完整控制中心效果 */
        .block-container {
            max-width: 1440px !important;
            padding-left: 1.25rem !important;
            padding-right: 1.25rem !important;
            padding-top: 0.6rem !important;
        }

        .main-workspace {
            margin-left: 0 !important;
            padding-top: 0.65rem !important;
        }

        .control-center {
            position: fixed !important;
            top: 0 !important;
            left: 1.25rem !important;
            bottom: 0 !important;
            width: min(285px, calc(22vw - 2rem)) !important;
            height: 100vh !important;
            min-height: 100vh !important;
            padding: 1.05rem !important;
            border-radius: 0 24px 24px 0 !important;
            z-index: 9999 !important;
        }

        .hero-card {
            padding: 1.75rem 1.9rem !important;
            border-radius: 28px !important;
        }

        .hero-grid {
            grid-template-columns: minmax(0, 1.2fr) minmax(230px, 0.8fr) !important;
            gap: 1.35rem !important;
        }

        .hero-title {
            max-width: 760px !important;
            font-size: clamp(2.35rem, 4vw, 3.35rem) !important;
            line-height: 1.08 !important;
        }

        .hero-subtitle {
            margin: 0.75rem 0 0.9rem !important;
        }

        .brand-icon {
            background: #eef2ff !important;
            color: #4338ca !important;
            border: 1px solid rgba(79,70,229,0.16) !important;
            box-shadow: 0 10px 24px rgba(79,70,229,0.10) !important;
        }

        [data-testid="stFileUploader"] button {
            background: #f1f5f9 !important;
            color: #334155 !important;
            border: 1px solid rgba(15,23,42,0.12) !important;
            box-shadow: none !important;
        }

        [data-testid="stFileUploader"] button:hover {
            background: #e2e8f0 !important;
            color: #0f172a !important;
            border-color: rgba(15,23,42,0.18) !important;
        }

        .score-card {
            background: #ffffff !important;
            border: 1px solid rgba(15,23,42,0.10) !important;
        }

        .score-ring {
            width: 7.6rem !important;
            height: 7.6rem !important;
            background:
                radial-gradient(circle at center, #ffffff 60%, transparent 61%),
                conic-gradient(from 180deg, #2563eb, #93c5fd, #e2e8f0) !important;
        }

        .score-row {
            gap: 1rem !important;
        }

        .section-block {
            padding: 1rem 0 1.25rem !important;
            border-top: 1px solid rgba(15,23,42,0.08) !important;
        }

        .section-block.first {
            border-top: 0 !important;
        }

        @media (max-width: 1180px) {
            .control-center {
                position: relative !important;
                width: auto !important;
                height: auto !important;
                min-height: auto !important;
                border-radius: 24px !important;
            }
            .main-workspace {
                margin-left: 0 !important;
            }
            .hero-grid {
                grid-template-columns: 1fr !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_frontend_design_theme():
    """Apply a cohesive editorial SaaS theme for the Streamlit workspace."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #f6f1e8;
            --bg-soft: #fbf8f3;
            --panel: rgba(255, 255, 255, 0.84);
            --panel-strong: rgba(255, 255, 255, 0.95);
            --sidebar: #17313a;
            --sidebar-soft: #234752;
            --line: rgba(23, 49, 58, 0.10);
            --line-strong: rgba(219, 106, 50, 0.22);
            --text: #17313a;
            --muted: #6b7d83;
            --muted-strong: #40585f;
            --accent: #db6a32;
            --accent-soft: #f4c5a9;
            --accent-2: #147d74;
            --accent-3: #f1b34f;
            --good: #157a6e;
            --warn: #d97706;
            --shadow-soft: 0 18px 40px rgba(23, 49, 58, 0.08);
            --shadow-strong: 0 28px 64px rgba(23, 49, 58, 0.14);
        }

        html, body, #root, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
            background: var(--bg) !important;
        }

        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        .stApp > header {
            display: none !important;
            visibility: hidden !important;
            height: 0 !important;
            background: transparent !important;
        }

        .main {
            padding-top: 0 !important;
        }

        .stApp {
            overflow-x: hidden;
            background:
                radial-gradient(circle at -5% -8%, rgba(241, 179, 79, 0.32), transparent 23rem),
                radial-gradient(circle at 108% 6%, rgba(20, 125, 116, 0.18), transparent 24rem),
                radial-gradient(circle at 78% 84%, rgba(219, 106, 50, 0.14), transparent 22rem),
                linear-gradient(180deg, #fbf8f3 0%, #f7f1e6 44%, #fdfbf7 100%) !important;
            color: var(--text) !important;
            font-family: "Palatino Linotype", "Microsoft YaHei UI", serif;
        }

        .stApp::before {
            content: "";
            position: fixed;
            inset: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(23, 49, 58, 0.03) 1px, transparent 1px),
                linear-gradient(90deg, rgba(23, 49, 58, 0.03) 1px, transparent 1px);
            background-size: 46px 46px;
            mask-image: radial-gradient(circle at center, black, transparent 78%);
            opacity: 0.55;
            z-index: 0;
        }

        * {
            font-family: "Palatino Linotype", "Microsoft YaHei UI", serif;
        }

        h1, h2, h3, h4,
        .brand-title,
        .hero-title,
        .section-title,
        .input-title,
        .stat-value,
        .score-value {
            font-family: "Bodoni MT", "Book Antiqua", "Microsoft YaHei UI", serif !important;
        }

        @keyframes panelRise {
            0% {
                opacity: 0;
                transform: translateY(18px);
            }
            100% {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes softDrift {
            0%, 100% {
                transform: translate3d(0, 0, 0);
            }
            50% {
                transform: translate3d(0, -6px, 0);
            }
        }

        @keyframes markSweep {
            0% {
                opacity: 0.35;
                transform: scaleX(0.72);
            }
            100% {
                opacity: 1;
                transform: scaleX(1);
            }
        }

        .block-container {
            position: relative;
            z-index: 1;
            max-width: 1520px;
            padding-top: 0.8rem !important;
            padding-right: 1.35rem !important;
            padding-bottom: 3rem !important;
            padding-left: 1.35rem !important;
        }

        [data-testid="stSidebar"] {
            background: transparent !important;
            border-right: 0 !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--line) !important;
            border-radius: 28px !important;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(251, 247, 240, 0.92)) !important;
            box-shadow: var(--shadow-soft) !important;
            overflow: hidden;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            animation: panelRise 0.62s ease both;
        }

        label,
        .stFileUploader label,
        .stTextArea label {
            color: var(--text) !important;
            font-weight: 650 !important;
        }

        .control-center {
            position: fixed;
            top: 0;
            bottom: 0;
            left: 0;
            width: clamp(244px, 19vw, 286px);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 1.35rem 1.1rem 1.15rem 1.2rem;
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            background:
                linear-gradient(180deg, rgba(23, 49, 58, 0.98), rgba(13, 33, 39, 0.98)),
                radial-gradient(circle at 14% 2%, rgba(241, 179, 79, 0.22), transparent 18rem),
                radial-gradient(circle at 88% 92%, rgba(20, 125, 116, 0.18), transparent 16rem);
            box-shadow: 18px 0 46px rgba(8, 20, 24, 0.18);
            z-index: 24;
            overflow-y: auto;
            animation: panelRise 0.58s ease both;
        }

        .control-center::before {
            content: "";
            position: absolute;
            inset: 1rem 1rem auto 1rem;
            height: 180px;
            border-radius: 24px;
            background:
                radial-gradient(circle at 18% 20%, rgba(241, 179, 79, 0.20), transparent 52%),
                radial-gradient(circle at 82% 84%, rgba(20, 125, 116, 0.18), transparent 48%);
            pointer-events: none;
        }

        .control-center::after {
            content: "ISSUE 01";
            position: absolute;
            top: 1.4rem;
            right: 0.7rem;
            writing-mode: vertical-rl;
            text-orientation: mixed;
            color: rgba(255, 255, 255, 0.26);
            font-family: "Bahnschrift", "Microsoft YaHei UI", sans-serif;
            font-size: 0.68rem;
            letter-spacing: 0.26em;
        }

        .control-center > div {
            position: relative;
            z-index: 1;
        }

        .brand-row {
            display: flex;
            align-items: center;
            gap: 0.9rem;
            margin-bottom: 1rem;
        }

        .brand-shell {
            margin-bottom: 1.1rem;
        }

        .brand-icon {
            width: 3rem;
            height: 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 20px;
            background: linear-gradient(135deg, var(--accent-3), var(--accent));
            color: #ffffff;
            font-size: 1.18rem;
            box-shadow: 0 16px 28px rgba(219, 106, 50, 0.24);
        }

        .brand-sub {
            color: rgba(255, 255, 255, 0.62);
            font-size: 0.74rem;
            line-height: 1.35;
            text-transform: uppercase;
            letter-spacing: 0.18em;
        }

        .brand-title {
            color: #ffffff;
            font-size: 1.08rem;
            font-weight: 760;
            letter-spacing: 0.03em;
        }

        .side-mini-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.68rem;
            margin-bottom: 1.2rem;
        }

        .side-mini {
            padding: 0.82rem 0.78rem;
            border-radius: 18px;
            border: 1px solid rgba(255, 255, 255, 0.08);
            background: rgba(255, 255, 255, 0.05);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
            transition: transform 0.18s ease, background 0.18s ease;
        }

        .side-mini:hover {
            transform: translateY(-1px);
            background: rgba(255, 255, 255, 0.08);
        }

        .side-mini span {
            display: block;
            color: rgba(255, 255, 255, 0.46);
            font-size: 0.64rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            margin-bottom: 0.24rem;
        }

        .side-mini strong {
            display: block;
            color: #f7faf9;
            font-size: 0.86rem;
            line-height: 1.45;
            font-weight: 700;
        }

        .side-item {
            position: relative;
            padding: 1rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.04));
            backdrop-filter: blur(10px);
            margin-bottom: 0.72rem;
            overflow: hidden;
            animation: panelRise 0.68s ease both;
        }

        .side-item::after {
            content: "";
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            height: 3px;
            background: linear-gradient(90deg, rgba(241, 179, 79, 0.0), rgba(241, 179, 79, 0.7), rgba(20, 125, 116, 0.0));
        }

        .side-label {
            color: rgba(255, 255, 255, 0.52);
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 0.35rem;
        }

        .side-value {
            color: #eff4f2;
            font-size: 0.92rem;
            line-height: 1.58;
        }

        .agent-note {
            padding: 1rem 1.05rem;
            border: 1px solid rgba(255, 255, 255, 0.10);
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(241, 179, 79, 0.14), rgba(20, 125, 116, 0.12));
            color: #edf4f1;
            line-height: 1.7;
            font-size: 0.87rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08);
        }

        .main-workspace {
            position: relative;
            margin-left: 0;
            padding-top: 0.45rem;
        }

        .main-workspace::before {
            content: "RESUME EDITORIAL DESK";
            position: absolute;
            top: -0.55rem;
            right: 0.4rem;
            color: rgba(23, 49, 58, 0.32);
            font-family: "Bahnschrift", "Microsoft YaHei UI", sans-serif;
            font-size: 0.68rem;
            letter-spacing: 0.24em;
        }

        .section-block {
            position: relative;
            padding: 1.08rem 0 1.35rem;
            border-top: 1px dashed rgba(23, 49, 58, 0.12);
            animation: panelRise 0.64s ease both;
        }

        .section-block.first {
            border-top: 0;
            padding-top: 0;
        }

        .hero-card {
            position: relative;
            overflow: hidden;
            padding: 2rem;
            border: 1px solid rgba(23, 49, 58, 0.08);
            border-radius: 34px;
            background:
                repeating-linear-gradient(
                    180deg,
                    rgba(130, 105, 78, 0.045) 0,
                    rgba(130, 105, 78, 0.045) 1px,
                    transparent 1px,
                    transparent 34px
                ),
                linear-gradient(145deg, rgba(255, 255, 255, 0.96), rgba(255, 248, 241, 0.92));
            box-shadow: 0 28px 65px rgba(23, 49, 58, 0.10);
            margin-bottom: 1rem;
            animation: panelRise 0.74s ease both;
        }

        .hero-card::before {
            content: "";
            position: absolute;
            left: -4rem;
            bottom: -5rem;
            width: 18rem;
            height: 18rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(20, 125, 116, 0.16), transparent 64%);
            pointer-events: none;
        }

        .hero-card::after {
            content: "";
            position: absolute;
            right: -6rem;
            top: -8rem;
            width: 22rem;
            height: 22rem;
            border-radius: 999px;
            background: radial-gradient(circle, rgba(219, 106, 50, 0.20), transparent 64%);
            pointer-events: none;
        }

        .hero-grid {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(0, 1.35fr) minmax(240px, 0.85fr);
            gap: 1.5rem;
            align-items: stretch;
        }

        .hero-kicker-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.85rem;
            flex-wrap: wrap;
        }

        .hero-pill {
            display: inline-flex;
            align-items: center;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            border: 1px solid rgba(20, 125, 116, 0.18);
            background: rgba(20, 125, 116, 0.10);
            color: var(--accent-2);
            font-size: 0.72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 0;
        }

        .hero-edition {
            color: var(--muted);
            font-family: "Bahnschrift", "Microsoft YaHei UI", sans-serif;
            font-size: 0.72rem;
            letter-spacing: 0.22em;
            text-transform: uppercase;
        }

        .hero-title {
            max-width: 760px;
            color: var(--text);
            font-size: clamp(2.5rem, 4vw, 3.9rem);
            line-height: 0.98;
            letter-spacing: -0.04em;
            margin: 0;
        }

        .hero-subtitle {
            max-width: 42rem;
            color: var(--muted-strong);
            font-size: 1.02rem;
            line-height: 1.75;
            margin: 0.9rem 0 1.15rem;
        }

        .hero-manifesto {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            margin-bottom: 1.05rem;
            color: var(--accent);
            font-size: 0.9rem;
            font-weight: 700;
            padding-bottom: 0.15rem;
            border-bottom: 1px solid rgba(219, 106, 50, 0.16);
        }

        .hero-manifesto::before {
            content: "";
            width: 1.1rem;
            height: 0.36rem;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--accent-3), var(--accent));
            animation: markSweep 0.8s ease both;
            transform-origin: left center;
        }

        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.62rem;
        }

        .chip {
            display: inline-flex;
            padding: 0.56rem 0.82rem;
            border-radius: 999px;
            border: 1px solid rgba(23, 49, 58, 0.08);
            background: rgba(255, 255, 255, 0.80);
            color: var(--text);
            font-size: 0.83rem;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
        }

        .hero-stats {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.82rem;
            align-content: start;
        }

        .stat-pill {
            padding: 1rem;
            border: 1px solid rgba(23, 49, 58, 0.08);
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 243, 236, 0.94));
            box-shadow: 0 12px 24px rgba(23, 49, 58, 0.05);
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            animation: panelRise 0.72s ease both;
        }

        .stat-pill:nth-child(1) {
            transform: translateY(12px);
        }

        .stat-pill:nth-child(2) {
            transform: translateY(0);
        }

        .stat-pill:nth-child(3) {
            transform: translateY(20px);
        }

        .stat-pill:nth-child(4) {
            transform: translateY(8px);
        }

        .stat-pill:hover {
            transform: translateY(-2px);
            box-shadow: 0 18px 30px rgba(23, 49, 58, 0.08);
        }

        .stat-label {
            color: var(--muted);
            font-size: 0.68rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            margin-bottom: 0.45rem;
        }

        .stat-value {
            color: var(--text);
            font-size: 1rem;
            font-weight: 740;
        }

        .section-label {
            color: var(--accent);
            font-size: 0.72rem;
            font-weight: 820;
            text-transform: uppercase;
            letter-spacing: 0.24em;
            margin-bottom: 0.42rem;
        }

        .section-title {
            color: var(--text);
            font-size: 1.7rem;
            font-weight: 760;
            margin-bottom: 0.25rem;
        }

        .section-desc {
            max-width: 42rem;
            color: var(--muted);
            font-size: 0.93rem;
            line-height: 1.72;
            margin-bottom: 0.9rem;
        }

        .input-title {
            color: var(--text);
            font-size: 1.2rem;
            font-weight: 760;
            margin-bottom: 0.25rem;
        }

        .input-desc {
            color: var(--muted-strong);
            font-size: 0.88rem;
            line-height: 1.66;
            margin-bottom: 0.8rem;
        }

        .status-note {
            padding: 0.95rem 1rem;
            border-radius: 18px;
            border: 1px solid rgba(219, 106, 50, 0.16);
            background: linear-gradient(135deg, rgba(241, 179, 79, 0.15), rgba(255, 255, 255, 0.92));
            color: var(--text);
            font-size: 0.92rem;
            line-height: 1.72;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.76);
            animation: panelRise 0.7s ease both;
        }

        .result-card {
            position: relative;
            min-height: 150px;
            padding: 1.2rem;
            border: 1px solid rgba(23, 49, 58, 0.08);
            border-radius: 26px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(250, 247, 242, 0.92));
            box-shadow: 0 18px 36px rgba(23, 49, 58, 0.06);
            overflow: hidden;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
            animation: panelRise 0.76s ease both;
        }

        .result-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 22px 40px rgba(23, 49, 58, 0.08);
        }

        .result-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            height: 5px;
            background: linear-gradient(90deg, rgba(219, 106, 50, 0.0), rgba(219, 106, 50, 0.92), rgba(20, 125, 116, 0.65));
        }

        .result-card.good::before {
            background: linear-gradient(90deg, rgba(21, 122, 110, 0.0), rgba(21, 122, 110, 0.78), rgba(104, 211, 145, 0.62));
        }

        .result-card.warn::before {
            background: linear-gradient(90deg, rgba(217, 119, 6, 0.0), rgba(217, 119, 6, 0.82), rgba(244, 181, 104, 0.62));
        }

        .result-label {
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin-bottom: 0.75rem;
        }

        .result-text {
            color: var(--text);
            font-size: 0.94rem;
            line-height: 1.8;
        }

        .score-card {
            padding: 1.25rem;
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 30px;
            background: linear-gradient(160deg, rgba(23, 49, 58, 0.98), rgba(32, 74, 69, 0.92));
            box-shadow: 0 24px 50px rgba(23, 49, 58, 0.18);
            animation: panelRise 0.76s ease both;
        }

        .score-card .result-label,
        .score-card .result-text,
        .score-card .score-foot {
            color: rgba(255, 255, 255, 0.78) !important;
        }

        .score-row {
            display: flex;
            align-items: center;
            gap: 1.1rem;
        }

        .score-ring {
            width: 8rem;
            height: 8rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            background:
                radial-gradient(circle at center, rgba(18, 36, 41, 1) 56%, transparent 57%),
                conic-gradient(from 210deg, var(--accent-3), var(--accent), var(--accent-2), rgba(255, 255, 255, 0.18));
            box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
            animation: softDrift 5s ease-in-out infinite;
        }

        .score-value {
            color: #ffffff;
            font-size: 2.6rem;
            font-weight: 820;
            line-height: 1;
        }

        .score-foot {
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            margin-top: 0.25rem;
        }

        .download-shell {
            padding: 1rem 1.1rem;
            border-radius: 22px;
            border: 1px solid rgba(20, 125, 116, 0.18);
            background: linear-gradient(135deg, rgba(20, 125, 116, 0.12), rgba(255, 255, 255, 0.94));
            color: var(--text);
            line-height: 1.72;
            margin: 1rem 0 0.85rem;
        }

        .result-kicker {
            color: var(--accent);
            font-size: 0.72rem;
            font-weight: 820;
            text-transform: uppercase;
            letter-spacing: 0.22em;
            margin-bottom: 0.45rem;
        }

        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 18px !important;
            border: 1px solid rgba(219, 106, 50, 0.20) !important;
            background: linear-gradient(135deg, var(--accent-3) 0%, var(--accent) 100%) !important;
            color: #ffffff !important;
            font-weight: 800 !important;
            letter-spacing: 0.02em;
            min-height: 3.1rem;
            box-shadow: 0 18px 28px rgba(219, 106, 50, 0.18);
            transition: transform 0.18s ease, box-shadow 0.18s ease, filter 0.18s ease;
        }

        div.stButton > button:hover,
        div.stDownloadButton > button:hover {
            transform: translateY(-1px);
            filter: saturate(1.06);
            box-shadow: 0 22px 34px rgba(219, 106, 50, 0.20);
        }

        div.stButton > button:focus,
        div.stDownloadButton > button:focus {
            box-shadow: 0 0 0 0.18rem rgba(219, 106, 50, 0.14), 0 18px 28px rgba(219, 106, 50, 0.18);
        }

        [data-testid="stFileUploader"] {
            padding: 0.85rem;
            border-radius: 22px;
            border: 1px dashed rgba(23, 49, 58, 0.16);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(248, 243, 236, 0.88));
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.85);
        }

        [data-testid="stFileUploader"] * {
            color: var(--text) !important;
        }

        [data-testid="stFileUploader"] section {
            border: 0 !important;
            background: rgba(255, 255, 255, 0.72) !important;
            border-radius: 16px !important;
            padding: 1rem !important;
        }

        [data-testid="stFileUploader"] button {
            border-radius: 14px !important;
            background: rgba(23, 49, 58, 0.06) !important;
            color: var(--text) !important;
            border: 1px solid rgba(23, 49, 58, 0.10) !important;
            box-shadow: none !important;
        }

        .stTextArea textarea,
        .stTextInput input,
        textarea,
        input {
            border-radius: 18px !important;
            background: rgba(255, 255, 255, 0.92) !important;
            color: var(--text) !important;
            border: 1px solid rgba(23, 49, 58, 0.12) !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.80), 0 10px 22px rgba(23, 49, 58, 0.04);
        }

        .stTextArea textarea:focus,
        .stTextInput input:focus,
        textarea:focus,
        input:focus {
            border-color: rgba(219, 106, 50, 0.40) !important;
            box-shadow: 0 0 0 0.18rem rgba(219, 106, 50, 0.12), 0 12px 26px rgba(23, 49, 58, 0.06);
        }

        [data-testid="stExpander"] {
            border: 1px solid rgba(23, 49, 58, 0.10);
            border-radius: 24px;
            background: rgba(255, 255, 255, 0.86);
            box-shadow: 0 14px 30px rgba(23, 49, 58, 0.06);
            overflow: hidden;
        }

        details summary {
            font-weight: 720;
            color: var(--text);
        }

        div[data-testid="stProgressBar"] > div {
            background: rgba(23, 49, 58, 0.08) !important;
            border-radius: 999px !important;
        }

        div[data-testid="stProgressBar"] div[role="progressbar"] {
            background: linear-gradient(90deg, var(--accent-3), var(--accent), var(--accent-2)) !important;
            border-radius: 999px !important;
        }

        [data-testid="stAlert"] {
            border-radius: 20px !important;
            border: 1px solid rgba(23, 49, 58, 0.08) !important;
            background: rgba(255, 255, 255, 0.88) !important;
            box-shadow: 0 12px 24px rgba(23, 49, 58, 0.05);
        }

        [data-testid="stAlert"] * {
            color: var(--text) !important;
        }

        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-thumb {
            background: rgba(23, 49, 58, 0.22);
            border-radius: 999px;
        }

        ::-webkit-scrollbar-track {
            background: transparent;
        }

        @media (max-width: 1180px) {
            .block-container {
                padding-right: 1rem !important;
                padding-left: 1rem !important;
            }

            .control-center {
                position: relative;
                width: auto;
                min-height: auto;
                height: auto;
                border-radius: 26px;
                margin-bottom: 1rem;
                overflow: visible;
            }

            .hero-grid {
                grid-template-columns: 1fr;
            }

            .hero-title {
                font-size: clamp(2.2rem, 10vw, 3rem);
            }

            .main-workspace::before,
            .control-center::after {
                display: none;
            }
        }

        @media (max-width: 820px) {
            .hero-card {
                padding: 1.45rem;
                border-radius: 28px;
            }

            .hero-stats {
                grid-template-columns: 1fr;
            }

            .hero-kicker-row {
                flex-direction: column;
                align-items: flex-start;
            }

            .side-mini-grid {
                grid-template-columns: 1fr;
            }

            .stat-pill,
            .stat-pill:hover {
                transform: none;
            }

            .score-row {
                flex-direction: column;
                align-items: flex-start;
            }

            .score-ring {
                width: 7rem;
                height: 7rem;
            }

            .section-block {
                padding: 0.9rem 0 1.12rem;
            }

            div.stButton > button,
            div.stDownloadButton > button {
                min-height: 2.9rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    """初始化页面需要保存的状态。"""
    default_values = {
        "analysis_result": None,
        "optimized_result": None,
        "step_records": [],
        "pipeline_error": "",
    }
    for key, value in default_values.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_all_state():
    """开始新的匹配分析前清空旧结果。"""
    st.session_state["analysis_result"] = None
    st.session_state["optimized_result"] = None
    st.session_state["step_records"] = []
    st.session_state["pipeline_error"] = ""


def reset_optimize_state():
    """开始优化前只清空优化结果，保留匹配分析结果。"""
    st.session_state["optimized_result"] = None
    st.session_state["pipeline_error"] = ""


def html_list(items):
    """把列表内容转换成首页卡片中的简短 HTML。"""
    if isinstance(items, list) and items:
        return "<br>".join(f"• {escape(str(item))}" for item in items[:5])
    if items:
        return escape(str(items))
    return "暂无内容"


def render_section_label(kicker, title, desc):
    """统一渲染区域标题。"""
    desc_html = f'<div class="section-desc">{escape(desc)}</div>' if desc else ""
    st.markdown(
        f"""
        <div class="section-label">{escape(kicker)}</div>
        <div class="section-title">{escape(title)}</div>
        {desc_html}
        """,
        unsafe_allow_html=True,
    )


def render_result_card(title, content, tone=""):
    """渲染结果摘要卡片。"""
    tone_class = f" {tone}" if tone else ""
    st.markdown(
        f"""
        <div class="result-card{tone_class}">
            <div class="result-label">{escape(title)}</div>
            <div class="result-text">{html_list(content)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stat(label, value):
    """渲染 Hero 和侧栏中的小指标。"""
    st.markdown(
        f"""
        <div class="stat-pill">
            <div class="stat-label">{escape(label)}</div>
            <div class="stat-value">{escape(str(value))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def show_step_records(records):
    """展示每一步是否成功。"""
    if not records:
        st.markdown(
            '<div class="status-note">等待任务开始。执行后会展示每一步的状态。</div>',
            unsafe_allow_html=True,
        )
        return

    for record in records:
        step_name = record.get("步骤", "未知步骤")
        status = record.get("状态", "未知")
        detail = record.get("说明", "")

        if status == "成功":
            st.success(f"{step_name}：成功")
        elif status == "失败":
            st.error(f"{step_name}：失败。{detail}")
        else:
            st.info(f"{step_name}：{status}")


def get_match_score(match_analysis):
    """把模型返回的匹配分数转换成数字。"""
    score = match_analysis.get("match_score", 0)
    try:
        return int(score)
    except (TypeError, ValueError):
        return 0


def show_match_result(analysis_result):
    """展示第一阶段的匹配度分析结果。"""
    match_plan = analysis_result.get("match_plan", {})
    match_analysis = match_plan.get("match_analysis", {})
    score = get_match_score(match_analysis)
    conclusion = match_analysis.get("conclusion", "暂无结论")

    score_col, conclusion_col = st.columns([0.9, 1.35])
    with score_col:
        st.markdown(
            f"""
            <div class="score-card">
            <div class="result-label">匹配分数</div>
                <div class="score-row">
                    <div class="score-ring">
                        <div class="score-value">{score}</div>
                        <div class="score-foot">/ 100</div>
                    </div>
                    <div class="result-text">
                        阈值：{MATCH_THRESHOLD}<br>
                        {'建议优化后投递' if score < MATCH_THRESHOLD else '可直接投递'}
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with conclusion_col:
        render_result_card("一句话结论", conclusion)

    st.write("")
    left_col, right_col = st.columns(2)
    with left_col:
        render_result_card("主要优势", match_analysis.get("main_strengths"), "good")
    with right_col:
        render_result_card("主要缺口", match_analysis.get("main_gaps"), "warn")

    if score < MATCH_THRESHOLD:
        st.warning(f"当前匹配分数低于 {MATCH_THRESHOLD}，建议进入优化生成阶段。")
    else:
        st.success(f"当前匹配分数不低于 {MATCH_THRESHOLD}，匹配度较高，暂不建议自动生成优化简历。")


def show_detail_expander(result, loop_result=None):
    """默认折叠中间过程，避免首页信息过载。"""
    with st.expander("查看调试详情与结构化结果"):
        st.subheader("原始 JD 文本")
        st.text_area(
            "JD 文本",
            value=result.get("jd_text", ""),
            height=150,
            disabled=True,
        )

        st.subheader("原始简历提取文本")
        st.text_area(
            "简历文本",
            value=result.get("resume_text", ""),
            height=150,
            disabled=True,
        )

        st.subheader("结构化简历")
        st.json(result.get("structured_resume", {}))

        st.subheader("结构化 JD")
        st.json(result.get("structured_jd", {}))

        st.subheader("匹配分析与改写计划")
        st.json(result.get("match_plan", {}))

        if result.get("rewritten_resume"):
            st.subheader("新版简历内容")
            st.json(result.get("rewritten_resume", {}))

        if loop_result:
            st.subheader("loop 检查结果")
            st.json(loop_result)


def show_optimized_result(result):
    """展示第二阶段生成后的最终结果。"""
    match_plan = result.get("match_plan", {})
    rewrite_plan = match_plan.get("rewrite_plan", {})
    loop_result = result.get("loop_result", {})

    st.markdown('<div class="result-kicker">交付结果</div>', unsafe_allow_html=True)
    st.subheader("优化简历已准备好")

    left_col, right_col = st.columns(2)
    with left_col:
        render_result_card("优化摘要", rewrite_plan.get("enhance_sections"))
    with right_col:
        render_result_card("建议补入关键词", rewrite_plan.get("keywords_to_add"))

    if result.get("pdf_bytes"):
        file_time = datetime.now().strftime("%Y%m%d_%H%M")
        st.markdown(
            '<div class="download-shell"><strong>交付文件</strong><br>新版 PDF 简历已生成，可以直接下载。</div>',
            unsafe_allow_html=True,
        )
        st.download_button(
            "下载优化后 PDF",
            data=result["pdf_bytes"],
            file_name=f"rewritten_resume_{file_time}.pdf",
            mime="application/pdf",
            type="primary",
            use_container_width=True,
        )

    show_detail_expander(result, loop_result)


def update_step(step_records, progress_bar, total_steps, step_name, status, detail=""):
    """记录步骤状态并更新进度条。"""
    step_records.append({"步骤": step_name, "状态": status, "说明": detail})
    st.session_state["step_records"] = step_records
    progress_bar.progress(min(len(step_records) / total_steps, 1.0))


def run_step(step_records, progress_bar, total_steps, current_step_area, step_name, action):
    """执行单个步骤，失败时停止当前流程。"""
    current_step_area.info(f"当前步骤：{step_name}")
    try:
        value = action()
    except Exception as error:
        update_step(step_records, progress_bar, total_steps, step_name, "失败", str(error))
        raise RuntimeError(f"{step_name}失败：{error}") from error

    update_step(step_records, progress_bar, total_steps, step_name, "成功")
    return value


def run_match_analysis(resume_pdf, jd_image, jd_text, progress_bar, current_step_area):
    """第一阶段：只完成匹配度分析。"""
    if resume_pdf is None:
        raise RuntimeError("请先上传 PDF 简历。")

    if jd_image is None and not jd_text.strip():
        raise RuntimeError("请上传 JD 图片，或直接粘贴文本 JD。")

    step_records = []
    total_steps = len(ANALYSIS_STEPS)

    resume_text = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "解析简历 PDF",
        lambda: extract_text_from_pdf(resume_pdf),
    )
    if not resume_text:
        raise RuntimeError("没有从 PDF 中提取到文本。请确认 PDF 不是纯图片扫描件。")

    def get_jd_text():
        if jd_image is not None:
            return extract_jd_from_image(jd_image)
        return jd_text.strip()

    final_jd_text = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "提取 JD 内容",
        get_jd_text,
    )
    if not final_jd_text:
        raise RuntimeError("没有得到有效 JD 内容。请检查 JD 图片是否清晰，或直接粘贴文本 JD。")

    structured_resume = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "结构化简历",
        lambda: parse_resume_structure(resume_text),
    )
    structured_jd = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "结构化 JD",
        lambda: parse_jd_structure(final_jd_text),
    )
    match_plan = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "匹配分析",
        lambda: generate_match_and_rewrite_plan(structured_resume, structured_jd),
    )

    progress_bar.progress(1.0)
    current_step_area.success("匹配度分析已完成。")

    return {
        "resume_text": resume_text,
        "jd_text": final_jd_text,
        "structured_resume": structured_resume,
        "structured_jd": structured_jd,
        "match_plan": match_plan,
    }


def run_resume_optimization(analysis_result, progress_bar, current_step_area):
    """第二阶段：在低匹配分数时生成优化简历和新版 PDF。"""
    if not analysis_result:
        raise RuntimeError("请先完成匹配度分析。")

    existing_records = st.session_state.get("step_records", [])
    step_records = list(existing_records)
    total_steps = len(existing_records) + len(OPTIMIZE_STEPS)

    structured_resume = analysis_result["structured_resume"]
    structured_jd = analysis_result["structured_jd"]
    match_plan = analysis_result["match_plan"]

    update_step(step_records, progress_bar, total_steps, "生成改写计划", "成功")

    rewritten_resume = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "按 section 改写",
        lambda: generate_section_rewrite(structured_resume, structured_jd, match_plan),
    )
    loop_result = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "检查与修正 loop",
        lambda: run_review_loop(structured_resume, structured_jd, rewritten_resume),
    )
    final_resume = loop_result.get("final_resume", rewritten_resume)

    pdf_bytes = run_step(
        step_records,
        progress_bar,
        total_steps,
        current_step_area,
        "生成新版 PDF",
        lambda: render_resume_pdf(final_resume),
    )

    progress_bar.progress(1.0)
    current_step_area.success("优化简历已生成。")

    return {
        **analysis_result,
        "rewritten_resume": final_resume,
        "loop_result": loop_result,
        "pdf_bytes": pdf_bytes,
    }


st.set_page_config(
    page_title="Resume Rewrite Agent MVP",
    page_icon="💼",
    layout="wide",
)

inject_frontend_design_theme()
init_state()

analysis_result = st.session_state["analysis_result"]
optimized_result = st.session_state["optimized_result"]

current_score = "--"
if analysis_result:
    current_score = get_match_score(analysis_result.get("match_plan", {}).get("match_analysis", {}))

shell_left, shell_right = st.columns([0.22, 0.78], gap="large")

with shell_left:
    st.markdown(
        f"""
        <aside class="control-center">
            <div>
                <div class="brand-shell">
                    <div class="brand-row">
                        <div class="brand-icon">✦</div>
                        <div>
                            <div class="brand-sub">Resume Editorial Desk</div>
                            <div class="brand-title">控制中心</div>
                        </div>
                    </div>
                    <div class="side-mini-grid">
                        <div class="side-mini">
                            <span>Issue</span>
                            <strong>Match First</strong>
                        </div>
                        <div class="side-mini">
                            <span>Flow</span>
                            <strong>先分析 再改稿</strong>
                        </div>
                    </div>
                </div>
                <div class="side-item">
                    <div class="side-label">当前模式</div>
                    <div class="side-value">岗位匹配诊断 + 条件触发改写</div>
                </div>
                <div class="side-item">
                    <div class="side-label">审稿阈值</div>
                    <div class="side-value">匹配分低于 {MATCH_THRESHOLD} 分时进入重写建议</div>
                </div>
                <div class="side-item">
                    <div class="side-label">实时分数</div>
                    <div class="side-value">{current_score}</div>
                </div>
                <div class="side-item">
                    <div class="side-label">决策路径</div>
                    <div class="side-value">解析材料，结构化判断，再决定是否进入优化稿</div>
                </div>
            </div>
            <div class="agent-note">
                <strong>编辑提示</strong><br>
                先判断这份简历适不适合投递，再决定要不要动笔重写。
            </div>
        </aside>
        """,
        unsafe_allow_html=True,
    )

with shell_right:
    st.markdown('<div class="main-workspace">', unsafe_allow_html=True)
    st.markdown('<div class="section-block first">', unsafe_allow_html=True)
    st.markdown(
        """
        <main>
            <section class="hero-card">
                <div class="hero-grid">
                    <div>
                        <div class="hero-kicker-row">
                            <div class="hero-pill">Resume Editorial Studio</div>
                            <div class="hero-edition">Issue 01 · Match First</div>
                        </div>
                        <h1 class="hero-title">把简历当成一篇要投版的稿件来打磨</h1>
                        <p class="hero-subtitle">
                            上传 PDF 简历和岗位 JD，工作台会像编辑部一样先审稿、找差距，再决定是否进入改写流程。
                        </p>
                        <div class="hero-manifesto">先判断适配度，再决定是否重写。</div>
                        <div class="chip-row">
                            <span class="chip">PDF 简历解析</span>
                            <span class="chip">图片 JD 识别</span>
                            <span class="chip">智能匹配分析</span>
                            <span class="chip">改写检查循环</span>
                            <span class="chip">新版 PDF 导出</span>
                        </div>
                    </div>
                    <div class="hero-stats">
                        <div class="stat-pill"><div class="stat-label">审稿材料</div><div class="stat-value">PDF + 图片 + 文本</div></div>
                        <div class="stat-pill"><div class="stat-label">判断原则</div><div class="stat-value">匹配优先</div></div>
                        <div class="stat-pill"><div class="stat-label">改稿粒度</div><div class="stat-value">section 级重写</div></div>
                        <div class="stat-pill"><div class="stat-label">最终交付</div><div class="stat-value">新版 PDF 简历</div></div>
                    </div>
                </div>
            </section>
        </main>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-block">', unsafe_allow_html=True)
    render_section_label(
        "Input",
        "资料编审区",
        "先放入原始材料，工作台会按同一套审稿逻辑处理简历与岗位信息。",
    )

    input_left, input_right = st.columns([0.48, 0.52], gap="large")
    with input_left:
        with st.container(border=True):
            st.markdown('<div class="input-title">PDF 简历</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="input-desc">上传原始简历 PDF。</div>',
                unsafe_allow_html=True,
            )
            uploaded_pdf = st.file_uploader(
                "上传 PDF 简历",
                type=["pdf"],
                help="建议上传文本型 PDF，扫描件可能无法完整提取文字。",
            )

    with input_right:
        with st.container(border=True):
            st.markdown('<div class="input-title">岗位 JD</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="input-desc">上传招聘截图，或粘贴文本 JD。</div>',
                unsafe_allow_html=True,
            )
            uploaded_jd_image = st.file_uploader(
                "上传 JD 图片或招聘截图",
                type=["png", "jpg", "jpeg", "webp", "bmp"],
                help="适合招聘平台截图、网页截图或职位图片。",
            )
            pasted_jd_text = st.text_area(
                "或直接粘贴文本 JD",
                height=150,
                placeholder="粘贴岗位职责、任职要求、优先条件、技能关键词等内容。",
            )

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-block">', unsafe_allow_html=True)
    render_section_label(
        "Action",
        "执行入口",
        "先完成匹配分析。只有在低匹配分场景下，才建议继续进入改写流程。",
    )

    action_col, hint_col = st.columns([0.42, 0.58], gap="large")
    with action_col:
        analyze_button = st.button(
            "开始分析匹配度",
            type="primary",
            use_container_width=True,
        )
    with hint_col:
        st.markdown(
            f'<div class="status-note">低于 {MATCH_THRESHOLD} 分才开放优化生成。</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-block">', unsafe_allow_html=True)
    render_section_label(
        "Execution",
        "执行轨迹",
        "每一步的提取、结构化和生成状态都会记录在这里，方便你判断当前卡在哪一环。",
    )

    has_any_result = st.session_state["analysis_result"] or st.session_state["optimized_result"]
    progress_bar = st.progress(1.0 if has_any_result else 0.0)
    current_step_area = st.empty()

    if analyze_button:
        reset_all_state()
        try:
            st.session_state["analysis_result"] = run_match_analysis(
                uploaded_pdf,
                uploaded_jd_image,
                pasted_jd_text,
                progress_bar,
                current_step_area,
            )
        except RuntimeError as error:
            st.session_state["pipeline_error"] = str(error)
            current_step_area.error(str(error))

    if st.session_state["pipeline_error"]:
        st.error(st.session_state["pipeline_error"])

    with st.container(border=True):
        show_step_records(st.session_state["step_records"])

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-block">', unsafe_allow_html=True)
    render_section_label(
        "Result",
        "结果看板",
        "先看分数、结论和主要缺口，再决定是否要让系统继续生成优化稿。",
    )

    analysis_result = st.session_state["analysis_result"]
    optimized_result = st.session_state["optimized_result"]

    if analysis_result:
        show_match_result(analysis_result)

        score = get_match_score(analysis_result.get("match_plan", {}).get("match_analysis", {}))
        if score < MATCH_THRESHOLD:
            optimize_button = st.button(
                "生成优化简历",
                type="primary",
                use_container_width=True,
            )

            if optimize_button:
                reset_optimize_state()
                try:
                    st.session_state["optimized_result"] = run_resume_optimization(
                        analysis_result,
                        progress_bar,
                        current_step_area,
                    )
                except RuntimeError as error:
                    st.session_state["pipeline_error"] = str(error)
                    current_step_area.error(str(error))
        else:
            st.info("当前匹配度较高，暂不建议自动生成优化简历。")

        if not st.session_state["optimized_result"]:
            show_detail_expander(analysis_result)

    if st.session_state["optimized_result"]:
        st.write("")
        show_optimized_result(st.session_state["optimized_result"])
    elif not analysis_result:
        st.markdown(
            '<div class="status-note">完成匹配度分析后，这里会展示匹配分数、主要优势、主要缺口和一句话结论。</div>',
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
