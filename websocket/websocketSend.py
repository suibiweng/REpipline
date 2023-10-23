import asyncio
import websockets

async def send_message():
    uri = "ws://34.106.250.143:8888/websocket"  # WebSocket 服務器地址
    async with websockets.connect(uri) as websocket:
        print("已連線到 WebSocket Server")
        
        while True:
            message = input("input send message: ")
            await websocket.send(message)  # 發送消息到服务器
            print(f"send: {message}")

# 启动 WebSocket 客户端
if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(send_message())