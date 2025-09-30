"""WebSocket连接管理API"""

import json
import asyncio
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse

from services.session_service import session_service
from core.logging import performance_logger, security_logger

router = APIRouter(prefix="/api/v1/ws", tags=["websocket"])

# 存储活跃的WebSocket连接
active_connections: Dict[str, WebSocket] = {}
session_connections: Dict[str, Set[str]] = {}  # session_id -> set of connection_ids


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_connections: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, session_id: str = None):
        """接受WebSocket连接"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        
        if session_id:
            if session_id not in self.session_connections:
                self.session_connections[session_id] = set()
            self.session_connections[session_id].add(connection_id)
        
        performance_logger.info(
            f"WebSocket connected: {connection_id}",
            extra={"connection_id": connection_id, "session_id": session_id}
        )
    
    def disconnect(self, connection_id: str, session_id: str = None):
        """断开WebSocket连接"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].discard(connection_id)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]
        
        performance_logger.info(
            f"WebSocket disconnected: {connection_id}",
            extra={"connection_id": connection_id, "session_id": session_id}
        )
    
    async def send_personal_message(self, message: str, connection_id: str):
        """发送个人消息"""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                performance_logger.error(f"Failed to send message to {connection_id}: {e}")
                self.disconnect(connection_id)
    
    async def send_session_message(self, message: str, session_id: str):
        """发送会话消息给所有连接"""
        if session_id in self.session_connections:
            disconnected_connections = []
            for connection_id in self.session_connections[session_id].copy():
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    try:
                        await websocket.send_text(message)
                    except Exception as e:
                        performance_logger.error(f"Failed to send session message to {connection_id}: {e}")
                        disconnected_connections.append(connection_id)
            
            # 清理断开的连接
            for connection_id in disconnected_connections:
                self.disconnect(connection_id, session_id)
    
    async def broadcast(self, message: str):
        """广播消息给所有连接"""
        disconnected_connections = []
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message)
            except Exception as e:
                performance_logger.error(f"Failed to broadcast to {connection_id}: {e}")
                disconnected_connections.append(connection_id)
        
        # 清理断开的连接
        for connection_id in disconnected_connections:
            self.disconnect(connection_id)


manager = ConnectionManager()


@router.websocket("/connect")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str = Query(None, description="会话ID"),
    connection_id: str = Query(..., description="连接ID")
):
    """WebSocket连接端点"""
    await manager.connect(websocket, connection_id, session_id)
    
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "heartbeat":
                    # 处理心跳消息
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat_response",
                        "timestamp": message.get("timestamp")
                    }))
                    
                    # 更新会话访问时间
                    if session_id:
                        await session_service.extend_session(session_id)
                
                elif message_type == "ping":
                    # 处理ping消息
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp")
                    }))
                
                elif message_type == "session_update":
                    # 处理会话更新消息
                    if session_id:
                        await session_service.extend_session(session_id)
                        
                        # 广播给同一会话的其他连接
                        await manager.send_session_message(
                            json.dumps({
                                "type": "session_updated",
                                "session_id": session_id,
                                "timestamp": message.get("timestamp")
                            }),
                            session_id
                        )
                
                else:
                    # 处理其他类型的消息
                    performance_logger.info(
                        f"Received message: {message_type}",
                        extra={
                            "connection_id": connection_id,
                            "session_id": session_id,
                            "message_type": message_type
                        }
                    )
            
            except json.JSONDecodeError:
                # 处理非JSON消息
                performance_logger.warning(
                    f"Received non-JSON message: {data[:100]}",
                    extra={"connection_id": connection_id, "session_id": session_id}
                )
            
            except Exception as e:
                performance_logger.error(
                    f"Error processing message: {e}",
                    extra={"connection_id": connection_id, "session_id": session_id}
                )
    
    except WebSocketDisconnect:
        # 处理WebSocket断开连接
        manager.disconnect(connection_id, session_id)
        
        # 如果有会话ID，标记会话为已断开
        if session_id:
            try:
                await session_service.cleanup_session_on_disconnect(session_id)
                
                # 通知同一会话的其他连接
                await manager.send_session_message(
                    json.dumps({
                        "type": "user_disconnected",
                        "session_id": session_id,
                        "connection_id": connection_id
                    }),
                    session_id
                )
                
                security_logger.info(
                    f"Session marked as disconnected: {session_id}",
                    extra={"session_id": session_id, "connection_id": connection_id}
                )
                
            except Exception as e:
                security_logger.error(
                    f"Failed to cleanup session on disconnect: {e}",
                    extra={"session_id": session_id, "connection_id": connection_id}
                )
    
    except Exception as e:
        # 处理其他异常
        security_logger.error(
            f"WebSocket error: {e}",
            extra={"connection_id": connection_id, "session_id": session_id}
        )
        manager.disconnect(connection_id, session_id)


@router.get("/connections")
async def get_active_connections():
    """获取活跃连接信息"""
    return JSONResponse(content={
        "success": True,
        "data": {
            "total_connections": len(manager.active_connections),
            "session_connections": {
                session_id: len(connections) 
                for session_id, connections in manager.session_connections.items()
            }
        }
    })


@router.post("/broadcast")
async def broadcast_message(message: dict):
    """广播消息给所有连接"""
    try:
        await manager.broadcast(json.dumps(message))
        return JSONResponse(content={
            "success": True,
            "message": "Message broadcasted successfully"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )


@router.post("/session/{session_id}/message")
async def send_session_message(session_id: str, message: dict):
    """发送消息给指定会话的所有连接"""
    try:
        await manager.send_session_message(json.dumps(message), session_id)
        return JSONResponse(content={
            "success": True,
            "message": f"Message sent to session {session_id}"
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )