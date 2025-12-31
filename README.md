# AutoGLM WebUI

一个轻量的本地 WebUI，用来跑 **Open-AutoGLM / AutoGLM Phone Agent**：连接手机（ADB）→ 做连通性检测 → 输入自然语言任务 → 实时查看步骤/日志（支持 Monitor 拆解循环）。

[English README](README_en.md)

## 功能一览

- 设备管理：列出 ADB 设备、选择目标设备
- 连通性检测：ADB / 设备在线 / 截图 / ADB Keyboard / input 注入提示
- 两种运行模式：
  - **操控AI（direct）**：直接执行用户任务
  - **监控AI（monitor）**：监控AI拆解 Goal → 下发短子任务给执行AI（可配置不同的 base_url/model/api_key）
- 实时日志：SSE 推送，前端分离显示 **Monitor 日志** 与 **Executor 日志**
- 采样参数：可调 `temperature`（执行AI）与 `monitor_temperature`（监控AI）
- 手机预览：
  - 网页监控（截图轮询）
  - scrcpy 控制（可选，独立桌面窗口更顺滑）

## 快速开始（Windows）

### 1) 准备环境

1. 安装 Python 3.10+（建议）
2. 安装 ADB（platform-tools），确保命令行能运行 `adb`
3. 手机上开启开发者选项 + USB 调试，用数据线连接电脑
4. 确认设备可见：`adb devices` 里状态为 `device`

> Android 文本输入建议安装 ADB Keyboard：  
> 下载 `ADBKeyboard.apk` 并安装/启用：`https://github.com/senzhk/ADBKeyBoard`

### 2) 安装依赖

双击运行：

- `setup.bat`

### 3) 启动 WebUI

双击运行：

- `webui_start.bat`

然后打开：

- `http://127.0.0.1:7860/`

## 云端模型（API Key 自动切换）

WebUI 支持 OpenAI-compatible 接口。规则：

- 当 **API Key** 非空且非 `EMPTY` 时，自动切到云端预设（可改 base_url/model）
- 清空后回到本地预设

默认预设（可在 UI 里切换）：

- LinkAPI（Gemini 中转）：`base_url=https://api.linkapi.org/v1`，`model=gemini-3-flash-preview`
- Zhipu BigModel：`base_url=https://open.bigmodel.cn/api/paas/v4`，`model=autoglm-phone`
- z.ai：`base_url=https://api.z.ai/api/paas/v4`，`model=autoglm-phone-multilingual`

## scrcpy 配置（可选）

后端会按顺序查找 scrcpy：

1. `SCRCPY_EXE`（指向 `scrcpy.exe`）
2. 系统 `PATH` 中的 `scrcpy`
3. `SCRCPY_DIR`（目录，尝试 `<dir>/scrcpy.exe` 或 `<dir>/dist/**/scrcpy.exe`）

## 安全说明（重要）

- WebUI 默认只监听 `127.0.0.1`（不对外网暴露）
- API Key **仅保存在浏览器 localStorage**；服务端日志只做脱敏显示
- 不要把 `env.bat` / `docker.env` / `docker.model.env` 提交到仓库（已在 `.gitignore`）

## 致谢

本项目基于 `zai-org/Open-AutoGLM` 二次整理，聚焦 WebUI 与本地联调体验。
