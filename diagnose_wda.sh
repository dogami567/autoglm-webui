#!/bin/bash

echo "🔍 WebDriverAgent 诊断工具"
echo "================================"
echo ""

# 1. 检查 WDA 进程
echo "1️⃣ 检查 WDA 进程..."
WDA_PROCESS=$(ps aux | grep -i "WebDriverAgent" | grep -v grep)
if [ -z "$WDA_PROCESS" ]; then
    echo "   ❌ WDA 进程未运行"
    echo "   → 请在 Xcode 中运行 WebDriverAgentRunner"
else
    echo "   ✅ WDA 进程正在运行"
    echo "$WDA_PROCESS" | head -2
fi
echo ""

# 2. 检查监听端口
echo "2️⃣ 检查 8100-8200 端口..."
PORTS=$(lsof -iTCP -sTCP:LISTEN -P | grep -E "8[12][0-9]{2}")
if [ -z "$PORTS" ]; then
    echo "   ❌ 未发现 8100-8200 端口监听"
else
    echo "   ✅ 发现监听端口:"
    echo "$PORTS"
fi
echo ""

# 3. 检查设备连接
echo "3️⃣ 检查 iOS 设备..."
DEVICES=$(idevice_id -l)
if [ -z "$DEVICES" ]; then
    echo "   ❌ 未检测到 iOS 设备"
else
    echo "   ✅ iOS 设备已连接:"
    echo "   $DEVICES"
fi
echo ""

# 4. 测试常见 URL
echo "4️⃣ 测试 WDA 连接..."
for url in "http://localhost:8100" "http://127.0.0.1:8100" "http://192.168.1.5:8100" "http://192.168.1.9:8100"; do
    RESULT=$(curl -s -m 2 "$url/status" 2>&1)
    if echo "$RESULT" | grep -q "sessionId\|state\|message"; then
        echo "   ✅ WDA 在 $url 运行！"
        echo "$RESULT" | python3 -m json.tool 2>/dev/null | head -10
        break
    else
        echo "   ❌ $url 无响应"
    fi
done
echo ""

echo "================================"
echo ""
echo "📋 下一步建议:"
echo ""
echo "如果 WDA 进程未运行:"
echo "  1. 打开 Xcode"
echo "  2. 打开项目: ~/WebDriverAgent/WebDriverAgent.xcodeproj"
echo "  3. 选择 scheme: WebDriverAgentRunner"
echo "  4. 选择设备: Huawei Mate 11 Pro"
echo "  5. 点击运行 (▶️)"
echo ""
echo "如果 WDA 已运行但无法连接:"
echo "  1. 查看 Xcode 控制台"
echo "  2. 找到 'ServerURLHere->http://...' 消息"
echo "  3. 将该 URL 更新到 env.sh 中的 PHONE_AGENT_WDA_URL"
echo ""
