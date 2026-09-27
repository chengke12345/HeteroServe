首先下载模型到本地的模型仓库 /opt/models/

```bash
modelscope download --model Qwen/Qwen3-4B \
  --local_dir /opt/models/Qwen3-4B
```

然后对 Qwen3-4B 模型进行单卡启动
启动脚本，详见[EXP0-Qwen3-4B_launch](/docs/03-exp0-Qwen3-4B_smoke_test.md) 其中关键的启动参数, 如下

| 参数                            | 作用          | 说明                               |
| ----------------------------- | ----------- | -------------------------------- |
| CUDA_VISIBLE_DEVICES=0        | 只启用 0 号 GPU | 单卡启动                             |
| --dtype float 16              | 设置启动数据格式    | 模型数据格式默认BP16，vLLM将模型以FP16格式加载到内存 |
| --gpu-memory-utilization 0.85 | 显存利用率       | gpu 显存利用率上限设置为 0.85              |
| --max-model-len 4096          | 模型上下文       | 模型最大上下文长度为 4096 token            |
| --served-model-name qwen3-4b  | 模型在系统中使用的名字 | 可能出现同时加载多个模型的情况，定位模型就使用模型名字      |
| --host 0.0.0.0                | 服务监听所有网络接口。 | 服务能从localhost外的其他设备访问。           |
| --port 8000                   | 端口号         | 请求模型服务的端口号。                      |

# vLLM 0.21.0 启动

Qwen3-4B 在vLLM 0.21.0中的启动日志，详见 [exp0-Qwen3-4B_launch_0_21_0.log](/logs%20&%20reports/03-EXP0-smoke_test/exp0-Qwen3-4B_launch_0_21_0.log)
在启动日志里有几个关键信息。

![](/docs/assets/EXP0_assets/Pasted%20image%2020260620005839.png)

Fragment 1: 调用后端算子 backend attention的时候，FA2 只支持 CC, Compute Compatibility >= 8.0, 即 sm ≥ 80 的硬件。 根据默认 Fallback 原则，从潜在 backends 的选项 `FlashInfer`, `Triton_atten`, `Flex_attention` 中，系统选择使用`FlashInfer`.

Fragment 2: 加载模型权重的时候，总共用了 6.56s。

![](/docs/assets/EXP0_assets/Pasted%20image%2020260620011058.png)

Fragment 3:  vLLM 除了使用 backend attention 之外，也使用其他算子。这些算子大多使用 AOT 编译模式，比如 QKV/O 投影、MLP 的 GEMM、RMSNorm、residual、RoPE 这些，以及它们之间的图结构融合。将这些 AOT 编译的算子二进制代码，可以直接放在缓存里，下一次启动需要调用的时候，可以直接 load，而不需要重复编译。编译的过程只发生在首次启动 vLLM 的时候。

Fragment 4: 现在可以使用的 KV Cache 缓存是 8.41 GB。

Fragment 5: 当前设置的显存利用率是 85%， 相当于 CUDA Graph 填充的 78.12%。为了维持相同有效 KV Cache 的大小。这里将显存利用率提高到 91.88%。

Fragment 6: KV Cache 的大小可以缓存 61216 个 token。如果每个 request 都按现在最大的 4096个 token 塞满。那系统现在可以同时并发处理 14.95个这样的请求。

FlashInfer 采用的是 JIT 的编译模式。所以，使用 FlashInfer 时，首先要将FlashInfer 的 kernel 动态编译成当下的硬件版本。
有了上面 fragment 1 和这里最后一行，`Warming up FlashInfer attention`. 就说明 FlashInfer 调用成功。FlashInfer 的 JIT 模式，能够为我们的硬件平台 sm_75 编译出正确的可执行版本。

![](/docs/assets/EXP0_assets/Pasted%20image%2020260620014930.png)

