## 1. 多GPU并行部署

vLLM支持的多GPU并行部署策略，主要有两种：

<u><b>张量并行(Tensor Parallelism), TP</b></u>**: 把每一层内部的权重矩阵按列/行切到多张卡，每张卡算一部分，然后每层都要做一次 AllReduce 把部分结果合起来。

<u><b>流水线并行(Pipeline Parallelism), PP</b></u>: 把整个模型的层按深度切成几段，每张卡负责连续的若干层，数据像流水线一样从第一段流到最后一段，**只在段与段的边界传一次 activation**。

>两者的通信特征完全不同，这是选型的关键：
>- TP 的 AllReduce 是**每层都发生、对带宽和延迟极其敏感**的高频通信。它几乎必须依赖 NVLink（GPU 间高带宽直连）才能不被通信拖死。
>- PP 的 activation 传递是**每段边界才发生一次、数据量小**的低频通信，普通 PCIe 就能扛。

## 2. 关键约束

本项目是 3 x 2080ti，vLLM 要求 `num_attention_heads % tensor_parallel_size == 0`。

| 模型          | Q heads | TP=2 | TP=3 | TP=4 |
| ----------- | ------- | ---- | ---- | ---- |
| Qwen3-32B   | 64      | ✅    | ❌    | ✅    |
| Qwen3-14B   | 40      | ✅    | ❌    | ✅    |
| Qwen3-8B    | 32      | ✅    | ❌    | ✅    |
| Llama-3-70B | 64      | ✅    | ❌    | ✅    |

**没有任何主流模型的 attention heads 能被 3 整除**，所以 3 卡场景下只有 PP=3 可行。

## 3. PP=3

**head 整除约束**：Qwen3-32B（dense）的 attention query head 数是 64。TP=N 要求把 head 数均分到 N 张卡，64 不能被 3 整除（64/3≈21.3），切不开。PP 按"层"切（如 64 层切成 22/21/21），不受 head 整除限制。

**无 NVLink 的通信瓶颈**：当前**没有 NVLink**。无 NVLink 时 TP 的 AllReduce 只能走 PCIe，主板上的三槽是非对称的 x8/x8/x4，第三张卡还挂在 PCH 上跨 DMI——TP 在这种拓扑上会被通信严重拖累。PP 只传 activation，受这套拓扑影响很小。

vLLM 官方文档明确：**"无 NVLink 优先 PP"**

**代价**：PP 有 pipeline bubble，小 batch 延迟略高于 TP，但 continuous batching 在高并发下能填满流水线。

## 4. 未来计划

这些约束在一下条件，都会发生变化。我们未来计划做以下尝试
- **TP=2 + NVLink**：两张 2080ti x 8 卡走 NVLink 做 TP=2，第三卡跑独立服务。Qwen3 KV head 数能被 2 整除、NVLink 在 decode 阶段 memory-bound 场景下实际收益。
- **TP=4**：项目未来会采用 ASUS X99-E-WS 主板，引入第四张2080ti。4 张GPU插入 4 个 PCIe * 16 插槽，4卡对称拓。TP = 4进行 AllReduce 的带宽瓶颈量化。
- **TP=4**: 。在上面的基础上，引入两个 NvLink, 将 4 张 2080ti 分成 2 个双卡组，对比 TP = 4 下的 AllReduce 性能表现。 

