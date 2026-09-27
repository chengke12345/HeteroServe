我们使用 Gradio 来进行用户侧的实时演练。关于 Gradio 的介绍，参考 [22-Gradio](/docs/analysis%20&%20research/22-Gradio.md)
Gradio Demo 中，通过 Gradio web 服务，在前端页面上，输入prompt 文本，由Gradio 再访问 后端 LLM 服务。
整个过程，我们实时监控 TTFT，TPOT，本次推理生成 tokens 总数，生成速度(tokens/s), 以及总耗时。这些数据是随着推理的进行，实时显示在 Gradio 页面上的。

Gradio Demo 前端的完整源代码，参考 [gradio-demo.py](/scripts/19-gradio_demo.py)

下面是 Gradio Demo 实机演示的截图

![](/docs/assets/gradio_assets/Pasted%20image%2020260912130135.png)

可以看到 "生产级 LLM 推理服务"。硬件条件是 3 * 2080ti 22GB。模型采用的是 Qwen3-32B-AWQ. 模型还可以选择备用模型 Qwen3-14B-FP16, 注意在当前方案中，主备模型仅有一个是在运行状态。

我们使用一个数学推理问题，让模型推理求解 $x^2+3x+2=0$ 方程的解。我们将求解推理的过程，打印在白色方框中。同时在推理的过程中，我们看到指标数据大致为

| 指标        | 数值            |
| --------- | ------------- |
| TTFT      | 166 ms        |
| TPOT      | 37.1 ms       |
| 生成 tokens | 1799个         |
| 生成速度      | 26.9 tokens/s |
| 总耗时       | 66.8 s        |
求解这个方程，大模型一共生成了 1799个 token, 首个 token 产生的延迟是 166 ms，之后的decode 阶段，平均产生每个 token 的延迟是 37.1 ms， 生成速度为 26.9 tokens/s, 解这个方程问题总共耗时 66.8s。

>注意⚠️：这里的 TTFT， TPOT 是单一推理请求的指标表现，这是站在用户请求的用户体验角度的指标。Locust 压测中的指标是在并发环境下，整体系统性能的指标表现。虽然指标都是 TTFT 和 TPOT，但是反映统计学含义是完全不同的。

HeteroServe 的实时演示视频如下

![](/docs/assets/HeteroServe-demo-app.gif)


完整详细的视频演示，参考[heteroserve-demo-app.mp4](/demo-app.mp4)

