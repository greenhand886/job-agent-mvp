SYSTEM_PROMPT = """
你是一个严谨的中文求职分析助手。
你只返回标准 JSON，不要返回 Markdown，不要返回解释文字。
如果某个字段没有足够信息，请返回空列表或简短说明，不要编造事实。
""".strip()


def build_jd_parse_prompt(jd_text):
    """第1步：生成岗位 JD 解析提示词。"""
    return f"""
请解析下面的岗位 JD，并只返回标准 JSON：
{{
  "岗位关键词": ["关键词1", "关键词2"],
  "岗位要求摘要": "用一句话概括岗位核心要求"
}}

岗位 JD：
{jd_text}
""".strip()


def build_match_prompt(jd_text, resume_text, jd_result):
    """第2步：生成岗位匹配分析提示词。"""
    return f"""
请根据岗位 JD、基础简历和岗位解析结果，分析候选人与岗位的匹配情况，并只返回标准 JSON：
{{
  "匹配分数": 0,
  "你的优势": ["优势1", "优势2"],
  "你的缺口": ["缺口1", "缺口2"]
}}

匹配分数必须是 0 到 100 的整数。

岗位解析结果：
{jd_result}

岗位 JD：
{jd_text}

基础简历：
{resume_text}
""".strip()


def build_rewrite_advice_prompt(jd_text, resume_text, match_result):
    """第3步：生成简历改写建议提示词。"""
    return f"""
请根据岗位 JD、基础简历和匹配分析结果，给出简历改写建议，并只返回标准 JSON：
{{
  "简历改写建议": ["建议1", "建议2", "建议3"]
}}

匹配分析结果：
{match_result}

岗位 JD：
{jd_text}

基础简历：
{resume_text}
""".strip()


def build_resume_lines_prompt(resume_text, advice_result):
    """第4步：生成可直接粘贴到简历中的优化表述提示词。"""
    return f"""
请根据基础简历和简历改写建议，生成可直接粘贴到简历中的优化表述，并只返回标准 JSON：
{{
  "可直接粘贴到简历中的优化表述": ["表述1", "表述2", "表述3"]
}}

要求：
1. 表述要具体、自然、适合简历。
2. 不要夸大经历，不要编造不存在的项目。

基础简历：
{resume_text}

简历改写建议：
{advice_result}
""".strip()


def build_final_check_prompt(jd_result, match_result, advice_result, resume_lines_result):
    """第5步：生成自检和最终结论提示词。"""
    return f"""
请自检前面几步的分析结果，并输出最终结论。只返回标准 JSON：
{{
  "一句话结论": "一句简短结论"
}}

岗位解析结果：
{jd_result}

匹配分析结果：
{match_result}

简历改写建议：
{advice_result}

可直接粘贴到简历中的优化表述：
{resume_lines_result}
""".strip()
