import tornado.ioloop
import tornado.web
import tornado.websocket

# WebSocket 處理程序
class WebSocketHandler(tornado.websocket.WebSocketHandler):
# 儲存所有客户端連線
    clients = set()

    def open(self):
        print("WebSocket 連線已建立")
        # 將連線添加到客户端集合
        self.clients.add(self)

    def on_message(self, message):
        print(f"收到訊息: {message}")
        # 在這裡處理接收到的訊息

        # 向所有客户端廣播
        for client in self.clients:
            client.write_message(f"{message}")

    def on_close(self):
        print("WebSocket 連線已關閉")
        # 將連線从客户端集合中移除
        self.clients.remove(self)

# 应用程序设置
app = tornado.web.Application([
    (r'/websocket', WebSocketHandler),
])

if __name__ == '__main__':
    app.listen(8888)  # 監聽在端口 8888
    print("WebSocket Server start")
    tornado.ioloop.IOLoop.current().start()