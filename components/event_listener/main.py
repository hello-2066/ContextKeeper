import json
import logging
import time
import sys
import os

# 1. 基础组件导入
from langbot_plugin.api.definition.components.common.event_listener import EventListener
# 2. 上下文导入
from langbot_plugin.api.entities.context import EventContext
# 3. 事件导入
from langbot_plugin.api.entities import events
# 4. Provider Message
from langbot_plugin.api.entities.builtin.provider import message as provider_message

# ================= 时区强制修正 =================
if hasattr(time, 'tzset'):
    os.environ['TZ'] = 'Asia/Shanghai'
    time.tzset()
# ===============================================

# 使用 __name__ 继承框架配置
logger = logging.getLogger(__name__)

class HistoryLogic(EventListener):
    
    async def initialize(self):
        await super().initialize()
        
        # ================= 日志调整 =================
        logger.setLevel(logging.INFO)
        logging.getLogger("langbot_plugin.runtime.io.handler").setLevel(logging.WARNING)
        
        if not logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            formatter = logging.Formatter('👉 [%(asctime)s] [ContextKeeper] %(message)s', datefmt='%H:%M:%S')
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        # ============================================

        self.HISTORY_PREFIX = "hist_v8_"
        self.TEMP_QUERY_PREFIX = "temp_q_v8_"
        
        try:
            self.handler(events.PersonNormalMessageReceived)(self.on_person_normal_message_received)
            self.handler(events.GroupNormalMessageReceived)(self.on_group_normal_message_received)
            self.handler(events.NormalMessageResponded)(self.on_normal_message_responded)
            self.handler(events.PromptPreProcessing)(self.on_prompt_pre_processing)
            
            logger.info("逻辑组件已启动 (兼容增强版)")
        except Exception as e:
            logger.error(f"启动失败: {e}", exc_info=True)

    def _get_uid(self, ctx: EventContext):
        """智能获取 UID"""
        try:
            event = ctx.event
            # 获取 bot_id，如果没有则默认为 default_bot
            bot_id = str(getattr(ctx, 'bot_id', 'default_bot'))

            launcher_type = str(getattr(event, 'launcher_type', ''))
            if launcher_type == 'group':
                gid = getattr(event, 'launcher_id', None)
                if gid: return f"{bot_id}_group_{gid}"
            
            uid = getattr(event, 'sender_id', getattr(event, 'target_id', getattr(event, 'launcher_id', None)))
            if uid: return f"{bot_id}_{uid}"
            
            session_name = getattr(event, 'session_name', "")
            if session_name:
                raw_uid = session_name.split("_")[-1] if "_" in session_name else session_name
                return f"{bot_id}_{raw_uid}"
            
            return f"{bot_id}_unknown"
        except Exception as e:
            logger.error(f"UID获取异常: {e}")
            return "unknown_all"

    # --- 1. 收到消息 ---
    async def _handle_incoming_message(self, ctx: EventContext):
        try:
            uid = self._get_uid(ctx)
            if uid == "unknown_all": return

            text = getattr(ctx.event, 'text_message', '').strip()
            if not text: return

            # A. 监听重置指令
            reset_keywords = ["重置对话", "重置会话", "/clear", "清除记忆", "清空对话"]
            if any(kw in text for kw in reset_keywords):
                try:
                    # 盲删模式，无需预检
                    await self.plugin.delete_plugin_storage(f"{self.HISTORY_PREFIX}{uid}")
                    await self.plugin.delete_plugin_storage(f"{self.TEMP_QUERY_PREFIX}{uid}")
                except: pass
                
                await self.plugin.set_plugin_storage(f"force_forget_{uid}", b"1")
                logger.info(f"【当前用户: {uid}】 请求重置，已开启强制拦截模式")
                return 

            # B. 正常消息暂存
            await self.plugin.set_plugin_storage(f"{self.TEMP_QUERY_PREFIX}{uid}", text.encode('utf-8'))
        except Exception as e:
            logger.warning(f"暂存消息失败: {e}")

    async def on_person_normal_message_received(self, ctx: EventContext):
        await self._handle_incoming_message(ctx)

    async def on_group_normal_message_received(self, ctx: EventContext):
        await self._handle_incoming_message(ctx)

    # --- 2. 发送前注入 ---
    async def on_prompt_pre_processing(self, ctx: EventContext):
        try:
            uid = self._get_uid(ctx)
            if uid == "unknown_all": return

            current_prompt = ctx.event.prompt or []

            # 盲操作获取强制遗忘标记
            force_forget = None
            try:
                force_forget = await self.plugin.get_plugin_storage(f"force_forget_{uid}")
            except: pass

            if force_forget:
                system_msgs = [m for m in current_prompt if getattr(m, 'role', '') == 'system']
                ctx.event.prompt = system_msgs
                try: await self.plugin.delete_plugin_storage(f"force_forget_{uid}")
                except: pass
                logger.info(f"【当前用户: {uid}】 已强行切断 LangBot 原生记忆")
                return

            has_native_memory = any(
                str(getattr(msg, 'role', '')).lower() in ['assistant', 'bot'] 
                for msg in current_prompt
            )
            if has_native_memory:
                return

            # 盲操作获取历史
            history_bytes = None
            try:
                history_bytes = await self.plugin.get_plugin_storage(f"{self.HISTORY_PREFIX}{uid}")
            except: pass

            if not history_bytes: return

            raw_data = json.loads(history_bytes.decode('utf-8'))
            history = raw_data.get("history", []) if isinstance(raw_data, dict) else []
            if not history: return

            history_messages = []
            for h in history:
                history_messages.append(provider_message.Message(role="user", content=h['q']))
                history_messages.append(provider_message.Message(role="assistant", content=h['a']))
            
            system_msgs = [m for m in current_prompt if getattr(m, 'role', '') == 'system']
            other_msgs = [m for m in current_prompt if getattr(m, 'role', '') != 'system']
            
            ctx.event.prompt = system_msgs + history_messages + other_msgs
            
            logger.info(f"【当前用户: {uid}】 检测到内存失忆，已注入 {len(history)} 条历史")
            
        except Exception as e:
            logger.error(f"注入历史失败: {e}", exc_info=True)

    # --- 3. 回复后保存 ---
    async def on_normal_message_responded(self, ctx: EventContext):
        uid = self._get_uid(ctx)
        if uid == "unknown_all": return

        # 【增强】更通用的回复内容提取，兼容 Markdown
        ai_reply = ""
        try:
            if hasattr(ctx.event, 'response_text') and ctx.event.response_text:
                ai_reply = ctx.event.response_text
            elif hasattr(ctx.event, 'message_chain'):
                # 只要有 text 属性就拼起来，不再局限于 Plain 类型
                ai_reply = "".join([getattr(x, 'text', '') for x in ctx.event.message_chain])
        except: pass
        
        # 如果提取不到回复，打印警告日志帮助排查
        if not ai_reply: 
            # logger.warning(f"【当前用户: {uid}】 未提取到 AI 回复，跳过保存")
            return

        temp_key = f"{self.TEMP_QUERY_PREFIX}{uid}"
        try:
            temp_query_bytes = None
            try:
                temp_query_bytes = await self.plugin.get_plugin_storage(temp_key)
            except: 
                # 找不到暂存问题，可能是并发导致已处理，或者是机器人主动回复
                return

            if not temp_query_bytes: return
            user_query = temp_query_bytes.decode('utf-8')

            history_key = f"{self.HISTORY_PREFIX}{uid}"
            
            data = []
            try:
                old_bytes = await self.plugin.get_plugin_storage(history_key)
                raw_data = json.loads(old_bytes.decode('utf-8'))
                if isinstance(raw_data, list): data = raw_data
                elif isinstance(raw_data, dict) and "history" in raw_data: data = raw_data["history"]
            except: pass

            data.append({"q": user_query, "a": str(ai_reply)})
            
            limit = 20
            try:
                config = await self.plugin.get_config()
                if config:
                    limit = int(config.get('max_history_rounds', 20))
            except: limit = 20
            
            data = data[-max(1, limit):]
            save_data = {"updated_at": int(time.time()), "history": data}
            await self.plugin.set_plugin_storage(history_key, json.dumps(save_data).encode('utf-8'))
            try: await self.plugin.delete_plugin_storage(temp_key)
            except: pass
            
            logger.info(f"【当前用户: {uid}】 保存成功 (保留{len(data)}/{limit}条)")
            
        except Exception as e:
            logger.error(f"保存失败: {e}", exc_info=True)