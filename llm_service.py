import base64
import json
import os

from prompts import (
    SYSTEM_PROMPT,
    build_final_check_prompt,
    build_jd_parse_prompt,
    build_match_prompt,
    build_resume_lines_prompt,
    build_rewrite_advice_prompt,
)

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-plus"
VISION_MODEL_NAME = "qwen-vl-plus"
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


def call_model(client, user_prompt):
    """调用一次文本模型，并返回解析后的 JSON。"""
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
    except Exception as error:
        raise RuntimeError("接口调用失败，请检查 API Key、网络连接或阿里云百炼服务状态。") from error

    model_text = response.choices[0].message.content
    return parse_model_json(model_text)


def call_vision_model(client, image_bytes, mime_type):
    """调用视觉模型，从招聘截图中提取 JD 文本。"""
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    image_url = f"data:{mime_type};base64,{image_base64}"

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请识别图片中的招聘信息，提取完整岗位 JD 文本。只返回提取出的中文内容，不要解释。",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": image_url},
                        },
                    ],
                }
            ],
            temperature=0.1,
        )
    except Exception as error:
        raise RuntimeError("图片 JD 解析失败，请检查图片格式、网络连接或阿里云百炼视觉模型服务状态。") from error

    return response.choices[0].message.content.strip()


def extract_jd_from_image(uploaded_image):
    """读取上传图片，并提取其中的招聘信息文本。"""
    client = create_client()
    uploaded_image.seek(0)
    image_bytes = uploaded_image.read()
    mime_type = uploaded_image.type or "image/png"
    return call_vision_model(client, image_bytes, mime_type)


def parse_jd(client, jd_text):
    """第1步：解析岗位 JD。"""
    prompt = build_jd_parse_prompt(jd_text)
    return call_model(client, prompt)


def analyze_match(client, jd_text, resume_text, jd_result):
    """第2步：分析简历与岗位的匹配情况。"""
    prompt = build_match_prompt(jd_text, resume_text, jd_result)
    return call_model(client, prompt)


def generate_rewrite_advice(client, jd_text, resume_text, match_result):
    """第3步：生成简历改写建议。"""
    prompt = build_rewrite_advice_prompt(jd_text, resume_text, match_result)
    return call_model(client, prompt)


def generate_resume_lines(client, resume_text, advice_result):
    """第4步：生成可直接粘贴到简历中的优化表述。"""
    prompt = build_resume_lines_prompt(resume_text, advice_result)
    return call_model(client, prompt)


def final_check(client, jd_result, match_result, advice_result, resume_lines_result):
    """第5步：自检并输出最终结论。"""
    prompt = build_final_check_prompt(
        jd_result,
        match_result,
        advice_result,
        resume_lines_result,
    )
    return call_model(client, prompt)


def run_agent_workflow(jd_text, resume_text, step_callback=None):
    """按 5 个步骤执行求职分析工作流。"""
    client = create_client()
    executed_steps = []

    def mark_step(step_name):
        executed_steps.append(step_name)
        if step_callback:
            step_callback(step_name)

    mark_step("第1步：解析岗位 JD")
    jd_result = parse_jd(client, jd_text)

    mark_step("第2步：分析简历与岗位的匹配情况")
    match_result = analyze_match(client, jd_text, resume_text, jd_result)

    mark_step("第3步：生成简历改写建议")
    advice_result = generate_rewrite_advice(client, jd_text, resume_text, match_result)

    mark_step("第4步：生成可直接粘贴到简历中的优化表述")
    resume_lines_result = generate_resume_lines(client, resume_text, advice_result)

    mark_step("第5步：自检并输出最终结论")
    final_result = final_check(
        client,
        jd_result,
        match_result,
        advice_result,
        resume_lines_result,
    )

    return {
        "执行步骤": executed_steps,
        "岗位关键词": jd_result.get("岗位关键词", []),
        "匹配分数": match_result.get("匹配分数", "暂无分数"),
        "你的优势": match_result.get("你的优势", []),
        "你的缺口": match_result.get("你的缺口", []),
        "一句话结论": final_result.get("一句话结论", "暂无结论"),
        "简历改写建议": advice_result.get("简历改写建议", []),
        "可直接粘贴到简历中的优化表述": resume_lines_result.get("可直接粘贴到简历中的优化表述", []),
    }


def analyze_job_match(jd_text, resume_text):
    """保留旧函数名，方便页面继续调用。"""
    return run_agent_workflow(jd_text, resume_text)
