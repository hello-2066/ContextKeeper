import logging
from langbot_plugin.api.definition.plugin import BasePlugin

# 【规范】使用 __name__ 自动继承框架的日志配置
# 日志会输出到 langbot_plugin_runtime 容器的控制台
logger = logging.getLogger(__name__)

class ContextKeeperPlugin(BasePlugin):
    """
    ContextKeeper (会话上下文持久化插件)
    
    【已实现功能】：
    1. 自动记忆：在对话结束后将问答对(Q&A)持久化存储到磁盘/数据库。
    2. 重启恢复：LangBot 重启或流水线重载后，自动读取历史并注入上下文。
    3. 智能注入：
       - 检测到原生上下文（如 Bot 刚启动或已有记忆）时，自动跳过注入，避免 Token 翻倍浪费。
       - 仅在“失忆”状态下注入最近 20 轮（可配置）对话。
    4. 命令控制：支持 "重置对话"、"/clear" 等指令清除记忆。
    5. 并发保护：修复了流式输出导致多次触发保存时的 "Key not found" 报错。
    """

    async def initialize(self):
        # 插件启动逻辑
        logger.info("ContextKeeper Plugin Initialized (v1.0.0)")

    async def dispose(self):
        # 插件卸载逻辑
        logger.info("ContextKeeper Plugin Disposed")