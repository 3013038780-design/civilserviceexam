# Spec Delta

## Purpose

将原有空课程入口补为可独立阅读的八课正文，先完成Markdown与可用的Word文档，再同步网站，使原文定位、理论解释、工作案例与申论写作任务能够在同一课内连续使用，并保留实际阅读范围和效果验证边界。

## ADDED Requirements

### Requirement: 完整课文

系统 SHALL 为八单元各提供实际讲义，包含原文定位、核心解释、事实案例与机制、申论用法及独立任务；十九章主题 SHALL 有课程映射，实际精读范围 MUST 如实标明。

#### Scenario: 阅读任意课程

- **WHEN** 用户进入任一单元
- **THEN** 可读完整讲义而非待建空页，并核查对应原文

### Requirement: 文档与网站一致

系统 SHALL 先生成八份Markdown与八份Word并提供合订版，Word MUST 完成中文和版式渲染检查；网站 SHALL 同步同一文本并提供下载。

#### Scenario: 下载与对照

- **WHEN** 用户下载单课或合订稿
- **THEN** 正文与网页对应，Word中文可读且链接有效

### Requirement: 独立输出保护

系统 SHALL 按课保存草稿、冻结首稿并默认收起表达示范，旧首课记录 MUST 保留原ID。

#### Scenario: 切换课节

- **WHEN** 用户在不同课节保存作答
- **THEN** 记录互不覆盖，原首课记录仍可读取
