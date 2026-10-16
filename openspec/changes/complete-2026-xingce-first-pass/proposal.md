# Proposal

## Why

用户要求安装OpenSpec并完成2026副省级行测首答。需要实际作答证据，确保答案核验与首答分离，并将既有教学规则转化为可验收的流程。

## What Changes

- 安装OpenSpec并配置本仓库Codex工作流。
- 本地逐题保存135题首答、简明可核查依据、把握程度及接触说明。
- 图形、公式和数据表回看原页；首答完成前不打开参考答案。
- 公开仓库仅提交流程、规格与完成摘要，原始题目和答案保留本地。
- 本次只完成AI首答，不将参考核验、用户迁移或提分判为已完成。

## Capabilities

### New Capabilities

- `exam-first-pass`: 独立首答的完整记录、先答后核验和本地证据管理。

### Modified Capabilities

无。

## Impact

影响OpenSpec配置、生成的Codex工作流、README、AGENTS及训练任务状态。新增本地首答文件，不改模型权重，不上传第三方教材和题面。关联issue #1与PR #2。
