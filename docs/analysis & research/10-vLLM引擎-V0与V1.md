# 1. 推理框架的 Engine

vLLM 中的引擎 engine，指的是 <b><u>vLLM 的推理执行核心</u></b>。
具体的，engine 指的是 vLLM 从"收到请求"到"吐出 token"这条主链路的那套核心实现，包括：

>- 调度器(scheduler): 决定哪些请求与 token 在这一步进 batch. Continuous Batching 的逻辑就在这。
>- KV Cache 管理: PagedAttention 的 block 分配、换入换出。
>- batch 的组织方式: prefill 和 decode 怎么拼进同一个 forward(V1 那套统一的 flattened batch 就是这层的设计)。
>- model runner: 怎么把 batch 喂给模型、怎么管 CUDA graph capture。
>- 进程/并行结构: API server、worker、TP/PP 怎么协同。
>- attention metadata 怎么构造——**然后**才轮到 attention backend 拿着这个 metadata 去算。

从V0 到 V1, engine 变了,上面这些几乎全变了。

从V0 到 V1, vLLM 把是把整条核心重写了一遍。V1 不是"换了套 backend 和 fallback",而是重做了调度、KV cache、batch 组织、metadata 这套底层架构,目标是更干净的 continuous batching、更低的 CPU 开销、prefill / decode 统一处理等等。backend 是这套核心调用的一个零件, 只是核心内部的一个子模块。

V0 和 V1 是两套并存的执行核心代码， `VLLM_USE_V1=0/1` 就是选用哪一套。两套核心实现共存于同一个 vLLM 包里,开关切换。

>engine = vLLM的推理执行核心整体 (调度 + KV Cache + batching + runner + metadata + ... ), V0/V1 是这套核心的两代不同实现。
>
>attention backend 是 engine 内部一个可替换的子模块。切换 engine，会使得 backend 集合不同，默认 fallback 不同。这是engine换代，导致的下游结果。
>V0 vs V1 时,变的远不止 attention 这一块——调度、KV cache 管理、CUDA graph 行为都在变。
>
>所以如果同一个 backend(比如 FlashInfer)在 V0 能跑、V1 挂了,根因**未必在 attention 适配层**,也可能是 V1 的 KV cache/metadata 喂进去的东西触发了 sm_75 上的问题。

# 2.  V0 vs V1 中的 backend

 V0 引擎和 V1 引擎，在 attention backend 上的选择是不一样的。
 - V0 的默认 fallback 路径是 `Flash-atten` --> `xFormers`
 - V1 的默认 fallback 路径是  `Flash-atten` --> `FlashInfer` -->`Triton-atten` --> `Flex_Attention`。

V0 引擎的backend算子库和 V1 引擎的算子库，是独立的，放在不同的路径下。
- V0 引擎的backend 放在 `vllm/attention/backends/` 下面，V0包含的内置backend有 `flash-atten` , `xformers`, `flashinfer`, `triton`
- V1 引擎的 backend 放在  `vllm/v1/attention/backends/`下面, V1包含的内置 backend 有 `flash-atten`,  `flashinfer`, `triton_atten`, `flex-atten`.
注意， V0 和 V1 的 backend 有重叠的部分，例如，`flashinfer`, `triton_atten`, 也有差异的部分，`flex-atten` 与 `xformers`。

<u>相同部分</u>：v0 和 v1 有各自不同的flashinfer，v0在`vllm/attention/backends/flashinfer.py`, 
V1 在 `vllm/v1/attention/backends/flashinfer.py`。两者是不同的实现。我们使用的哪个引擎，就调用的是哪个backend。
<u>不同部分</u>：xformers只存在于V0引擎，而不存在于 V1 引擎。Flex-attention 是 V1 新加入的 attention backend。

| backend        | V0  | V1       |
| -------------- | --- | -------- |
| XFORMERS       | ✅   | ❌(不存在)   |
| FLASHINFER     | ✅   | ✅        |
| TRITON         | ✅   | ✅        |
| FLEX_ATTENTION | ❌   | ✅(V1 专属) |
# 3. 指定引擎与backend

我们在启动框架的时候，需要指定使用的引擎, 也可以指定使用的 attention backend。假设我们要指定使用v0的 xFormers 后端算子

```shell
VLLM_USE_V1=0                   # 选引擎，0=V0， 1=v1
VLLM_ATTENTION_BACKEND=XFORMERS # 在当前引擎内部选 backend 
```

如果没有指定，vLLM 默认以 v1 引擎启动，如果硬件架构不满足，再 fallback 到 v0. 在不同引擎下，backend 默认的加载顺序和 fallback 路径都不一样。
如果走v1, 那么我们无法使用 xformers，如果使用v0，我们就无法fallback到 flex-atten。