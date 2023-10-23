import tornado.ioloop
import tornado.web
import tornado.websocket
import asyncio

class WebSocketClient(tornado.websocket.WebSocketClientConnection):
    async def on_message(self, message):
        # 處理接收到的消息
        print(f"收到消息: {message}")

async def main():
    # WebSocket 服務器地址
    server_url = "ws://34.106.250.143:8888/websocket"

    try:
        # 連線到 WebSocket 服務器
        client = await tornado.websocket.websocket_connect(server_url)
        print("已連線到 WebSocket Server")

        while True:
            message = await client.read_message()  # 監聽来自服務器的訊息
            if message is None:
                print("連線已關閉")
                break
            print("收到消息:", message)

    except Exception as e:
        print(f"error: {e}")

if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(main())
    tornado.ioloop.IOLoop.current().start()