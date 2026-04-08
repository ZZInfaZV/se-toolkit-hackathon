"""WebChat channel — WebSocket server for web clients."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any
from urllib.parse import parse_qs, urlparse

import websockets
from websockets.asyncio.server import Server as WebSocketServer
from websockets.asyncio.server import ServerConnection
from loguru import logger
from pydantic import Field

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import Base

from .structured import parse_outbound


# HTML page for the web chat
HTML_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Schedule Bot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .chat-container {
            width: 100%;
            max-width: 800px;
            height: 90vh;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .chat-header h1 { font-size: 24px; font-weight: 600; }
        .status { font-size: 12px; margin-top: 5px; opacity: 0.9; }
        .status.connected { color: #4ade80; }
        .status.disconnected { color: #f87171; }
        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        .message {
            margin-bottom: 15px;
            display: flex;
            flex-direction: column;
        }
        .message.user { align-items: flex-end; }
        .message.bot { align-items: flex-start; }
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.5;
            word-wrap: break-word;
        }
        .message.user .message-content {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-bottom-right-radius: 4px;
        }
        .message.bot .message-content {
            background: white;
            color: #1f2937;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .message-time { font-size: 11px; color: #9ca3af; margin-top: 4px; }
        .input-area {
            padding: 20px;
            background: white;
            border-top: 1px solid #e5e7eb;
            display: flex;
            gap: 10px;
        }
        .input-area input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e5e7eb;
            border-radius: 25px;
            font-size: 14px;
            outline: none;
            transition: border-color 0.3s;
        }
        .input-area input:focus { border-color: #667eea; }
        .input-area button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            font-size: 14px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        .input-area button:hover { transform: translateY(-2px); }
        .input-area button:disabled { opacity: 0.5; cursor: not-allowed; }
        .typing-indicator {
            display: none;
            padding: 12px 16px;
            background: white;
            border-radius: 18px;
            border-bottom-left-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 15px;
        }
        .typing-indicator.show { display: inline-block; }
        .typing-indicator span {
            height: 8px; width: 8px;
            background: #9ca3af;
            border-radius: 50%;
            display: inline-block;
            margin: 0 2px;
            animation: typing 1.4s infinite;
        }
        .typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
        .typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }
        .welcome-message { text-align: center; color: #6b7280; padding: 40px 20px; }
        .welcome-message h2 { color: #1f2937; margin-bottom: 10px; }
        .quick-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
            margin-top: 20px;
        }
        .quick-action-btn {
            padding: 8px 16px;
            background: white;
            border: 2px solid #667eea;
            border-radius: 20px;
            color: #667eea;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .quick-action-btn:hover { background: #667eea; color: white; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>📅 Schedule Bot</h1>
            <div class="status" id="status">Подключение...</div>
        </div>
        <div class="messages" id="messages">
            <div class="welcome-message">
                <h2>Привет! 👋</h2>
                <p>Я ваш помощник по расписанию. Спросите меня о занятиях!</p>
                <div class="quick-actions">
                    <button class="quick-action-btn" onclick="sendQuick('Какое у меня расписание на сегодня?')">📅 Сегодня</button>
                    <button class="quick-action-btn" onclick="sendQuick('Какое у меня расписание на неделю?')">📆 На неделю</button>
                    <button class="quick-action-btn" onclick="sendQuick('Какое сейчас занятие?')">⏰ Сейчас</button>
                    <button class="quick-action-btn" onclick="sendQuick('Где проходит Data Structures and Algorithms?')">📍 Кабинет</button>
                </div>
            </div>
        </div>
        <div class="typing-indicator" id="typing"><span></span><span></span><span></span></div>
        <div class="input-area">
            <input type="text" id="msgInput" placeholder="Введите сообщение..." disabled>
            <button id="sendBtn" disabled>Отправить</button>
        </div>
    </div>
    <script>
        const messagesDiv = document.getElementById('messages');
        const msgInput = document.getElementById('msgInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusDiv = document.getElementById('status');
        const typingDiv = document.getElementById('typing');
        let ws = null;
        let reconnectAttempts = 0;
        const maxReconnect = 10;
        function getWsUrl() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const key = '__ACCESS_KEY__';
            return `${protocol}//${window.location.host}/ws?access_key=${key}`;
        }
        function connect() {
            ws = new WebSocket(getWsUrl());
            ws.onopen = () => {
                statusDiv.textContent = 'Подключено ✓';
                statusDiv.className = 'status connected';
                msgInput.disabled = false;
                sendBtn.disabled = false;
                msgInput.focus();
                reconnectAttempts = 0;
            };
            ws.onmessage = (e) => {
                typingDiv.classList.remove('show');
                try {
                    const data = JSON.parse(e.data);
                    if (data.content) addMessage(data.content, 'bot');
                } catch(err) { addMessage(e.data, 'bot'); }
            };
            ws.onclose = () => {
                statusDiv.textContent = 'Отключено ✗';
                statusDiv.className = 'status disconnected';
                msgInput.disabled = true;
                sendBtn.disabled = true;
                typingDiv.classList.remove('show');
                if (reconnectAttempts < maxReconnect) {
                    reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
                    statusDiv.textContent = `Переподключение через ${delay/1000}с...`;
                    setTimeout(connect, delay);
                } else {
                    statusDiv.textContent = 'Ошибка подключения. Обновите страницу.';
                }
            };
        }
        function addMessage(text, type) {
            const welcome = messagesDiv.querySelector('.welcome-message');
            if (welcome) welcome.remove();
            const msgDiv = document.createElement('div');
            msgDiv.className = `message ${type}`;
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = text;
            const timeDiv = document.createElement('div');
            timeDiv.className = 'message-time';
            timeDiv.textContent = new Date().toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit'});
            msgDiv.appendChild(contentDiv);
            msgDiv.appendChild(timeDiv);
            messagesDiv.appendChild(msgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        function sendMessage() {
            const text = msgInput.value.trim();
            if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
            addMessage(text, 'user');
            ws.send(JSON.stringify({content: text}));
            msgInput.value = '';
            typingDiv.classList.add('show');
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        function sendQuick(text) { msgInput.value = text; sendMessage(); }
        msgInput.addEventListener('keypress', (e) => { if (e.key === 'Enter') sendMessage(); });
        sendBtn.addEventListener('click', sendMessage);
        connect();
    </script>
</body>
</html>"""


