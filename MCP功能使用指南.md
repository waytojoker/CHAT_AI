# MCP功能使用指南

## 概述

MCP (Model Context Protocol) 是一个用于连接AI模型与外部工具和数据的协议。本指南将详细介绍如何在你的项目中集成和使用MCP功能。

## 1. 安装MCP服务端

### 1.1 克隆MCP知识库服务端

首先，从GitHub克隆MCP知识库服务端：

```bash
# 进入你的项目目录
cd /Users/yangjiayi15

# 克隆MCP知识库服务端
git clone https://github.com/ikungsjl/mcp-knowledge-base.git MCP

# 进入MCP目录
cd MCP

# 安装依赖
npm install

# 构建项目
npm run build
```

### 1.2 验证安装

构建完成后，你应该在`/Users/yangjiayi15/MCP/dist/`目录下看到`index.js`文件。

## 2. 配置MCP服务器

### 2.1 创建MCP配置文件

在你的项目根目录创建一个MCP配置文件，例如`mcp_config.json`：

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "node",
      "args": ["/Users/yangjiayi15/MCP/dist/index.js"],
      "env": {}
    }
  }
}
```

**重要说明：**
- `command`: 使用`node`来执行JavaScript文件
- `args`: 包含MCP服务端的完整路径
- `env`: 环境变量配置（通常为空对象）

### 2.2 路径配置说明

确保路径配置正确：
- 使用绝对路径：`/Users/yangjiayi15/MCP/dist/index.js`
- 路径中不能包含空格或特殊字符
- 确保文件存在且有执行权限

## 3. Streamlit前端配置

### 3.1 启用MCP功能

在Streamlit应用中：

1. **启用MCP工具调用**：在侧边栏勾选"启用MCP工具调用"
2. **选择模式**：
   - **AI自主选择工具**：AI自动判断何时使用工具
   - **手动指定工具**：用户手动指定工具调用

### 3.2 导入MCP配置

在Streamlit界面中：

1. 点击"导入MCP配置"按钮
2. 在配置对话框中输入你的MCP配置：

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "node",
      "args": ["/Users/yangjiayi15/MCP/dist/index.js"],
      "env": {}
    }
  }
}
```

3. 点击"导入配置"按钮
4. 系统会自动启动MCP服务器并加载可用工具

### 3.3 验证配置

导入成功后，你应该能看到：
- 服务器状态显示为"已启动"
- 工具列表中显示可用的工具（如：add_document, query_knowledge_base等）

## 4. 使用MCP功能

### 4.1 AI自主选择工具模式

在这种模式下，AI会自动判断何时需要使用工具：

1. 选择"AI自主选择工具"模式
2. 直接提问，例如：
   - "帮我查询一下人工智能的最新发展"
   - "添加一个文档到知识库"
   - "搜索关于机器学习的信息"

AI会自动调用相应的工具并返回结果。

### 4.2 手动指定工具模式

在这种模式下，你需要使用特定语法手动调用工具：

#### 语法格式

```
@tool:服务器名:工具名{参数JSON}
```

#### 使用示例

```bash
# 查询知识库
@tool:knowledge-base:query_knowledge_base{"question": "人工智能发展趋势", "max_results": 5}

# 添加文档到知识库
@tool:knowledge-base:add_document{"file_path": "/path/to/document.pdf"}

# 获取知识库统计信息
@tool:knowledge-base:get_stats{}

# 列出所有文档
@tool:knowledge-base:list_documents{}
```

### 4.3 工具调用信息展示

在手动模式下，系统会显示：
- **检测到的工具调用**：显示将要调用的工具信息
- **手动工具执行结果**：显示工具执行的结果

## 5. 可用工具列表

MCP知识库服务端提供以下工具：

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `add_document` | 添加单个文档到知识库 | `file_path`: 文档文件路径 |
| `add_directory` | 添加目录中的所有文档到知识库 | `directory_path`: 目录路径 |
| `query_knowledge_base` | 查询知识库 | `question`: 查询问题, `max_results`: 最大返回结果数, `threshold`: 相似度阈值 |
| `list_documents` | 列出知识库中的所有文档 | 无 |
| `get_document` | 获取特定文档信息 | `document_id`: 文档ID |
| `remove_document` | 从知识库中移除文档 | `document_id`: 文档ID |
| `clear_knowledge_base` | 清空知识库 | 无 |
| `get_stats` | 获取知识库统计信息 | 无 |

## 6. 故障排除

### 6.1 常见问题

**问题1：MCP服务器启动失败**
- 检查路径是否正确
- 确保Node.js已安装
- 验证MCP服务端是否已构建

**问题2：工具调用失败**
- 检查服务器是否已启动
- 验证工具参数格式是否正确
- 查看错误日志获取详细信息

**问题3：配置文件导入失败**
- 检查JSON格式是否正确
- 确保路径使用绝对路径
- 验证文件权限

### 6.2 调试步骤

1. **检查MCP服务端状态**：
   ```bash
   cd /Users/yangjiayi15/MCP
   node dist/index.js
   ```

2. **查看Streamlit日志**：
   - 在终端中查看Streamlit运行日志
   - 检查是否有错误信息

3. **验证工具列表**：
   - 在Streamlit界面中查看工具列表是否正常显示
   - 确认工具数量是否正确

## 7. 高级配置

### 7.1 环境变量配置

如果需要配置环境变量，可以在配置中添加：

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "node",
      "args": ["/Users/yangjiayi15/MCP/dist/index.js"],
      "env": {
        "NODE_ENV": "production",
        "DEBUG": "true"
      }
    }
  }
}
```

### 7.2 多服务器配置

可以配置多个MCP服务器：

```json
{
  "mcpServers": {
    "knowledge-base": {
      "command": "node",
      "args": ["/Users/yangjiayi15/MCP/dist/index.js"],
      "env": {}
    },
    "another-server": {
      "command": "python",
      "args": ["/path/to/another/server.py"],
      "env": {}
    }
  }
}
```

## 8. 最佳实践

1. **路径管理**：使用绝对路径避免路径问题
2. **错误处理**：在工具调用失败时查看详细错误信息
3. **性能优化**：合理设置查询参数（如max_results）
4. **安全考虑**：确保MCP服务端的安全性
5. **日志记录**：保持日志记录以便调试

## 9. 更新和维护

### 9.1 更新MCP服务端

```bash
cd /Users/yangjiayi15/MCP
git pull origin main
npm install
npm run build
```

### 9.2 备份配置

定期备份你的MCP配置文件，以便在需要时快速恢复。

---

通过以上步骤，你就可以成功集成和使用MCP功能了。如果在使用过程中遇到问题，请参考故障排除部分或查看相关日志信息。 