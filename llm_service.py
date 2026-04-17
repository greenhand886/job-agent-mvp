import json
import os

from prompts import SYSTEM_PROMPT, build_user_prompt

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-plus"
API_KEY_NAMES = ("DASHSCOPE_API_KEY", "BAILIAN_API_KEY", "OPENAI_API_KEY")


def get_api_key():
    """按顺序从环境变量中读取 API Key。"""
    for key_name in API_KEY_NAMES:
        api_key = os.getenv(key_name)
        if api_key and api_key.strip():
            return api_key.strip()
    return None


def create_client():
    """创建阿里云百炼 OpenAI 兼容客户端。"""
    if OpenAI is None:
        raise RuntimeError("当前环境没有安装 openai SDK，请先安装后再运行。")

    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("没有找到 API Key。请先设置 DASHSCOPE_API_KEY、BAILIAN_API_KEY 或 OPENAI_API_KEY 中的任意一个环境变量。")

    return OpenAI(api_key=api_key, base_url=BASE_URL)


def parse_model_json(text):
    """解析模型返回的 JSON，兼容偶尔出现的代码块包裹。"""
    content = text.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    try:
        result = json.loads(content)
    except (json.JSONDecodeError, TypeError, AttributeError):
        raise ValueError("模型返回的内容不是标准 JSON，暂时无法展示分析结果。请重新点击开始分析再试。")

    if not isinstance(result, dict):
        raise ValueError("模型返回的内容不是标准 JSON，暂时无法展示分析结果。请重新点击开始分析再试。")

    return result


def analyze_job_match(jd_text, resume_text):
    """调用模型，并返回解析后的岗位匹配分析结果。"""
    client = create_client()
    user_prompt = build_user_prompt(jd_text, resume_text)

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
    except Exception:
        raise RuntimeError("接口调用失败，请检查 API Key、网络连接或阿里云百炼服务状态。")

    model_text = response.choices[0].message.content
    return parse_model_json(model_text)
