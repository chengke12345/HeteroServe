Gradio 是一个开源 Python 库，用来把 Python 函数，机器学习模型或 LLM 快速包装成可在浏览器中使用的交互式界面。它特别适合做模型演示，内部工作和原型验证。常见应用包括，图像识别/生成演示，语音转写，RAG 问答机器人，数据处理工具，试用的模型后台。

它的优点是上手非常快，Python 代码量小，局限是它更偏向 AI 应用和数据工程的界面层。如果要做复杂的商业网站，精细的权限体系或完整的后端架构，通常需要与 FastAPI, 数据库，React 等配合。它采用的是 Apache 2.0 许可。
# Gradio 基本运行机制

在 Python 程序中，引入 Python 包之后，并不会启动任何服务。代码创建的所有界面和事件，只是界面的描述，并不会导致任何服务启动。
直到，执行 `demo.launch(server_name="xxxx", server_port=xxxx)` 这行代码的时候，Gradio 会在当前的 Python 进程中启动一个 Web 服务，并输出本地地址，通常形如 http://127.0.0.1:7860, 通过浏览器访问这个地址，就可以使用界面。

> 注意⚠️：在 Python 中执行 `demo.launch()` 这段代码的时候，它不是另外起一个独立的 web 服务进程，而是在 Python 进程中创建一个 Unicorn Web 服务器，并用一个后台线程运行它。在档前 Gradio 源码中，服务启动逻辑等价于`thread.Thread(target=server.run,daemon=True). start()` 即，新开一个线程。

```
当前 Python 进程
├─ 主线程：运行你的脚本，并保持程序不退出
└─ 后台线程：监听 7860 等端口，处理浏览器 HTTP 请求
```

所以，结束这个 Python 进程，Gradio 服务也会停止。在系统的进程列表中，我们不会看到一个普通场景下单独的类似 `gradio-server`进程。

demo.launch() 默认会阻塞主线程，主要是为了让进程可以存活，并不是说 web 服务一定要跑在主线程中，有一些少数功能需要引入额外辅助服务，比如 SSR 模式需要引入 Node.js，`share=True` 可能需要隧道程序。本地普通 demo.launch() 核心服务是在同一 Python 进程的后台线程中运行。 