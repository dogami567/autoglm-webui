# Open-AutoGLM WebUI (设计约定 / Contract)

本文件定义 WebUI 的最小可执行约定，用于防止实现跑偏（“任务边界合同”）。

## 默认监听与端口

- 默认只监听本机：`127.0.0.1`
- 默认端口：`7860`
- 事件推送：Server-Sent Events（SSE）

## 模式与切换规则

WebUI 提供两种模型访问模式：

1. **本地模式（Local）**
   - 适用：本机已部署 vLLM（或任何 OpenAI 兼容服务）
   - 默认：
     - `base_url=http://127.0.0.1:8000/v1`
     - `model=autoglm-phone-9b`
     - `api_key=EMPTY`

2. **云端模式（Cloud）**
   - 触发规则：当用户在 WebUI 中填写 `api_key` 且非空、非 `EMPTY` 时，默认切换为云端模式。
   - 默认服务商（可在 UI 中切换/自定义）：
     - LinkAPI（Gemini 中转，OpenAI 兼容）：
       - `base_url=https://api.linkapi.org/v1`
       - `model=gemini-3-flash-preview`
     - Zhipu BigModel：
       - `base_url=https://open.bigmodel.cn/api/paas/v4`
       - `model=autoglm-phone`
     - z.ai：
       - `base_url=https://api.z.ai/api/paas/v4`
       - `model=autoglm-phone-multilingual`

> 安全：服务端/前端日志与事件流不得明文输出 `api_key`，最多只展示是否已设置（boolean）或脱敏后的前后缀。

## WebUI 字段清单（前后端一致）

WebUI 需要支持以下配置字段（均可在前端展示与保存到 localStorage）：

- 设备：
  - `device_type`: `adb|hdc|ios`（本期优先支持 `adb`）
  - `device_id`: ADB 设备序列号（多设备时必填）
- 任务：
  - `task`: 用户自然语言任务
  - `max_steps`: 最大执行步数（默认 100）
  - `lang`: `cn|en`（默认 cn）
- 模型：
  - `base_url`
  - `model`
  - `api_key`

## 接口约定（最小集合）

- `GET /`：返回静态 WebUI 页面（HTML）
- `GET /api/health`：健康检查
- `GET /api/devices`：列出设备
- `POST /api/connectivity-check`：连通性检测（adb、设备在线、截图、ADB Keyboard）
- `POST /api/run`：启动任务（单任务互斥）
- `GET /api/run/stream`：SSE 推送日志与步骤事件

## 日志与事件流

WebUI 至少要在前端显示：

- 每一步的 `thinking`（可选截断）与解析后的 `action`（结构化）
- 执行结果（success/finished/message）
- 后端运行日志（用于排查错误）
