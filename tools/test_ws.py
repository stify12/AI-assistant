#!/usr/bin/env python
"""简单的 WebSocket 连接测试"""
import json
import time
import websocket

def on_message(ws, message):
    print(f"收到: {message}")

def on_error(ws, error):
    print(f"错误: {error}")

def on_close(ws, code, msg):
    print(f"关闭: {code} - {msg}")

def on_open(ws):
    print("连接成功!")
    # 发送注册
    ws.send(json.dumps({
        'type': 'register',
        'client_id': 'test_client',
        'ip_address': '127.0.0.1',
        'device_info': {'test': True}
    }))
    print("已发送注册消息")

if __name__ == '__main__':
    websocket.enableTrace(True)  # 启用调试
    ws = websocket.WebSocketApp(
        "ws://47.82.64.147:5000/ws/rfid-simulator",
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )
    ws.run_forever()
