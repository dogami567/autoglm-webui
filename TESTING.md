# 🧪 autoglm-webui Mac + iPhone 适配测试指南

## 当前状态检测

✅ **iOS 设备已连接**
- Device ID: `00008030-001529600C05802E`
- Model: iPhone12,3 (iPhone 11 Pro)
- Connection: USB

❌ **WebDriverAgent 未运行**
- WDA 需要启动才能进行完整测试

## 📋 测试步骤

### 阶段 1: 基础环境测试（无需 WDA）

#### 1.1 测试 iOS 设备检测

```bash
cd /Users/kola/autoglmwebui/autoglm-webui

# 测试设备列表
.venv/bin/python -c "
from phone_agent.xctest import list_devices
devices = list_devices()
print(f'✅ Found {len(devices)} iOS device(s)')
for d in devices:
    print(f'  - {d.device_id}: {d.device_name or \"iPhone\"} ({d.connection_type})')
"
```

**预期结果**: 显示你的 iPhone 设备

#### 1.2 测试 WebUI 启动（不执行任务）

```bash
# 启动 WebUI（会在前台运行）
./webui_start.sh
```

**预期结果**:
- 显示: `Open-AutoGLM WebUI (Mac + iPhone)`
- 显示: `URL: http://127.0.0.1:7860/`
- 无错误信息

**测试方法**:
1. 在浏览器打开 http://127.0.0.1:7860/
2. 检查页面是否正常加载
3. 按 `Ctrl+C` 停止服务器

---

### 阶段 2: WebDriverAgent 启动

#### 2.1 检查 WDA 项目位置

你之前配置 WDA 时应该有一个 Xcode 项目，通常在：
- `~/WebDriverAgent/`
- 或其他自定义位置

#### 2.2 启动 WebDriverAgent

**方法 1: 使用 Xcode（推荐）**

```bash
# 1. 打开 WDA 项目
open /path/to/WebDriverAgent/WebDriverAgent.xcodeproj

# 2. 在 Xcode 中:
#    - 选择 WebDriverAgentRunner scheme
#    - 选择你的 iPhone 作为目标设备
#    - 点击 Run (▶️) 按钮
```

**方法 2: 使用命令行**

如果你之前配置了命令行启动：

```bash
# 进入 WDA 目录
cd /path/to/WebDriverAgent

# 启动 WDA
xcodebuild -project WebDriverAgent.xcodeproj \
           -scheme WebDriverAgentRunner \
           -destination 'id=00008030-001529600C05802E' \
           test
```

#### 2.3 验证 WDA 运行

```bash
# 检查 WDA 状态
curl http://localhost:8100/status

# 如果返回 JSON 数据，说明 WDA 正常运行
```

**预期结果**: 返回包含 sessionId、capabilities 等信息的 JSON

---

### 阶段 3: 完整功能测试

一旦 WDA 启动成功，进行以下测试：

#### 3.1 测试 API 端点

在新终端窗口运行：

```bash
cd /Users/kola/autoglmwebui/autoglm-webui

# 1. 启动 WebUI（后台）
./webui_start.sh &
WEBUI_PID=$!

# 等待启动
sleep 3

# 2. 测试设备列表 API
echo "=== Testing /api/devices ==="
curl -s http://127.0.0.1:7860/api/devices | python3 -m json.tool

# 3. 测试连通性检查 API
echo ""
echo "=== Testing /api/connectivity-check ==="
curl -s -X POST http://127.0.0.1:7860/api/connectivity-check \
  -H "Content-Type: application/json" \
  -d '{"device_type":"ios"}' | python3 -m json.tool

# 4. 测试截图 API
echo ""
echo "=== Testing /api/screen ==="
curl -s http://127.0.0.1:7860/api/screen -o /tmp/test_screenshot.png
if [ -f /tmp/test_screenshot.png ]; then
  echo "✅ Screenshot saved to /tmp/test_screenshot.png"
  file /tmp/test_screenshot.png
  open /tmp/test_screenshot.png
else
  echo "❌ Screenshot failed"
fi

# 5. 停止 WebUI
# kill $WEBUI_PID
```

#### 3.2 测试 WebUI 界面

```bash
# 启动 WebUI
./webui_start.sh
```

在浏览器中测试（http://127.0.0.1:7860/）：

**测试清单**:
- [ ] **设备管理**
  - 点击"设备管理"或"List Devices"
  - 应该显示设备: `00008030-001529600C05802E`
  - 显示设备类型: iOS

- [ ] **连通性检测**
  - 点击"连通性检测"或"Connectivity Check"
  - 应该看到三个检查:
    - ✅ iOS 设备已连接
    - ✅ WebDriverAgent 运行正常
    - ✅ 设备通信正常
  - Overall 状态应该是 "pass"

- [ ] **截图预览**
  - 如果有"Screen Preview"或"手机预览"功能
  - 应该能看到你的 iPhone 当前屏幕

#### 3.3 测试简单任务执行

在 WebUI 中：

