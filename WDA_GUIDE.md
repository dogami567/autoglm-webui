# WebDriverAgent 启动指南

## 当前状态

✅ **WDA 构建成功** - 代码已签名并可部署
⚠️ **WDA 命令行启动失败** - 需要使用 Xcode 界面启动

## 🎯 解决方案：使用 Xcode 启动 WDA（推荐）

### 步骤 1: 打开 Xcode 项目

```bash
open ~/WebDriverAgent/WebDriverAgent.xcodeproj
```

### 步骤 2: 在 Xcode 中配置

1. **选择 Scheme**：
   - 点击顶部工具栏的 scheme 选择器
   - 选择 "**WebDriverAgentRunner**"

2. **选择设备**：
   - 在 scheme 旁边的设备选择器中
   - 选择 "**Huawei Mate 11 Pro**"（你的 iPhone 11 Pro）

3. **确认设备已连接并解锁**：
   - 设备应该显示为"已连接"状态
   - 确保 iPhone 已解锁

### 步骤 3: 运行 WDA

1. **点击运行按钮** （▶️） 或按 `Cmd + R`

2. **等待构建和部署**：
   - Xcode 会编译项目
   - 将 WDA 部署到你的 iPhone
   - 在控制台中查看输出

3. **查找 ServerURL**：
   - 在 Xcode 底部的控制台窗口
   - 找到这样的一行：
     ```
     ServerURLHere->http://192.168.1.9:8100<-ServerURLHere
     ```
   - 这就是 WDA 的访问地址

### 步骤 4: 验证 WDA 运行

在终端中测试：

```bash
# 使用 WiFi IP（从 Xcode 控制台获取）
curl http://192.168.1.9:8100/status

# 应该返回 JSON 数据包含 sessionId 等信息
```

## 📱 WDA 运行后的状态

成功启动后，你会看到：

1. **iPhone 屏幕**：
   - 显示一个黑色或空白的测试应用界面
   - 这是正常的，WDA 在后台运行

2. **Xcode 控制台**：
   - 显示 "ServerURLHere->" 消息
   - 持续输出设备方向变化等日志

3. **保持运行**：
   - **不要停止 Xcode 中的测试**
   - WDA 需要持续运行才能被 autoglm-webui 使用

## 🔧 常见问题

### 问题 1: "device is locked"

**解决**：解锁你的 iPhone，输入密码

### 问题 2: "Untrusted Developer"

**解决**：
1. iPhone 设置 → 通用 → VPN 与设备管理
2. 信任你的开发者账号

### 问题 3: WDA URL 是 localhost 而不是 WiFi IP

**解决**：两种方式都可以

- **WiFi IP** (如 192.168.1.9:8100)：直接使用，Mac 和 iPhone 在同一网络
- **localhost:8100**：需要使用 `tidevice` 或 `pymobiledevice3` 转发端口

### 问题 4: 找不到设备

**解决**：
```bash
# 重新插拔 USB 线
# 或重新配对设备
idevicepair unpair
idevicepair pair
```

## ✅ 验证成功的标志

WDA 成功运行时：

```bash
$ curl http://192.168.1.9:8100/status
{
  "value": {
    "message": "WebDriverAgent is ready to accept commands",
    "state": "success",
    "os": {
      "version": "18.5",
      "name": "iOS"
    },
    ...
  },
  "sessionId": "..."
}
```

## 🚀 下一步

WDA 启动成功后：

1. **保持 Xcode 运行**（或让 WDA 继续运行）

2. **更新 autoglm-webui 配置**：
   ```bash
   # 编辑 env.sh
   export PHONE_AGENT_WDA_URL="http://192.168.1.9:8100"
   ```

3. **重启 WebUI** （如果正在运行）：
   ```bash
   # 停止当前的 WebUI (Ctrl+C)
   cd /Users/kola/autoglmwebui/autoglm-webui
   ./webui_start.sh
   ```

4. **测试连通性**：
   - 在浏览器打开 http://127.0.0.1:7860/
   - 点击"连通性检测"
   - 应该全部显示 ✅

5. **开始使用**！
   - 输入任务："打开设置"
   - 观看 AI 控制你的 iPhone

---

**提示**：保持 iPhone 解锁并连接（WiFi 或 USB），WDA 才能正常工作。
