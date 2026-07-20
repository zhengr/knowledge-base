# Hermes Agent

> tags: #AI-Agent #Function-Calling #LLM-Framework #NousResearch #Open-Source
> source: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
> score: 技术深度8/10 | 实用价值7/10 | 时效性8/10 | 领域匹配9/10 | 综合 8.0/10

## 核心概念
Hermes Agent 是 NousResearch 开源的 AI 智能体框架，基于 Hermes 系列模型（Llama/Mistral 微调版）提供原生函数调用、工具使用与多轮推理能力，支持结构化输出与动态工具链编排。

## 设计原理
采用『模型原生工具调用 + 标准化 Agent 循环』设计：Hermes 模型经专门训练可直接输出 JSON 格式工具调用，框架层负责解析、执行、结果回填与上下文管理，避免外部 ReAct 提示词工程，降低幻觉与格式错误率。

## 关键实现
核心组件：1) HermesFunctionCallingModel - 封装 vLLM/TGI 推理端点，内置聊天模板与工具 schema 注入；2) AgentLoop - 单步执行：模型生成 → JSON 解析 → 工具路由（支持同步/异步、重试、超时） → 结果压缩 → 下一轮；3) ToolRegistry - 装饰器式注册（@tool），自动生成 OpenAPI 风格 schema；4) ContextManager - 滑动窗口+摘要压缩，控制上下文长度。关键参数：max_steps=10, tool_timeout=30s, temperature=0.1。接口：agent.run(user_msg, tools=[...], stream=True) 返回 AsyncGenerator[StepEvent]。

## 关联分析
同类对比：LangGraph 更重编排图、依赖通用模型提示词；AutoGPT 侧重自主循环但工具调用不稳定；OpenAI Assistants API 闭源且无法本地部署。Hermes Agent 优势：本地化部署、模型原生函数调用、Apache-2.0 许可。可与 NousResearch/Hermes-3 模型配合，或替换为任何兼容 OpenAI API 格式的模型。

## 可执行建议
1) 克隆仓库运行 `pip install -e .` 后执行 `python examples/basic_agent.py` 体验 5 分钟内搭建本地工具调用 Agent；2) 参考 `hermes_agent/tools/` 编写自定义 @tool 函数（如数据库查询、HTTP 请求），注册后即可让模型自主决定调用时机。
