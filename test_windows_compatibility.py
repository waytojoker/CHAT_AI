#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows兼容性测试脚本
"""

import asyncio
import json
import platform
from modules.mcp_client import MCPClient, MCPToolCaller, MCPServerConfig, MCPServer, run_async_function

async def test_windows_compatibility():
    """测试Windows兼容性"""
    
    print("🚀 Windows兼容性测试")
    print(f"操作系统: {platform.system()}")
    print(f"平台: {platform.platform()}")
    
    # 创建MCP客户端
    mcp_client = MCPClient()
    tool_caller = MCPToolCaller(mcp_client)
    
    # 检查系统类型
    is_windows = platform.system() == "Windows"
    print(f"是否为Windows系统: {is_windows}")
    
    # 自动配置knowledge-base服务器
    print("\n📋 配置knowledge-base服务器...")
    try:
        config_obj = MCPServerConfig(
            name="knowledge-base",
            command="node",
            args=["dist/index.js"],
            env={},
            server_type="process"
        )
        
        server = MCPServer(
            name="knowledge-base",
            config=config_obj,
            tools=[]
        )
        
        # 添加到客户端
        mcp_client.servers["knowledge-base"] = server
        
        # 启动服务器
        print("🔧 启动MCP服务器...")
        success = await mcp_client.start_server("knowledge-base")
        if success:
            print("✅ 服务器启动成功")
        else:
            print("❌ 服务器启动失败")
            return
            
    except Exception as e:
        print(f"❌ 配置MCP服务器失败: {str(e)}")
        return
    
    # 检查可用工具
    print("\n📚 检查可用工具...")
    all_tools = mcp_client.get_available_tools()
    
    if any(tools for tools in all_tools.values()):
        print("✅ 找到可用工具:")
        for server_name, tools in all_tools.items():
            if tools:
                print(f"  🔧 {server_name}服务器 ({len(tools)}个工具):")
                for tool in tools:
                    print(f"    • {tool.name}: {tool.description}")
    else:
        print("❌ 没有可用的MCP工具")
        print("这可能是因为Windows兼容性问题导致的")
        return
    
    # 测试工具调用
    print("\n🧪 测试工具调用...")
    
    # 测试获取统计信息
    print("\n1️⃣ 测试获取统计信息...")
    try:
        result = await mcp_client.call_tool("knowledge-base", "get_stats", {})
        print(f"✅ 统计信息: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"❌ 获取统计信息失败: {str(e)}")
    
    # 测试查询知识库
    print("\n2️⃣ 测试查询知识库...")
    try:
        result = await mcp_client.call_tool("knowledge-base", "query_knowledge_base", {
            "question": "什么是人工智能？",
            "max_results": 3
        })
        print(f"✅ 查询结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    except Exception as e:
        print(f"❌ 查询知识库失败: {str(e)}")
    
    # 测试文本解析
    print("\n3️⃣ 测试文本解析...")
    test_text = '{"tool_call": {"server": "knowledge-base", "tool": "query_knowledge_base", "arguments": {"question": "机器学习", "max_results": 2}}}'
    
    tool_calls = tool_caller._parse_tool_calls_from_text(test_text)
    if tool_calls:
        print(f"✅ 解析到 {len(tool_calls)} 个工具调用")
        for tool_call in tool_calls:
            print(f"  - 服务器: {tool_call['server']}")
            print(f"  - 工具: {tool_call['tool']}")
            print(f"  - 参数: {tool_call['arguments']}")
    else:
        print("❌ 没有解析到工具调用")
    
    # 测试执行工具调用
    print("\n4️⃣ 测试执行工具调用...")
    try:
        results = await tool_caller.parse_and_execute_tools(test_text)
        if results:
            print(f"✅ 执行了 {len(results)} 个工具调用")
            formatted_results = tool_caller.format_tool_result(results)
            print("执行结果:")
            print(formatted_results)
        else:
            print("❌ 没有执行任何工具调用")
    except Exception as e:
        print(f"❌ 执行工具调用失败: {str(e)}")
    
    print("\n✅ Windows兼容性测试完成")

def test_platform_detection():
    """测试平台检测"""
    
    print("\n🔍 平台检测测试")
    print(f"platform.system(): {platform.system()}")
    print(f"platform.platform(): {platform.platform()}")
    print(f"platform.machine(): {platform.machine()}")
    print(f"platform.processor(): {platform.processor()}")
    
    # 测试条件判断
    is_windows = platform.system() == "Windows"
    is_unix = platform.system() in ["Linux", "Darwin"]
    
    print(f"是否为Windows: {is_windows}")
    print(f"是否为Unix/Linux: {is_unix}")

if __name__ == "__main__":
    print("🎯 Windows兼容性测试程序")
    print("=" * 50)
    
    # 测试平台检测
    test_platform_detection()
    
    # 运行兼容性测试
    try:
        asyncio.run(test_windows_compatibility())
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
    
    print("\n" + "=" * 50)
    print("测试完成") 