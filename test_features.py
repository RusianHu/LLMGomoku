#!/usr/bin/env python3
"""
测试LLMGomoku新功能的脚本
Test script for LLMGomoku new features
"""

import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000"

def test_game_state():
    """测试游戏状态API"""
    print("=== 测试游戏状态 ===")
    response = requests.get(f"{BASE_URL}/api/game/state")
    if response.status_code == 200:
        data = response.json()
        print(f"游戏状态: {data.get('game_over', 'Unknown')}")
        print(f"当前玩家: {data.get('current_player', 'Unknown')}")
        print(f"回合数: {data.get('round_number', 'Unknown')}")
        print(f"AI最新落子: {data.get('last_ai_move', 'None')}")
        return True
    else:
        print(f"获取游戏状态失败: {response.status_code}")
        return False

def test_debug_info():
    """测试调试信息API"""
    print("\n=== 测试调试信息 ===")
    response = requests.get(f"{BASE_URL}/api/game/debug")
    if response.status_code == 200:
        data = response.json()
        print(f"调试模式启用: {data.get('debug_enabled', False)}")
        if data.get('debug_enabled'):
            print(f"最新请求时间: {data.get('last_request_time', 0):.3f}s")
            print(f"有最新请求: {'是' if data.get('last_request') else '否'}")
            print(f"有最新响应: {'是' if data.get('last_response') else '否'}")
            print(f"历史记录数量: {len(data.get('request_history', []))}")
        return True
    elif response.status_code == 404:
        print("调试模式未启用")
        return True
    else:
        print(f"获取调试信息失败: {response.status_code}")
        return False

def test_context_info():
    """测试上下文信息API"""
    print("\n=== 测试上下文信息 ===")
    response = requests.get(f"{BASE_URL}/api/game/context")
    if response.status_code == 200:
        data = response.json()
        print(f"LLM提供商: {data.get('llm_provider', 'Unknown')}")
        print(f"模型: {data.get('model', 'Unknown')}")
        print(f"对话轮数: {data.get('conversation_count', 0)}")
        print(f"总消耗Token: {data.get('total_consumed_tokens', 0)}")
        return True
    else:
        print(f"获取上下文信息失败: {response.status_code}")
        return False

def test_make_move():
    """测试下棋功能"""
    print("\n=== 测试下棋功能 ===")
    
    # 先重置游戏
    reset_response = requests.post(f"{BASE_URL}/api/game/reset")
    if reset_response.status_code != 200:
        print("重置游戏失败")
        return False
    
    print("游戏已重置")
    
    # 玩家下棋 (中心位置)
    move_data = {"row": 7, "col": 7}
    response = requests.post(f"{BASE_URL}/api/game/move", json=move_data)
    
    if response.status_code == 200:
        data = response.json()
        print(f"玩家下棋成功: (7, 7)")
        if data.get('ai_move'):
            ai_move = data['ai_move']
            print(f"AI下棋: ({ai_move['row']}, {ai_move['col']})")
            print(f"AI思路: {ai_move['reasoning'][:100]}...")
        return True
    else:
        print(f"下棋失败: {response.status_code}")
        try:
            error_data = response.json()
            print(f"错误详情: {error_data.get('detail', 'Unknown error')}")
        except:
            pass
        return False

def main():
    """主测试函数"""
    print("LLMGomoku 功能测试")
    print("=" * 50)
    
    # 测试服务器连接
    try:
        response = requests.get(f"{BASE_URL}/api/game/state", timeout=5)
        print("✓ 服务器连接正常")
    except requests.exceptions.RequestException as e:
        print(f"✗ 服务器连接失败: {e}")
        print("请确保服务器正在运行 (python main.py)")
        return
    
    # 运行各项测试
    tests = [
        ("游戏状态", test_game_state),
        ("调试信息", test_debug_info),
        ("上下文信息", test_context_info),
        ("下棋功能", test_make_move),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"{'✓' if result else '✗'} {test_name}测试{'通过' if result else '失败'}")
        except Exception as e:
            print(f"✗ {test_name}测试异常: {e}")
            results.append((test_name, False))
    
    # 总结
    print("\n" + "=" * 50)
    print("测试总结:")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"通过: {passed}/{total}")
    
    if passed == total:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请检查相关功能")

if __name__ == "__main__":
    main()