Fragment 7: vLLM 系统中有一些算子可能会调用 Triton JIT 的模式。如果推理过程中有算子调用Triton JIT，那么会以警告的方式记录下来。

Fragment 8: vLLM 服务器启动的地址和端口为 0.0.0.0:8000

Fragment 9: 系统为我们提供的访问路由。

# vLLM 0.8.5.post1 启动

在 vLLM 0.8.5.post1 里启动 Qwen3-4B 的启动日志，详见 [exp0-Qwen3-4B_launch_0_8_5.log](/logs%20&%20reports/03-EXP0-smoke_test/exp0-Qwen3-4B_launch_0_8_5.log)
其中值得关注的如下：

![](/docs/assets/EXP0_assets/Pasted%20image%2020260620032648.png)

Fragment 1: vLLM 的版本号为 0.8.5.post1. 
Fragment 2: 将模型的数据格式由 BF16 转换为 FP16 再加载到显存中
Fragment 3: vLLM 0.8.5.post1 中的 v1 engine 的最低要求是 Compute Compatibility CC 8.0, 即要求 sm ≥ 80 的硬件。所以，Fallback到 v0，使用 v0 引擎。
Fragment 4:  FA2 后端算子不能用于 Volta 和 Turing 架构。只能退回使用 xFormers。

# 0.8.5.post1 .VS. 0.21.0

旧版本的 vLLM 是 v0 和 v1 两个引擎并存的状态。默认走 v1， v1 走不通就退回到 v0. v0中的后端算子，默认首选 FA2，由于 FA2 不支持 sm_75. 所以后端算子退回到 xFormers。这是启动0.8.5.post1 版本时，vLLM 选择执行路径的完整路由。

新版本的 vLLM 彻底丢弃了 v0 引擎，只能使用 v1 引擎，这使得新的框架下，我们无法使用xFormers了，取而代之，我们只能在 v1 中从 FA2 退回到 FlashInfer。

结论：
<u>vLLM 0.8.5.post1 使用 v0 引擎，后端算子使用 xFormers</u>
<u>vLLM 0.21.0 使用 v1 引擎，后端算子使用 FlashInfer.</u>

# Trouble Shooting

第一次推理的时候，在 0.21.0 版本中遇到了如下错误
![](/docs/assets/EXP0_assets/Pasted%20image%2020260620101953.png)

原因是因为 vLLM v0.21.0 的 uvicorn, prometheus_fastapi_instrumentator, starlette 发生了版本错配。这个错误在 vLLM Github 仓库中 `issue #45597`，目前 open、无 assignee、无 PR、**没有合入的修复**。
我们做了 Patch 补丁解决了这个问题。
详细的错误日志，参考 [exp0-Qwen3-4B-Error.log](/logs%20&%20reports/03-EXP0-smoke_test/exp0-Qwen3-4B-Error.log)
打完补丁 Patch 之后，就可以正常进行测试访问了。

# 终端测试 与 流式测试

vLLM 服务启动起来以后。在另一个终端下：

首先进行单个访问测试。测试脚本，参见 [04-exp0-Qwen3-4B_single_test.sh](/scripts/04-exp0-Qwen3-4B_single_test.sh), 
测试结果正常， 产生的输出参见  [exp0-Qwen3-4B_single_test.log](/logs%20&%20reports/03-EXP0-smoke_test/exp0-Qwen3-4B_single_test.log)

然后进行流式测试，流式测试的脚本，参见  [05-exp0-Qwen3-4B_stream_test.sh](/scripts/05-exp0-Qwen3-4B_stream_test.sh)
测试结果正常，产生的输出参见  [exp0-Qwen3-4B_stream_test.log](/logs%20&%20reports/03-EXP0-smoke_test/exp0-Qwen3-4B_stream_test.log)

# 结论

vLLM 能够正常部署 Qwen3-4B 大模型。vLLM 启动符合预期，curl 返回正确 JSON。流式响应每个Token 立即返回。