1. **任务输入框** 输入：
   ```
   打开设置
   ```

2. **配置参数**:
   - Device Type: `ios`
   - Model: `claude-sonnet-4-5`
   - Max Steps: `10`

3. **点击"执行"或"Run"按钮**

**预期结果**:
- 实时日志显示 AI 的思考过程
- 显示执行的动作（如 `Launch`, `Tap` 等）
- iPhone 应该打开"设置"应用
- 任务完成后显示成功消息

---

### 阶段 4: 高级功能测试

#### 4.1 测试复杂任务

```
打开Safari浏览器，搜索人工智能
```

**预期**:
- 打开 Safari
- 点击搜索框
- 输入"人工智能"
- 点击搜索

#### 4.2 测试错误处理

故意输入一个无法完成的任务：

```
打开一个不存在的应用程序XYZ123
```

**预期**:
- AI 应该识别出应用不存在
- 返回合理的错误消息
- 不会崩溃

---

## 🐛 常见问题排查

### 问题 1: WebUI 无法启动

```bash
# 检查端口占用
lsof -i :7860

# 如果端口被占用，杀掉进程或更改端口
# 编辑 env.sh: export WEBUI_PORT="7861"
```

### 问题 2: WDA 连接失败

```bash
# 重启端口转发
killall iproxy
iproxy 8100 8100 &

# 检查 iPhone 是否锁屏（WDA 需要解锁）
```

### 问题 3: API 调用失败

```bash
# 检查 Anthropic 反代
curl http://127.0.0.1:8045/v1/models

# 检查环境变量
source env.sh
echo "API Key: $PHONE_AGENT_API_KEY"
echo "Base URL: $PHONE_AGENT_BASE_URL"
```

### 问题 4: 设备检测失败

```bash
# 重新配对设备
idevicepair unpair
idevicepair pair

# 检查设备信任
ideviceinfo -u 00008030-001529600C05802E
```

---

## 📊 测试结果记录

完成测试后，记录结果：

| 测试项 | 状态 | 备注 |
|--------|------|------|
| iOS 设备检测 | ⬜ | |
| WebUI 启动 | ⬜ | |
| WDA 运行 | ⬜ | |
| /api/devices | ⬜ | |
| /api/connectivity-check | ⬜ | |
| /api/screen | ⬜ | |
| 简单任务执行 | ⬜ | |
| 复杂任务执行 | ⬜ | |

---

## 🎯 快速测试脚本

创建一个自动化测试脚本：

```bash
cat > /Users/kola/autoglmwebui/autoglm-webui/test_adaptation.sh << 'EOF'
#!/bin/bash

echo "🧪 Testing autoglm-webui Mac + iPhone Adaptation"
echo "================================================"
echo ""

cd /Users/kola/autoglmwebui/autoglm-webui

# Test 1: iOS Device Detection
echo "Test 1: iOS Device Detection"
.venv/bin/python -c "
from phone_agent.xctest import list_devices
devices = list_devices()
if devices:
    print('✅ PASS: Found', len(devices), 'device(s)')
    for d in devices:
        print(f'   - {d.device_id}')
else:
    print('❌ FAIL: No devices found')
" || echo "❌ FAIL: Error detecting devices"
echo ""

# Test 2: WDA Status
echo "Test 2: WebDriverAgent Status"
if curl -s http://localhost:8100/status > /dev/null 2>&1; then
    echo "✅ PASS: WDA is running"
else
    echo "❌ FAIL: WDA is not running"
    echo "   Please start WebDriverAgent first"
fi
echo ""

# Test 3: WebUI Dependencies
echo "Test 3: Python Dependencies"
.venv/bin/python -c "
try:
    import fastapi, uvicorn, openai
    from phone_agent import PhoneAgent
    from phone_agent.xctest import XCTestConnection
    print('✅ PASS: All dependencies imported')
except ImportError as e:
    print(f'❌ FAIL: Missing dependency: {e}')
"
echo ""

echo "================================================"
echo "Basic tests complete!"
echo ""
echo "Next steps:"
echo "  1. If WDA is not running, start it in Xcode"
echo "  2. Run: ./webui_start.sh"
echo "  3. Open: http://127.0.0.1:7860/"
EOF

chmod +x /Users/kola/autoglmwebui/autoglm-webui/test_adaptation.sh
```

运行快速测试：

```bash
cd /Users/kola/autoglmwebui/autoglm-webui
./test_adaptation.sh
```

---

## 🚀 开始测试！

**推荐顺序**:

1. ✅ **先运行快速测试脚本** - 验证基础环境
2. 🔧 **启动 WebDriverAgent** - 在 Xcode 中运行 WDA
3. 🌐 **启动 WebUI** - `./webui_start.sh`
4. 🧪 **测试 API 端点** - 使用上面的 curl 命令
5. 🎮 **测试 WebUI 界面** - 在浏览器中操作
6. 🎯 **执行简单任务** - "打开设置"
7. 🚀 **执行复杂任务** - 完整的自动化流程

测试过程中如有问题，随时告诉我！
