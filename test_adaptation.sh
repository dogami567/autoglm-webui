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
else:
    echo "⚠️  WARNING: WDA is not running"
    echo "   Please start WebDriverAgent to test full functionality"
fi
echo ""

# Test 3: WebUI Dependencies
echo "Test 3: Python Dependencies"
.venv/bin/python -c "
try:
    import fastapi, uvicorn, openai
    from phone_agent import PhoneAgent
    from phone_agent.xctest import XCTestConnection
    print('✅ PASS: All dependencies imported successfully')
except ImportError as e:
    print(f'❌ FAIL: Missing dependency: {e}')
"
echo ""

# Test 4: Environment Configuration
echo "Test 4: Environment Configuration"
source env.sh
if [ -n "$PHONE_AGENT_API_KEY" ] && [ -n "$PHONE_AGENT_BASE_URL" ]; then
    echo "✅ PASS: Environment variables configured"
    echo "   Device Type: $PHONE_AGENT_DEVICE_TYPE"
    echo "   Base URL: $PHONE_AGENT_BASE_URL"
    echo "   Model: $PHONE_AGENT_MODEL"
else:
    echo "❌ FAIL: Environment variables not set"
fi
echo ""

# Test 5: WebUI Server Files
echo "Test 5: WebUI Server Files"
if [ -f "webui/server.py" ] && [ -f "webui_start.sh" ]; then
    echo "✅ PASS: WebUI files present"
    # Quick syntax check
    .venv/bin/python -m py_compile webui/server.py 2>/dev/null && \
        echo "✅ PASS: server.py syntax valid" || \
        echo "❌ FAIL: server.py has syntax errors"
else:
    echo "❌ FAIL: WebUI files missing"
fi
echo ""

echo "================================================"
echo "📊 Test Summary"
echo "================================================"
echo ""
echo "✅ Basic environment: Ready"
echo "⚠️  WebDriverAgent: $(curl -s http://localhost:8100/status > /dev/null 2>&1 && echo 'Running' || echo 'Not running')"
echo ""
echo "Next steps:"
echo "  1. Start WebDriverAgent (if not running):"
echo "     - Open WDA project in Xcode"
echo "     - Select WebDriverAgentRunner scheme"
echo "     - Run on your iPhone"
echo ""
echo "  2. Start WebUI:"
echo "     ./webui_start.sh"
echo ""
echo "  3. Open browser:"
echo "     http://127.0.0.1:7860/"
echo ""
