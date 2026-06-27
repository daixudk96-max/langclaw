# mini-OpenClaw 可吸收点记录

## 来源项目

- **对比目标项目**：`E:\github\mini-OpenClaw`
- **当前项目**：`E:\github\langclaw`
- **参考材料位置**：
  - `E:\github\mini-OpenClaw\.qoder\repowiki\zh`
  - `E:\github\mini-OpenClaw` 中现有 README / 后端前端实现说明

## 结论

从 `E:\github\mini-OpenClaw` 这套实现里，**Langclaw 在核心 Agent / runtime / extensibility 能力上没有明显缺口**。真正值得吸收、且当前 `E:\github\langclaw` 没有直接内置成品的内容，**主要只有一个：前端工作台（frontend workbench）**。

## 建议吸收的内容

### 1. 内置前端工作台

可参考来源：`E:\github\mini-OpenClaw\frontend`

这是一个浏览器中的一体化工作台，用于把 Agent 的运行过程直接展示给开发者或最终用户，典型能力包括：

- 聊天界面
- 会话列表与切换
- 原始消息查看（raw messages）
- 技能 / Memory 文件在线查看与编辑
- 工具调用过程可视化
- RAG 检索结果展示
- Token 统计面板

## 不需要作为重点吸收的内容

以下部分不是 Langclaw 的核心能力缺口，不构成必须补齐的功能差异：

- Agent 核心运行时
- 子代理 / 命名代理机制
- 工具系统本身
- RAG 作为一种能力的存在与否
- 会话持久化的基本能力
- 技能扩展的基本能力

这些能力在 `E:\github\langclaw` 中已经具备，或者以更框架化、更可扩展的方式存在。mini-OpenClaw 的优势主要体现在它把这些能力包成了一个开箱即用的本地产品壳，而不是在框架内核层面提供了 Langclaw 没有的重大功能。

## 一句话结论

**从 `E:\github\mini-OpenClaw` 可吸收的核心内容，基本只有一个：位于 `E:\github\mini-OpenClaw\frontend` 的前端工作台。除此之外，没有明显必须从该项目补入 Langclaw 的重大功能缺口。**
