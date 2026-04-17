# Job Agent MVP

## 项目简介

Job Agent MVP 是一个本地运行的求职辅助 Agent 原型项目。

用户可以输入岗位 JD 和基础简历，系统会调用阿里云百炼大模型进行岗位匹配分析，并输出岗位关键词、匹配分数、你的优势、你的缺口、一句话结论等内容。后续也可以继续扩展简历改写建议、面试准备建议等能力。

这个项目适合作为初学者练习 Streamlit 页面、大模型 API 调用和简单项目拆分的入门作品。

## 核心功能

- 输入岗位 JD
- 输入基础简历
- 调用阿里云百炼 OpenAI 兼容接口
- 使用 `qwen-plus` 模型进行分析
- 输出岗位关键词
- 输出匹配分数
- 输出个人优势
- 输出能力缺口
- 输出一句话结论
- 对缺少 API Key、接口调用失败、JSON 解析失败进行中文提示

## 项目结构说明

```text
job_agent_mvp/
├── app.py              # Streamlit 页面入口，负责页面展示和结果渲染
├── llm_service.py      # 负责读取 API Key、创建客户端、调用模型、解析结果
├── prompts.py          # 存放发给大模型的提示词模板
├── requirements.txt    # 项目依赖
├── .env                # 本地环境变量文件，不建议提交到 GitHub
└── .idea/              # PyCharm 本地配置目录，不建议提交到 GitHub
```

## 技术栈

- Python
- Streamlit
- OpenAI Python SDK
- 阿里云百炼 OpenAI 兼容接口
- qwen-plus 大模型

## 运行方式

适合 Windows + PyCharm 的本地运行方式：

1. 用 PyCharm 打开项目目录 `job_agent_mvp`
2. 在 PyCharm 终端中安装依赖：

```powershell
pip install -r requirements.txt
```

3. 设置环境变量中的 API Key
4. 在 PyCharm 终端中启动页面：

```powershell
streamlit run app.py
```

5. 浏览器会自动打开本地页面

## 环境变量说明

程序会按下面顺序读取 API Key，只需要设置其中一个即可：

- `DASHSCOPE_API_KEY`
- `BAILIAN_API_KEY`
- `OPENAI_API_KEY`

不要把真实 API Key 写进代码，也不要提交到 GitHub。

## 使用流程

1. 打开本地 Streamlit 页面
2. 在左侧输入岗位 JD
3. 在右侧输入基础简历
4. 点击“开始分析”
5. 等待模型返回分析结果
6. 查看匹配分数、关键词、优势、缺口和一句话结论

## 当前版本说明

当前版本是一个轻量级 MVP，重点是完成从页面输入到大模型分析结果展示的完整闭环。

目前已经具备：

- 本地 Streamlit 页面
- 岗位 JD 和简历输入
- 阿里云百炼大模型调用
- JSON 结果解析
- 基础错误提示
- 简单清晰的结果展示

## 后续可扩展方向

- 增加简历改写建议
- 增加求职信生成
- 增加面试问题预测
- 增加岗位关键词高亮
- 增加历史分析记录
- 增加多轮对话式简历优化
- 增加导出 Markdown 或 PDF 的能力
