# 快速启动指南 - autoglm-webui (Mac + iPhone)

## ✅ 已完成的适配

1. **✅ 克隆并安装成功**
   - 项目已克隆到：`/Users/kola/autoglmwebui/autoglm-webui`
   - 依赖已安装完成
   - Python 虚拟环境已创建

2. **✅ iOS 支持已添加**
   - WebUI 服务器已支持 iOS 设备
   - iOS 设备检测功能正常
   - WebDriverAgent 集成完成

3. **✅ 环境配置已生成**
   - `env.sh` 已创建并预配置你的 Anthropic API
   - `setup.sh` 和 `webui_start.sh` 已创建并可执行

## 🚀 启动步骤

### 1. 确认 WebDriverAgent 运行

```bash
# 检查 WDA 是否正常
curl http://localhost:8100/status
```

如果没有响应，需要在 Xcode 中重新运行 WebDriverAgent。

### 2. 确认 iOS 设备连接

```bash
# 检查设备连接
idevice_id -l
# 应该显示：00008030-001529600C05802E
```

### 3. 启动 WebUI

```bash
cd /Users/kola/autoglmwebui/autoglm-webui
./webui_start.sh
```

### 4. 访问 WebUI

打开浏览器访问：**http://127.0.0.1:7860/**

## 🎯 使用流程

1. **设备管理**
   - 点击"设备管理"查看已连接的 iOS 设备
   - 应该能看到设备 UDID: `00008030-001529600C05802E`

2. **连通性检测**
   - 点击"连通性检测"按钮
   - 确认以下检查通过：
     - ✅ iOS 设备已连接
     - ✅ WebDriverAgent 运行正常
     - ✅ 设备通信正常

3. **执行任务**
   - 在任务输入框输入指令，例如：
     - "打开设置"
     - "打开Safari浏览器"
     - "打开相机"
   - 点击"开始执行"

## 📝 当前配置

- **设备类型**：iOS (iPhone)
- **设备 ID**：00008030-001529600C05802E
- **WDA URL**：http://localhost:8100
- **API 类型**：Anthropic (本地反代)
- **Base URL**：http://127.0.0.1:8045
- **Model**：claude-sonnet-4-5

## ⚙️ 如需修改配置

编辑 `env.sh` 文件：

```bash
nano /Users/kola/autoglmwebui/autoglm-webui/env.sh
```

修改后需要重启 WebUI：
```bash
# 停止当前运行的 WebUI (Ctrl+C)
# 然后重新启动
./webui_start.sh
```

## 🐛 故障排除

### WebDriverAgent 无法连接

```bash
# 检查端口转发
killall iproxy
iproxy 8100 8100 &

# 在 Xcode 中重新运行 WebDriverAgent
```

### 设备无法检测

```bash
# 检查 libimobiledevice
which idevice_id

# 重新配对设备
idevicepair unpair
idevicepair pair
```

### API 调用失败

```bash
# 确认反代服务运行
curl http://127.0.0.1:8045/v1/models

# 检查环境变量
source env.sh
echo $PHONE_AGENT_API_KEY
```

## 📚 更多文档

详细文档请参考：
- **Mac + iPhone README**: [README_MAC.md](README_MAC.md)
- **原项目文档**: [README.md](README.md)
- **iOS 设置指南**: https://github.com/zai-org/Open-AutoGLM/blob/main/docs/ios_setup/ios_setup.md

## ✨ 主要改进

相比原版 Windows + Android 项目，本适配版：

1. **完整 iOS 支持** - 包括设备检测、连接检查、截图功能
2. **跨平台脚本** - 提供 `.sh` 替代 `.bat` 文件
3. **自动配置** - `env.sh` 预填充你的 API 配置
4. **Mac 优化** - 路径、工具检测适配 macOS 环境

祝使用愉快！🎉
