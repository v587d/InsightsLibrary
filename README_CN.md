# 研报知识库 MCP 服务器 

[>>>English Version]()

>🍭一个免费的、即插即用的知识库。内置10,000+份高质量洞察报告(Research Report、Insight Report)、封装成MCP Server、本地数据安全存储。

⚠️⚠️ 本项目所有采集的研报，均来自各研报官网免费资源。⚠️⚠️
## 特点
1. 🍾无需配置任何API TOKEN，主打一个即插即用。若您需解析私有文档，`.env` 可配置VLM模型和相关参数，如：`VLM_MODEL_NAME=qwen2.5-vl-72b-instruct`。
2. 🦉永久免费，无需考虑浪费心智收集报告资源。欢迎大家通过`issue`分享可靠的、无版权纠纷研报资源。
3. 📢承诺至少每周一次研报资源，但改bug就看个人心情了，毕竟我不是程序员🤭。


## 安装方法（对无编程基础用户友好）

>💡tips: 若实在搞不定，可将该页面拖到LLM客户端（比如[DeepSeek](https://chat.deepseek.com/)）让AI一步步教您安装🦾。

```json
{
  "mcpServers": {
    "ikb-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "<Your Project Root Directory!!!>", 
        "run",
        "ikb_mcp_server.py"
      ]
    }
  }
}
```