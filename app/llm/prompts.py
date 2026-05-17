"""Two-stage prompt system: classify first, then route to specialized prompts."""

# ============================================================
# Stage 1: Quick classification
# ============================================================

CLASSIFY_PROMPT = {
    "zh": """请快速分析以下视频内容，返回 JSON 格式：
{{"summary": "一句话概要（30字以内）", "type": "<类型标签>"}}

类型标签可选值：
- tutorial: 教程、教学、操作指南
- tech_talk: 技术分享、演讲、会议
- demo: 产品演示、实操演示、案例展示
- review: 评测、对比、推荐
- news: 新闻、时事、行业动态
- vlog: 日常记录、生活分享
- general: 其他

只返回 JSON，不要其他内容。

[转录文本]
{transcript}""",
    "en": """Quickly analyze the following video content, return JSON format:
{{"summary": "one-line summary (under 30 words)", "type": "<type label>"}}

Type labels:
- tutorial: tutorials, teaching, how-to guides
- tech_talk: tech talks, speeches, conferences
- demo: product demos, live demos, case studies
- review: reviews, comparisons, recommendations
- news: news, current events, industry updates
- vlog: daily logs, lifestyle content
- general: other

Return JSON only, nothing else.

[Transcript]
{transcript}""",
}

CLASSIFY_PROMPT_MULTIMODAL = {
    "zh": """请根据视频画面和转录文本快速分析，返回 JSON 格式：
{{"summary": "一句话概要（30字以内）", "type": "<类型标签>"}}

类型标签可选值：
- tutorial: 教程、教学、操作指南
- tech_talk: 技术分享、演讲、会议
- demo: 产品演示、实操演示、案例展示
- review: 评测、对比、推荐
- news: 新闻、时事、行业动态
- vlog: 日常记录、生活分享
- general: 其他

只返回 JSON，不要其他内容。

[转录文本]
{transcript}""",
    "en": """Quickly analyze the video visuals and transcript, return JSON format:
{{"summary": "one-line summary (under 30 words)", "type": "<type label>"}}

Type labels:
- tutorial: tutorials, teaching, how-to guides
- tech_talk: tech talks, speeches, conferences
- demo: product demos, live demos, case studies
- review: reviews, comparisons, recommendations
- news: news, current events, industry updates
- vlog: daily logs, lifestyle content
- general: other

Return JSON only, nothing else.

[Transcript]
{transcript}""",
}

# ============================================================
# Stage 2: Specialized prompts by content type
# ============================================================

