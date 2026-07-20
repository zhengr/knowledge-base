# claw-code

> tags: #claude-code #ai-coding #cli-agent #anthropic
> source: [ultraworkers/claw-code](https://github.com/ultraworkers/claw-code)
> score: 技术深度8/10 | 实用价值7/10 | 时效性8/10 | 领域匹配9/10 | 综合 7.5/10

## 核心概念
claw-code 是 ultraworkers 组织开源的 Claude Code 增强工具/包装层，基于 Anthropic 的 Claude Code CLI 构建，扩展其作为 AI 编码代理的能力。它通过额外的命令、钩子或插件机制增强 Claude Code 的工作流自动化、上下文管理与多代理协作能力。

## 设计原理
遵循 Claude Code 的 agentic loop 设计原则（plan → act → observe），在保留 Anthropic 官方 CLI 行为兼容性的前提下，通过插件化扩展点（slash commands、hooks、sub-agents）实现功能增强，避免 fork 核心逻辑。

## 关键实现
核心实现为 Node.js/TypeScript CLI 包装器，依赖 @anthropic-ai/claude-code SDK；通过 ~/.claude/ 目录下的 commands/、agents/、hooks/ 配置加载自定义扩展；支持 MCP（Model Context Protocol）工具集成；典型参数包括 --model、--max-turns、--permission-mode；接口为标准 CLI（claw <command> [args]）。

## 关联分析
与同类项目相比：上游为 anthropics/claude-code（官方）；横向对比 openai/codex-cli（OpenAI 编码代理）、aider-chat/aider（终端 AI 配对编程）、cursor（IDE 集成方案）；claw-code 定位为 Claude Code 生态的社区增强层，区别于独立构建的替代品。

## 可执行建议
1) 立即执行 `npx claw-code` 或克隆仓库后运行 `npm install && npm link` 试用基础命令；2) 在 ~/.claude/commands/ 目录下创建自定义 slash command 测试插件机制，参考仓库 examples/ 目录的模板。
