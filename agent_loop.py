import json

from llm_service import call_model, create_client


RESUME_FIELDS = {
    "basic_info": {},
    "education": [],
    "experience": [],
    "projects": [],
    "skills": [],
    "self_summary": "",
}

JD_FIELDS = {
    "job_title": "",
    "company_name": "",
    "responsibilities": [],
    "required_skills": [],
    "preferred_skills": [],
    "education_requirement": "",
    "experience_requirement": "",
    "location": "",
    "keywords": [],
}

MATCH_PLAN_FIELDS = {
    "match_analysis": {
        "match_score": 0,
        "main_strengths": [],
        "main_gaps": [],
        "missing_keywords": [],
        "conclusion": "",
    },
    "rewrite_plan": {
        "keep_sections": [],
        "enhance_sections": [],
        "compress_sections": [],
        "keywords_to_add": [],
        "do_not_fabricate": [],
    },
}

REWRITTEN_RESUME_FIELDS = {
    "basic_info": {},
    "education": [],
    "self_summary": "",
    "skills": [],
    "projects": [],
    "experience": [],
}

REVIEW_RESULT_FIELDS = {
    "is_good_enough": True,
    "keyword_coverage": [],
    "missing_match_points": [],
    "style_issues": [],
    "fabrication_risks": [],
    "need_revision": False,
    "revision_instructions": [],
}

LOOP_RESULT_FIELDS = {
    "check_result": {},
    "triggered_revision": False,
    "diff_summary": [],
    "final_resume": {},
    "round_count": 1,
}


def build_resume_parse_prompt(resume_text):
    """生成简历结构化解析提示词。"""
    return f"""
请把下面的简历原始文本整理成结构化 JSON。
只返回标准 JSON，不要返回 Markdown，不要返回解释文字。

JSON 字段必须包含：
{{
  "basic_info": {{
    "name": "",
    "phone": "",
    "email": "",
    "location": ""
  }},
  "education": [],
  "experience": [],
  "projects": [],
  "skills": [],
  "self_summary": ""
}}

要求：
1. 如果某个字段没有内容，请返回空对象、空列表或空字符串。
2. 不要编造简历中不存在的信息。
3. experience 和 projects 尽量按条目拆分。
4. skills 尽量整理成技能关键词列表。

简历原始文本：
{resume_text}
""".strip()


def build_jd_structure_prompt(jd_text):
    """生成 JD 结构化解析提示词。"""
    return f"""
请把下面的岗位 JD 原始内容整理成结构化 JSON。
只返回标准 JSON，不要返回 Markdown，不要返回解释文字。

JSON 字段必须包含：
{{
  "job_title": "",
  "company_name": "",
  "responsibilities": [],
  "required_skills": [],
  "preferred_skills": [],
  "education_requirement": "",
  "experience_requirement": "",
  "location": "",
  "keywords": []
}}

要求：
1. 如果某个字段没有内容，请返回空字符串或空列表。
2. 不要编造 JD 中不存在的信息。
3. responsibilities 放岗位职责。
4. required_skills 放明确必需的技能或条件。
5. preferred_skills 放加分项或优先条件。
6. keywords 提取适合后续匹配分析的关键词。

岗位 JD 原始内容：
{jd_text}
""".strip()


def build_match_plan_prompt(structured_resume, structured_jd):
    """生成匹配分析和改写计划提示词。"""
    resume_json = json.dumps(structured_resume, ensure_ascii=False, indent=2)
    jd_json = json.dumps(structured_jd, ensure_ascii=False, indent=2)

    return f"""
请基于结构化简历和结构化 JD，输出岗位匹配分析和简历改写计划。
只返回标准 JSON，不要返回 Markdown，不要返回解释文字。

JSON 字段必须包含：
{{
  "match_analysis": {{
    "match_score": 0,
    "main_strengths": [],
    "main_gaps": [],
    "missing_keywords": [],
    "conclusion": ""
  }},
  "rewrite_plan": {{
    "keep_sections": [],
    "enhance_sections": [],
    "compress_sections": [],
    "keywords_to_add": [],
    "do_not_fabricate": []
  }}
}}

要求：
1. match_score 必须是 0 到 100 的整数。
2. main_strengths 写候选人和岗位匹配较好的地方。
3. main_gaps 写当前简历相对 JD 的主要缺口。
4. missing_keywords 写 JD 中重要但简历中不明显的关键词。
5. keep_sections 写建议保留的简历 section。
6. enhance_sections 写建议增强的 section 和原因。
7. compress_sections 写建议压缩的 section 和原因。
8. keywords_to_add 写建议自然补入的 JD 关键词。
9. do_not_fabricate 写不能瞎编、不能夸大的内容。
10. 不要编造简历里没有的经历，只能基于已有信息给改写计划。

结构化简历：
{resume_json}

结构化 JD：
{jd_json}
""".strip()


