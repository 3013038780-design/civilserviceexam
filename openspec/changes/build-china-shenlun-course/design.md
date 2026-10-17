# Design

## Context

参见proposal.md。公开仓库不能包含私人资料；现有PR是顺序依赖，新PR以codex/corpus-strategies为基线，避免混入既有变更。

## Goals / Non-Goals

Goals：独立静态站、证据可追溯、课程状态诚实、写作数据本地保存。Non-Goals：本轮不声称完整八单元课程或用户效果已验证，不接入自动评分与后台更新。

## Decisions

使用原生HTML/CSS/JS和结构化课程数据，无构建依赖。哈希路由支持直达；来源关联使用稳定ID。localStorage保留草稿与冻结首稿，导出JSON，存储异常提示。Site保持owner-private，发布副本位于忽略目录并由Sites helper提交其专用源仓库；公开GitHub仅存原创源码与摘要。保留旧站不迁移。

## Risks / Trade-offs

来源时效变化→显示每条核验日期与范围，更新时保留差异。数据清理丢失→提供导出。首课不能代表课程完成→其余七单元标待建设。浏览器存储不可用→提示保存失败并允许导出当前草稿。

## Migration Plan

独立注册、验证、打包与私人部署，不改旧站。需要回退时部署该站先前已保存版本；不删除用户草稿。完整课程保持Issue开放。
