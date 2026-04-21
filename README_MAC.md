# AutoGLM WebUI - Mac + iPhone 适配版

这是 [autoglm-webui](https://github.com/dogami567/autoglm-webui) 的 Mac + iPhone 适配版本，支持在 macOS 上运行并控制 iPhone 设备。

## 功能特性

- ✅ 支持 iOS 设备（iPhone/iPad）通过 WebDriverAgent
- ✅ 支持 Android 设备通过 ADB
- ✅ 设备管理：列出设备、选择目标设备
- ✅ 连通性检测：设备在线检测、WebDriverAgent 状态检查
- ✅ 实时日志：SSE 推送任务执行过程
- ✅ 手机预览：实时截图轮询
- ✅ 支持自定义 AI 模型 API（包括本地反代）

## 系统要求

### macOS 环境

- macOS 10.15+
- Python 3.10+
- Homebrew（推荐）

### iOS 设备支持

1. **libimobiledevice**（用于设备通信）
   ```bash
   brew install libimobiledevice
   ```

2. **WebDriverAgent**（用于设备控制）
   - 必须在 iPhone 上安装并运行 WebDriverAgent
   - 参考安装教程：[Open-AutoGLM iOS Setup](https://github.com/zai-org/Open-AutoGLM/blob/main/docs/ios_setup/ios_setup.md)
   - 默认运行在 `http://localhost:8100`

3. **iPhone 配置**
   - 开启开发者模式
   - 信任电脑
   - WebDriverAgent 正常运行

### Android 设备支持（可选）

如果要使用 Android 设备：
```bash
brew install android-platform-tools
```

## 快速开始

### 1. 安装依赖

克隆项目并运行安装脚本：

```bash
cd autoglm-webui
chmod +x setup.sh
./setup.sh
```

### 2. 配置环境变量

编辑 `env.sh` 文件（setup.sh 会自动创建）：

```bash
#!/bin/bash

# Anthropic API 配置（或其他 OpenAI 兼容 API）
export ANTHROPIC_API_KEY="your-api-key-here"
export ANTHROPIC_BASE_URL="http://127.0.0.1:8045"  # 本地反代地址

# Phone Agent API 配置
export PHONE_AGENT_BASE_URL="http://127.0.0.1:8045"
export PHONE_AGENT_MODEL="claude-sonnet-4-5"  # 或你使用的模型
export PHONE_AGENT_API_KEY="your-api-key-here"

# 设备类型：ios（iPhone）或 adb（Android）
export PHONE_AGENT_DEVICE_TYPE="ios"

# iOS 设备配置
export PHONE_AGENT_WDA_URL="http://localhost:8100"
# 如果有多个设备，可以指定 UDID（可选）
# export PHONE_AGENT_DEVICE_ID="00008030-001529600C05802E"

# WebUI 设置
export WEBUI_HOST="127.0.0.1"
export WEBUI_PORT="7860"
```

**重要提示：**
- 不要把包含 API Key 的 `env.sh` 提交到 Git（已在 `.gitignore` 中）
- 如果使用本地反代（如 antigravity），确保反代服务已启动

### 3. 启动 WebDriverAgent

确保 WebDriverAgent 在 iPhone 上正常运行：

```bash
# 检查 WDA 状态
curl http://localhost:8100/status

# 或使用 Python 脚本检查
python3 ios.py --list-devices
```

### 4. 启动 WebUI

```bash
chmod +x webui_start.sh
./webui_start.sh
```

然后在浏览器中打开：http://127.0.0.1:7860/

## 使用说明

### 设备检测

1. 打开 WebUI 后，点击"设备管理"
2. 查看已连接的 iOS 设备列表
3. 运行连通性检测确保：
   - iOS 设备已连接
   - WebDriverAgent 正常运行
   - 设备通信正常

### 运行任务

1. 在任务输入框输入自然语言指令，例如：
   - "打开设置，进入通用"
   - "打开Safari浏览器，搜索人工智能"
   - "打开相机拍照"

2. 配置参数：
   - **设备类型**：选择 iOS 或 ADB
   - **设备 ID**：多设备时选择特定设备
   - **最大步数**：限制任务执行步数
   - **Temperature**：模型温度参数

3. 点击"开始执行"

### 实时监控

- WebUI 会实时显示：
  - 任务执行步骤
  - AI 的思考过程
  - 执行的操作
  - 设备截图（可选）

## 高级配置

### 使用本地模型 API

如果你使用本地反代（如 antigravity）：

```bash
# 在 env.sh 中配置
export PHONE_AGENT_BASE_URL="http://127.0.0.1:8045"
export PHONE_AGENT_MODEL="claude-sonnet-4-5"
export PHONE_AGENT_API_KEY="your-local-api-key"
```

### 支持的云端 API

WebUI 也支持其他 OpenAI 兼容的 API：

- **智谱 BigModel**：
  ```bash
  export PHONE_AGENT_BASE_URL="https://open.bigmodel.cn/api/paas/v4"
  export PHONE_AGENT_MODEL="autoglm-phone"
  ```

- **ModelScope**：
  ```bash
  export PHONE_AGENT_BASE_URL="https://api-inference.modelscope.cn/v1"
  export PHONE_AGENT_MODEL="ZhipuAI/AutoGLM-Phone-9B"
  ```

### 多设备支持

如果有多个 iOS 设备：

1. 列出所有设备：
   ```bash
   idevice_id -l
   ```

2. 在 `env.sh` 中指定设备 UDID：
   ```bash
   export PHONE_AGENT_DEVICE_ID="your-device-udid"
   ```

## 故障排除

### iOS 设备无法检测

```bash
# 检查 libimobiledevice 是否安装
which idevice_id

# 检查设备连接
idevice_id -l

# 检查设备信息
ideviceinfo -u your-device-udid
```

### WebDriverAgent 无法连接

```bash
# 检查 WDA 是否运行
curl http://localhost:8100/status

# 检查端口转发（如果使用 USB）
iproxy 8100 8100 &

# 重启 WDA（在 Xcode 中重新运行）
```

### API 调用失败

```bash
# 检查 API 服务是否运行
curl http://127.0.0.1:8045/v1/models  # 根据你的 base_url

# 检查环境变量是否正确加载
echo $PHONE_AGENT_API_KEY
echo $PHONE_AGENT_BASE_URL
```

### Python 依赖问题

```bash
# 重新安装依赖
.venv/bin/python -m pip install --force-reinstall -r requirements.txt
```

## 与原版的区别

本 Mac + iPhone 适配版相比原版的主要改进：

1. **✅ 添加 iOS 设备支持**
   - 完整的 iOS 设备检测和连接
   - WebDriverAgent 状态监控
   - iOS 截图功能

2. **✅ 跨平台脚本**
   - 提供 `setup.sh` 和 `webui_start.sh` 替代 `.bat` 文件
   - 自动检测 Mac/Linux 环境

3. **✅ 修复路径问题**
   - ADB 路径支持 Mac/Linux（去掉 `.exe` 扩展名）
   - 支持 Homebrew 安装的工具

4. **✅ 环境变量配置**
   - 创建 `env.sh` 配置文件
   - 支持本地 API 反代配置

## 安全说明

- WebUI 默认只监听 `127.0.0.1`（本地访问）
- API Key 仅保存在 `env.sh`（不会提交到 Git）
- 服务端日志会脱敏显示 API Key

## 致谢

- 原项目：[autoglm-webui](https://github.com/dogami567/autoglm-webui)
- 基础框架：[Open-AutoGLM](https://github.com/zai-org/Open-AutoGLM)

## 许可证

与原项目保持一致

## 常见问题

**Q: 为什么选择 iPhone 而不是 Android？**

A: 两者都支持！通过 `PHONE_AGENT_DEVICE_TYPE` 环境变量切换：
- `export PHONE_AGENT_DEVICE_TYPE="ios"` - 使用 iPhone
- `export PHONE_AGENT_DEVICE_TYPE="adb"` - 使用 Android

**Q: 可以同时控制多个设备吗？**

A: WebUI 目前一次只能控制一个设备。如需控制多个设备，可以：
1. 运行多个 WebUI 实例（不同端口）
2. 为每个实例配置不同的设备 ID

**Q: 支持 HarmonyOS 吗？**

A: 原项目支持 HarmonyOS（通过 HDC），但本 Mac 适配版主要针对 iOS。如需 HarmonyOS 支持，需要额外配置 HDC 工具。

**Q: 本地反代 API 速度慢怎么办？**

A:
1. 检查反代服务器性能
2. 考虑使用云端 API（智谱、ModelScope 等）
3. 调整 `temperature` 参数降低响应时间
