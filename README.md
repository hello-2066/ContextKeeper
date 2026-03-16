ContextKeeper (Conversation Persistence)
Say goodbye to bot "amnesia"! Keep your LangBot conversation history continuous and persistent across restarts.

ContextKeeper is a context management plugin designed for LangBot. It solves the issue where conversation context is lost after container restarts, pipeline reloads, or configuration updates.

⚠️Platform Compatibility: This plugin has been developed and verified specifically for WeChat Work (Enterprise WeChat) Smart Bots. While it may work on other platforms, it has not been tested elsewhere.

✨ Key Features
1. Automatic Persistence
Automatically saves user queries and AI responses (Q&A) to local storage after every conversation turn.

2. Seamless Recovery
Automatically restores conversation history after LangBot restarts or pipeline reloads.
🧠

3. Smart Context Injection
Token Saving: Automatically detects if native context exists (e.g., a newly started conversation or bot memory). If so, it skips injection to prevent token waste.
Auto-Completion: Injects the last 20 rounds (configurable) of conversation history only when "amnesia" is detected.

4. Command Control
Supports commands to clear memory and start a fresh topic.
Commands
Send any of the following keywords in the chat to clear the current user's history memory:
SOURCE CODE
/clear
SOURCE CODE
重置对话
(Reset Chat)
SOURCE CODE
重置会话
(Reset Session)
SOURCE CODE
清除记忆
(Clear Memory)
SOURCE CODE
清空对话
(Empty Chat)