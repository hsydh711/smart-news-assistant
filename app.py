#!/usr/bin/env python3
"""
智能新闻助手 - API代理服务
这是一个后端代理，用于连接前端和LangChain Agent
"""

import os
import json
import asyncio
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from typing import Dict, Any
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入Agent构建函数
from agents.agent import build_agent

app = Flask(__name__)
# 允许跨域请求
CORS(app)

# 全局Agent实例
agent = None

def get_agent():
    """获取或创建Agent实例"""
    global agent
    if agent is None:
        agent = build_agent()
    return agent

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({
        'status': 'healthy',
        'message': 'API代理服务运行正常'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    聊天接口 - 非流式
    """
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': '缺少message参数'}), 400

        user_message = data['message']
        session_id = data.get('session_id', 'default')

        # 获取Agent实例
        agent_instance = get_agent()

        # 调用Agent
        config = {"configurable": {"thread_id": session_id}}
        result = agent_instance.invoke(
            {"messages": [user_message]},
            config=config
        )

        # 提取回复内容
        response_message = result['messages'][-1].content

        return jsonify({
            'success': True,
            'response': response_message
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'error': str(e),
            'message': '处理请求时出错'
        }), 500

@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    聊天接口 - 流式响应
    返回SSE (Server-Sent Events) 格式的流式数据
    """
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': '缺少message参数'}), 400

        user_message = data['message']
        session_id = data.get('session_id', 'default')

        # 获取Agent实例
        agent_instance = get_agent()

        # 定义生成器函数
        def generate():
            try:
                config = {"configurable": {"thread_id": session_id}}

                # 使用stream方法
                for chunk in agent_instance.stream(
                    {"messages": [user_message]},
                    config=config
                ):
                    # 提取内容
                    if 'messages' in chunk:
                        for message in chunk['messages']:
                            if hasattr(message, 'content') and message.content:
                                # 发送SSE格式的数据
                                yield f"data: {json.dumps({'content': message.content})}\n\n"

                # 发送结束标记
                yield "data: [DONE]\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        # 返回流式响应
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'
            }
        )

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({
            'error': str(e),
            'message': '处理请求时出错'
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'False') == 'True'
    host = os.environ.get('HOST', '0.0.0.0')

    print(f"🚀 智能新闻助手API代理服务启动中...")
    print(f"📍 访问地址: http://{host}:{port}")
    print(f"💡 健康检查: http://{host}:{port}/health")
    print(f"💬 聊天接口: http://{host}:{port}/api/chat/stream")

    app.run(host=host, port=port, debug=debug, threaded=True)
