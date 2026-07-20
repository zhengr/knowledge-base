# Causal-Audit: 基于目标感知因果链的可审计图推理

> tags: #causal-reasoning #graph-reasoning #llm-auditing #explainable-ai #knowledge-graph
> source: [Causal-Audit: Explicit and Auditable Graph-based Reasoning via Target-Aware Causal Chain Construction](https://arxiv.org/abs/2607.15281)
> score: 技术深度8/10 | 实用价值7/10 | 时效性8/10 | 领域匹配9/10 | 综合 8/10

## 核心概念
Causal-Audit 是一种通过构建目标感知因果链来实现显式且可审计的图推理框架。它将大语言模型（LLM）的隐式推理过程转化为基于图结构的显式因果路径，结合干预与反事实推理验证节点间的因果依赖，从而提供可追溯的决策依据。

## 设计原理
设计原理在于将黑盒推理过程白盒化。通过引入目标感知机制，动态约束因果链的搜索空间，避免无关节点的干扰；利用结构因果模型（SCM）的思想，对图节点进行do算子干预，评估其对最终推理目标的影响，以此区分真实因果关联与虚假统计相关性，确保推理链路的可审计性与逻辑严密性。

## 关键实现
关键实现包含目标感知的因果图构建算法与审计接口。算法侧采用基于注意力权重的因果节点提取，参数包含因果置信度阈值α（如0.75）与最大链路深度D（如5）。接口侧暴露 `audit_trace(query, target)` 返回结构化因果链对象，包含节点ID、因果转移概率、干预效应值（ATE）及反事实验证日志，支持JSON格式导出供外部审计系统调用。

## 关联分析
与基于知识图谱的检索增强生成（KG-RAG）相比，Causal-Audit 强调因果推理而非语义相似度检索；与 GraphGPT 等图结构大模型相比，其核心差异在于引入了反事实干预验证机制。可交叉引用 LlamaIndex 的图数据索引实现以及 DoWhy 等因果推断库作为底层因果验证的参考。

## 可执行建议
1. 在现有的 RAG 流水线中引入 do算子模拟，对 Top-K 检索出的上下文节点进行虚假相关性过滤，测试并对比因果过滤前后的幻觉率。2. 使用 NetworkX 构建一个小型测试知识图谱，调用 Causal-Audit 的 `audit_trace` 接口导出特定查询的因果链 JSON，人工审查其逻辑可解释性。