def build_section_rewrite_prompt(structured_resume, structured_jd, rewrite_plan_result):
    """生成按 section 改写简历的提示词。"""
    resume_json = json.dumps(structured_resume, ensure_ascii=False, indent=2)
    jd_json = json.dumps(structured_jd, ensure_ascii=False, indent=2)
    plan_json = json.dumps(rewrite_plan_result, ensure_ascii=False, indent=2)

    return f"""
请根据结构化简历、结构化 JD 和改写计划，按 section 改写简历内容。
只返回标准 JSON，不要返回 Markdown，不要返回解释文字。

JSON 字段必须包含：
{{
  "basic_info": {{}},
  "education": [],
  "self_summary": "",
  "skills": [],
  "projects": [],
  "experience": []
}}

改写范围：
1. self_summary
2. skills
3. projects
4. experience

要求：
1. 贴合 JD，但不要凭空捏造不存在的经历。
2. 尽量保留原始事实，只优化表达、重点和顺序。
3. 表述要像正式求职简历，不要像聊天回答。
4. basic_info 和 education 原则上保留原始信息，不要随意改写。
5. projects 和 experience 可以改写为更清晰的条目，但不能增加原简历没有的公司、项目、指标或经历。
6. 如果缺少某个 section，请返回空字符串或空列表。

结构化简历：
{resume_json}

结构化 JD：
{jd_json}

匹配分析与改写计划：
{plan_json}
""".strip()


def build_resume_check_prompt(structured_resume, structured_jd, candidate_resume):
    """生成候选简历检查提示词。"""
    original_json = json.dumps(structured_resume, ensure_ascii=False, indent=2)
    jd_json = json.dumps(structured_jd, ensure_ascii=False, indent=2)
    candidate_json = json.dumps(candidate_resume, ensure_ascii=False, indent=2)

    return f"""
请检查新版简历内容候选稿是否适合投递该岗位。
只返回标准 JSON，不要返回 Markdown，不要返回解释文字。

JSON 字段必须包含：
{{
  "is_good_enough": true,
  "keyword_coverage": [],
  "missing_match_points": [],
  "style_issues": [],
  "fabrication_risks": [],
  "need_revision": false,
  "revision_instructions": []
}}

检查重点：
1. 是否覆盖了核心 JD 关键词。
2. 是否存在明显缺失的重要匹配点。
3. 是否有过长、啰嗦、不像简历表述的内容。
4. 是否疑似出现了凭空捏造。

判断规则：
1. 如果整体已经可用，is_good_enough 为 true，need_revision 为 false。
2. 如果需要再修正一轮，is_good_enough 为 false，need_revision 为 true，并给出 revision_instructions。
3. 不要要求补充原始简历里没有的经历或数据。

原始结构化简历：
{original_json}

结构化 JD：
{jd_json}

新版简历内容候选稿：
{candidate_json}
""".strip()


def build_revision_prompt(structured_resume, structured_jd, candidate_resume, check_result):
    """生成二次修正提示词。"""
    original_json = json.dumps(structured_resume, ensure_ascii=False, indent=2)
    jd_json = json.dumps(structured_jd, ensure_ascii=False, indent=2)
    candidate_json = json.dumps(candidate_resume, ensure_ascii=False, indent=2)
    check_json = json.dumps(check_result, ensure_ascii=False, indent=2)

    return f"""
请根据检查结果，对新版简历内容候选稿进行一次修正。
只返回标准 JSON，不要返回 Markdown，不要返回解释文字。

JSON 字段必须包含：
{{
  "revised_resume": {{
    "basic_info": {{}},
    "education": [],
    "self_summary": "",
    "skills": [],
    "projects": [],
    "experience": []
  }},
  "diff_summary": []
}}

修正要求：
1. 优先补足 JD 核心关键词覆盖不足的问题。
2. 修正过长、啰嗦、不像简历的表达。
3. 删除或弱化疑似凭空捏造的内容。
4. 不要添加原始简历里没有的公司、项目、岗位、指标或经历。
5. diff_summary 用简短中文说明修正前后主要差异。

原始结构化简历：
{original_json}

结构化 JD：
{jd_json}

新版简历内容候选稿：
{candidate_json}

检查结果：
{check_json}
""".strip()


