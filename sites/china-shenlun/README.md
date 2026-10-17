# 了解中国 写好申论

从官方原文理解国家运行，再将工作机制用于申论。此目录是独立网站，与原逐题研习站分别发布。

[私人课程网站](https://china-to-shenlun.easy-tern-3117.chatgpt.site) · [全部需求](docs/requirements.md) · [内容标准](docs/content-standard.md) · [协作规则](AGENTS.md) · [每日方案](../../了解中国与申论每日学习方案.md)

## 当前交付

网站基础、八单元导航、第一节示范课、来源核查、独立草稿与导出。其余七单元为待建设导航；第一课仍待用户独立迁移。上线不代表完整课程或用户掌握。

## 本机运行

在本目录执行 `python3 -m http.server 8767 --directory dist`，打开 http://localhost:8767 。检查运行 `python3 validate.py` 与 `node --check dist/app.js`。静态站无需安装依赖。笔记只存在当前浏览器，可导出；网站不自动向GitHub或服务器上传作答。

## 工程跟踪

- [总工程 #6](https://github.com/3013038780-design/civilserviceexam/issues/6)
- [本轮网站与治理 #7](https://github.com/3013038780-design/civilserviceexam/issues/7)
- [完整课程 #8](https://github.com/3013038780-design/civilserviceexam/issues/8)
- [来源与迁移 #9](https://github.com/3013038780-design/civilserviceexam/issues/9)

本轮实现任务在 `../../openspec/changes/build-china-shenlun-course/`；Issue管理课程整体进展，PR审阅文件。未建立后台更新或提醒。

## 发布

`.openai/hosting.json`固定新站身份，受众保持仅所有者。通过Sites源码工作流在忽略目录建立独立发布副本，不把它的Git仓库嵌入公开源码。发布凭据仅通过内存与stdin传递。发布版本与GitHub评审提交分别记录在 `docs/delivery.md`。

公开仓库仅含代码、原创摘要及来源索引；不上传原卷全文、课程原文、个人笔记和私人发布包。