class WebChatConfig(Base):
    """WebChat channel configuration."""

    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8765
    allow_from: list[str] = Field(default_factory=lambda: ["*"])


class WebChatChannel(BaseChannel):
    """WebSocket-based web chat channel.

    Each WebSocket connection is treated as an independent chat session.
    Protocol (JSON):
        Client -> Server:  {"content": "hello"}
        Server -> Client:  {"content": "response text"}

    Access control:
        Set NANOBOT_ACCESS_KEY env var to require authentication.
        Clients pass the key via query parameter: ws://host:port?access_key=SECRET
        Connections without a valid key are rejected. LMS-aware clients may
        also provide ?api_key=...; when present it is forwarded to the agent
        as a prompt prefix for backwards compatibility.
    """

    name = "webchat"
    display_name = "WebChat"

    @classmethod
    def default_config(cls) -> dict[str, Any]:
        return WebChatConfig().model_dump(by_alias=True)

    def __init__(self, config: Any, bus: MessageBus):
        if isinstance(config, dict):
            config = WebChatConfig.model_validate(config)
        super().__init__(config, bus)
        self.config: WebChatConfig = config
        self._connections: dict[str, ServerConnection] = {}
        self._server: WebSocketServer | None = None
        self._access_key: str = os.environ.get("NANOBOT_ACCESS_KEY", "")

    async def start(self) -> None:
        """Start the WebSocket server."""
        self._running = True
        if not self._access_key:
            raise RuntimeError("WebChat: NANOBOT_ACCESS_KEY must be set")
        logger.info("WebChat starting on {}:{}", self.config.host, self.config.port)
        
        # Prepare HTML page with access key
        html_page = HTML_PAGE.replace("__ACCESS_KEY__", self._access_key)
        self._html_bytes = html_page.encode('utf-8')
        
        # Start HTTP server for serving HTML
        import aiohttp
        from aiohttp import web
        
        self._aiohttp = {'web': web, 'aiohttp': aiohttp}
        
        self._aiohttp_app = web.Application()
        self._aiohttp_app.router.add_get('/', self._http_handler)
        self._aiohttp_app.router.add_get('/ws', self._ws_handler)
        
        self._aiohttp_runner = web.AppRunner(self._aiohttp_app)
        await self._aiohttp_runner.setup()
        self._aiohttp_site = web.TCPSite(self._aiohttp_runner, self.config.host, self.config.port)
        await self._aiohttp_site.start()
        logger.info("WebChat HTTP server started on {}:{}", self.config.host, self.config.port)
        
        while self._running:
            await asyncio.sleep(1)
    
    async def _http_handler(self, request):
        """Serve the HTML web UI."""
        web = self._aiohttp['web']
        return web.Response(
            text=self._html_bytes.decode('utf-8'),
            content_type='text/html',
            headers={'Cache-Control': 'no-cache'}
        )
    
    async def _ws_handler(self, request):
        """Handle WebSocket connections."""
        web = self._aiohttp['web']
        aiohttp = self._aiohttp['aiohttp']
        
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        # Wrap aiohttp WebSocket to look like websockets ServerConnection
        # We need to handle the connection through our existing handler
        # But first, let's validate the access key
        client_key = request.query.get('access_key', '')
        api_key = request.query.get('api_key', '').strip()
        
        if self._access_key and client_key != self._access_key:
            logger.warning("WebChat: rejected connection — invalid access key")
            await ws.close(code=4001, message=b'Invalid access key')
            return ws
        
        chat_id = str(uuid.uuid4())
        
        # Create a wrapper that mimics websockets.ServerConnection
        class WsWrapper:
            def __init__(self, ws):
                self._ws = ws
                self.request = type('Request', (), {'path': request.path})()
            
            async def send(self, data):
                await self._ws.send_str(data)
            
            async def close(self, code=1000, reason=''):
                await self._ws.close(code=code, message=reason.encode())
        
        wrapper = WsWrapper(ws)
        self._connections[chat_id] = wrapper
        sender_id = chat_id
        
        logger.info("WebChat: new connection chat_id={}", chat_id)
        
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        content = data.get("content", "").strip()
                    except (json.JSONDecodeError, AttributeError):
                        content = str(msg.data).strip()
                    
                    if not content:
                        continue
                    
                    if api_key:
                        content = f"[LMS_API_KEY={api_key}] {content}"
                    
                    await self._handle_message(
                        sender_id=sender_id,
                        chat_id=chat_id,
                        content=content,
                    )
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break
        finally:
            self._connections.pop(chat_id, None)
            logger.info("WebChat: disconnected chat_id={}", chat_id)
        
        return ws

    async def _process_http_request(self, path, request_headers):
        """Handle HTTP requests to serve the web UI."""
        # Check if this is a regular HTTP request (not a WebSocket upgrade)
        connection_header = request_headers.get("Connection", "")
        upgrade_header = request_headers.get("Upgrade", "")
        
        # If no WebSocket upgrade headers, serve the HTML page
        if "upgrade" not in connection_header.lower() or not upgrade_header:
            headers = [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(self._html_bytes))),
                ("Cache-Control", "no-cache"),
            ]
            return (200, headers, self._html_bytes)
        # Return None to proceed with WebSocket handshake
        return None

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        self._running = False
        if hasattr(self, '_aiohttp_runner'):
            await self._aiohttp_runner.cleanup()
        self._connections.clear()

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message back to the client via its WebSocket."""
        ws = self._connections.get(msg.chat_id)
        if ws is None:
            logger.warning("WebChat: no connection for chat_id={}", msg.chat_id)
            return
        try:
            result = parse_outbound(msg.content)
            await ws.send(result.model_dump_json())
        except websockets.ConnectionClosed:
            logger.info("WebChat: connection closed for chat_id={}", msg.chat_id)
            self._connections.pop(msg.chat_id, None)

    async def _handle_ws(self, ws: ServerConnection) -> None:
        """Handle a single WebSocket connection lifecycle."""
        # Validate access key
        path: str = ws.request.path if ws.request is not None else ""
        qs = parse_qs(urlparse(path).query)
        client_key: str = qs.get("access_key", [""])[0]
        api_key: str = qs.get("api_key", [""])[0].strip()

        if self._access_key and client_key != self._access_key:
            logger.warning("WebChat: rejected connection — invalid access key")
            await ws.close(4001, "Invalid access key")
            return

        chat_id = str(uuid.uuid4())
        self._connections[chat_id] = ws
        sender_id = chat_id

        logger.info("WebChat: new connection chat_id={}", chat_id)

        try:
            async for raw in ws:
                try:
                    data = json.loads(raw)
                    content = data.get("content", "").strip()
                except (json.JSONDecodeError, AttributeError):
                    content = str(raw).strip()

                if not content:
                    continue

                if api_key:
                    # Preserve the legacy per-user LMS credential flow used by
                    # the Telegram client without reusing it as deployment auth.
                    content = f"[LMS_API_KEY={api_key}] {content}"

                await self._handle_message(
                    sender_id=sender_id,
                    chat_id=chat_id,
                    content=content,
                )
        except websockets.ConnectionClosed:
            pass
        finally:
            self._connections.pop(chat_id, None)
            logger.info("WebChat: disconnected chat_id={}", chat_id)