SUMMARY_PROMPTS = {
    "tutorial": {
        "zh": """请对以下教程类视频进行结构化总结，按以下格式输出：

## 核心主题
一句话说明本教程教什么。

## 前置条件
列出学习本教程需要的基础知识或环境准备。

## 操作步骤
按顺序列出关键步骤，每步简要说明操作内容和目的。

## 关键要点
提取 3-5 个最重要的知识点或技巧。

## 常见问题/注意事项
如有提到易错点或注意事项，列出。

[转录文本]
{transcript}""",
        "en": """Summarize the following tutorial video in this structured format:

## Core Topic
One sentence on what this tutorial teaches.

## Prerequisites
List any required knowledge or setup.

## Steps
List key steps in order, briefly describing each action and its purpose.

## Key Takeaways
Extract 3-5 most important points or tips.

## Pitfalls / Notes
List any common mistakes or important notes mentioned.

[Transcript]
{transcript}""",
    },
    "tech_talk": {
        "zh": """请对以下技术分享/演讲类视频进行结构化总结，按以下格式输出：

## 核心观点
提炼演讲者的中心论点或核心主张。

## 背景与动机
为什么提出这个观点？解决什么问题？

## 关键论据/架构
支撑核心观点的技术细节、架构设计或数据。

## 演示/案例
如有演示或案例，简述其内容和效果。

## 结论与展望
演讲者的总结和对未来的判断。

[转录文本]
{transcript}""",
        "en": """Summarize the following tech talk in this structured format:

## Core Argument
Distill the speaker's central thesis or main claim.

## Background & Motivation
Why was this proposed? What problem does it solve?

## Key Evidence / Architecture
Technical details, architecture, or data supporting the core argument.

## Demos / Case Studies
Briefly describe any demos or cases shown and their results.

## Conclusion & Outlook
The speaker's summary and outlook on the future.

[Transcript]
{transcript}""",
    },
    "demo": {
        "zh": """请对以下演示/实操类视频进行结构化总结，按以下格式输出：

## 演示目标
说明演示的是什么产品/工具/功能。

## 操作流程
按顺序列出演示中的关键操作。

## 输入与输出
每步的关键输入是什么，得到什么输出/效果。

## 亮点与局限
演示中展现的优势和可能的不足。

[转录文本]
{transcript}""",
        "en": """Summarize the following demo video in this structured format:

## Demo Objective
What product/tool/feature is being demonstrated.

## Workflow
List key operations in order.

## Input & Output
What are the key inputs and resulting outputs/effects for each step.

## Strengths & Limitations
Advantages shown and any potential shortcomings.

[Transcript]
{transcript}""",
    },
    "review": {
        "zh": """请对以下评测/对比类视频进行结构化总结，按以下格式输出：

## 评测对象
列出被评测的产品/方案。

## 评测维度
列出从哪些方面进行评测。

## 核心结论
各维度的对比结论，谁优谁劣。

## 推荐建议
视频作者的最终推荐和适用场景。

[转录文本]
{transcript}""",
        "en": """Summarize the following review video in this structured format:

## Review Subjects
List the products/solutions being reviewed.

## Evaluation Criteria
List the dimensions used for comparison.

## Key Findings
Comparison results for each dimension — which is better and why.

## Recommendation
The author's final recommendation and best-fit scenarios.

[Transcript]
{transcript}""",
    },
    "news": {
        "zh": """请对以下新闻/资讯类视频进行结构化总结，按以下格式输出：

## 事件概述
一句话说明发生了什么。

## 关键事实
列出时间、地点、涉及方等关键事实。

## 背景与影响
事件的背景和可能产生的影响。

## 各方观点
如有不同立场或观点，分别列出。

[转录文本]
{transcript}""",
        "en": """Summarize the following news video in this structured format:

## Event Summary
One sentence on what happened.

## Key Facts
List time, location, parties involved, and other key facts.

## Context & Impact
Background of the event and its potential impact.

## Perspectives
List different viewpoints or positions if mentioned.

[Transcript]
{transcript}""",
    },
    "vlog": {
        "zh": """请对以下 Vlog/日常类视频进行结构化总结，按以下格式输出：

## 内容概要
一段话概括视频的主要内容。

## 关键场景
按时间顺序列出视频中的主要场景或活动。

## 值得关注的点
如有有趣的信息、推荐或经验分享，列出。

[转录文本]
{transcript}""",
        "en": """Summarize the following vlog in this structured format:

## Overview
A brief paragraph summarizing the video content.

## Key Scenes
List main scenes or activities in chronological order.

## Notable Points
List any interesting info, recommendations, or shared experiences.

[Transcript]
{transcript}""",
    },
    "general": {
        "zh": """请对以下视频内容进行结构化总结，按以下格式输出：

## 核心内容
一段话概括视频的核心主题和主要内容。

## 关键要点
提取 3-5 个最重要的信息点。

## 详细分析
按主题分段展开，保留重要细节和数据。

## 结论
总结视频的核心结论或行动建议。

[转录文本]
{transcript}""",
        "en": """Summarize the following video in this structured format:

## Core Content
A brief paragraph on the main topic and key content.

## Key Points
Extract 3-5 most important pieces of information.

## Detailed Analysis
Expand by topic, preserving important details and data.

## Conclusion
Summarize the core conclusions or action items.

[Transcript]
{transcript}""",
    },
}

# Multimodal variants add visual context instructions
MULTIMODAL_SUFFIX = {
    "zh": "\n\n请在分析中结合视频画面内容，标注关键视觉信息（如白板内容、图表、代码界面等）。",
    "en": "\n\nIn your analysis, incorporate visual content from the video (e.g., whiteboard notes, charts, code interfaces).",
}


def get_classify_prompt(lang: str = "zh", multimodal: bool = False) -> str:
    prompts = CLASSIFY_PROMPT_MULTIMODAL if multimodal else CLASSIFY_PROMPT
    return prompts.get(lang, prompts["zh"])


def get_summary_prompt(content_type: str, lang: str = "zh", multimodal: bool = False) -> str:
    type_prompts = SUMMARY_PROMPTS.get(content_type, SUMMARY_PROMPTS["general"])
    prompt = type_prompts.get(lang, type_prompts["zh"])
    if multimodal:
        suffix = MULTIMODAL_SUFFIX.get(lang, MULTIMODAL_SUFFIX["zh"])
        prompt += suffix
    return prompt


# All known content types for validation
CONTENT_TYPES = {"tutorial", "tech_talk", "demo", "review", "news", "vlog", "general"}