def normalize_data(result, fields):
    """补齐缺失字段，避免页面展示时报错。"""
    normalized_data = {}
    for field_name, default_value in fields.items():
        normalized_data[field_name] = result.get(field_name, default_value)
    return normalized_data


def normalize_match_plan(result):
    """补齐匹配分析和改写计划中的缺失字段。"""
    normalized_data = normalize_data(result, MATCH_PLAN_FIELDS)
    normalized_data["match_analysis"] = normalize_data(
        normalized_data.get("match_analysis", {}),
        MATCH_PLAN_FIELDS["match_analysis"],
    )
    normalized_data["rewrite_plan"] = normalize_data(
        normalized_data.get("rewrite_plan", {}),
        MATCH_PLAN_FIELDS["rewrite_plan"],
    )
    return normalized_data


def normalize_review_result(result):
    """补齐检查结果中的缺失字段。"""
    return normalize_data(result, REVIEW_RESULT_FIELDS)


def normalize_loop_result(result):
    """补齐 loop 结果中的缺失字段。"""
    normalized_data = normalize_data(result, LOOP_RESULT_FIELDS)
    normalized_data["check_result"] = normalize_review_result(
        normalized_data.get("check_result", {})
    )
    normalized_data["final_resume"] = normalize_data(
        normalized_data.get("final_resume", {}),
        REWRITTEN_RESUME_FIELDS,
    )
    return normalized_data


def parse_resume_structure(resume_text):
    """调用大模型，把简历原始文本解析成结构化信息。"""
    client = create_client()
    prompt = build_resume_parse_prompt(resume_text)
    result = call_model(client, prompt)
    return normalize_data(result, RESUME_FIELDS)


def parse_jd_structure(jd_text):
    """调用大模型，把岗位 JD 解析成结构化信息。"""
    client = create_client()
    prompt = build_jd_structure_prompt(jd_text)
    result = call_model(client, prompt)
    return normalize_data(result, JD_FIELDS)


def generate_match_and_rewrite_plan(structured_resume, structured_jd):
    """基于结构化简历和结构化 JD，生成匹配分析与改写计划。"""
    client = create_client()
    prompt = build_match_plan_prompt(structured_resume, structured_jd)
    result = call_model(client, prompt)
    return normalize_match_plan(result)


def generate_section_rewrite(structured_resume, structured_jd, rewrite_plan_result):
    """按 section 生成新版简历内容。"""
    client = create_client()
    prompt = build_section_rewrite_prompt(
        structured_resume,
        structured_jd,
        rewrite_plan_result,
    )
    result = call_model(client, prompt)
    return normalize_data(result, REWRITTEN_RESUME_FIELDS)


def check_resume_candidate(client, structured_resume, structured_jd, candidate_resume):
    """检查新版简历候选稿是否需要修正。"""
    prompt = build_resume_check_prompt(
        structured_resume,
        structured_jd,
        candidate_resume,
    )
    result = call_model(client, prompt)
    return normalize_review_result(result)


def revise_resume_candidate(client, structured_resume, structured_jd, candidate_resume, check_result):
    """根据检查结果，对候选稿自动修正一轮。"""
    prompt = build_revision_prompt(
        structured_resume,
        structured_jd,
        candidate_resume,
        check_result,
    )
    result = call_model(client, prompt)
    return {
        "revised_resume": normalize_data(
            result.get("revised_resume", {}),
            REWRITTEN_RESUME_FIELDS,
        ),
        "diff_summary": result.get("diff_summary", []),
    }


def run_review_loop(structured_resume, structured_jd, candidate_resume):
    """最多执行 2 轮：先检查，必要时再自动修正一轮。"""
    client = create_client()
    check_result = check_resume_candidate(
        client,
        structured_resume,
        structured_jd,
        candidate_resume,
    )

    loop_result = {
        "check_result": check_result,
        "triggered_revision": False,
        "diff_summary": [],
        "final_resume": candidate_resume,
        "round_count": 1,
    }

    if check_result.get("need_revision") or not check_result.get("is_good_enough"):
        revision_result = revise_resume_candidate(
            client,
            structured_resume,
            structured_jd,
            candidate_resume,
            check_result,
        )
        loop_result["triggered_revision"] = True
        loop_result["diff_summary"] = revision_result.get("diff_summary", [])
        loop_result["final_resume"] = revision_result.get("revised_resume", candidate_resume)
        loop_result["round_count"] = 2

    return normalize_loop_result(loop_result)
