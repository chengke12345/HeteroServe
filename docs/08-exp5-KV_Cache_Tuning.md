# 1. KV Cache Tuning 测试目的

Qwen3-32B-AWQ、Qwen3-32B-GPTQ、Qwen3-14B-FP16 三个模型在不同 `max-model-len` 配置下的 KV Cache 容量和并发能力进行对比，目标是判断：

>-  KV Cache 容量是否随 `max-model-len` 改变；
>- 不同模型/量化方式对 KV 容量的影响；
>- 如何合理设置 `max-model-len` 与 `max-num-seqs`；
>- 长上下文场景下的并发瓶颈在哪里。

# 2. 关键口径说明

本实验中有两个容易混淆的指标：

| 指标                                           | 含义                                  |
| -------------------------------------------- | ----------------------------------- |
| `Available KV cache memory`                  | 单张 GPU 上可用于 KV Cache 的显存预算          |
| `GPU KV cache size` or `KV Cache Size(toks)` | 整个 vLLM engine 可服务的 active token 槽位 |
需要注意：`KV Cache Size(toks)` 不是每卡 token 容量，也不能乘以 GPU 数量, 它是整个系统可用于 KV Cache 的 KV Cache 缓存池。

例如 Qwen3-32B-AWQ 使用 `pipeline_parallel_size=3`，三张卡分别承担不同模型层。日志中 `GPU KV cache size: 135,440 tokens` 表示这个服务实例最多可容纳约 135K active tokens。每个请求 token 都会在对应 pipeline stage 上占用 KV，因此服务并发能力按 135K 计算，而不是 `135K * 3`。它表示是整个系统 KV Cache 缓存池的容量。

# 3. 实验数据汇总

测试结果数据如下：
#### Qwen3-32B-AWQ

| max-model-len | available KV <br>Cache memory/卡 | KV Cache<br>Size(toks) | GPU blocks | 可同时跑 seq 数 | 平均 max-num-seqs |
| ------------- | ------------------------------- | ---------------------- | ---------- | ---------- | --------------- |
| 1024          | 10.85 GiB                       | 135440                 | 8465@16    | 132.27 @1k | 64              |
| 2048          | 10.85 GiB                       | 135440                 | 8465@16    | 66.13 @2k  | 64              |
| 4096          | 10.85 GiB                       | 135440                 | 8465@16    | 33.07 @4k  | 64              |
| 8192          | 10.58 GiB                       | 135440                 | 8465@16    | 16.53x @8k | 64              |
| 16384         | 10.89 GiB                       | 135984                 | 8499@16    | 8.27x @16k | 64              |
| 32768         | 10.89 GiB                       | 135984                 | 8499@16    | 4.15x @32k | 64              |

#### Qwen3-14B-FP16


| max-model-len | available KV <br>Cache memory/卡 | KV Cache<br>Size(toks) | GPU blocks | 可同时跑 seq 数 | 平均 max-num-seqs |
| ------------- | ------------------------------- | ---------------------- | ---------- | ---------- | --------------- |
| 1024          | 3.81GiB                         | 49872                  | 3117@16    | 48.70x @1k | 64              |
| 2048          | 3.81GiB                         | 49872                  | 3117@16    | 24.35x @2k | 64              |
| 4096          | 3.81GiB                         | 49872                  | 3117@16    | 12.18x @4k | 64              |
| 8192          | 3.81GiB                         | 49872                  | 3117@16    | 6.09x @8k  | 64              |
| 16384         | 3.84GiB                         | 50304                  | 3144@16    | 3.07x @16k | 64              |
| 32768         | 3.84GiB                         | 50304                  | 3144@16    | 1.52x @32k | 64              |

#### Qwen3-32B-GPTQ

| max-model-len | available KV <br>Cache memory/卡 | KV Cache<br>Size(toks) | GPU blocks | 可同时跑 seq 数 | 平均 max-num-seqs |
| ------------- | ------------------------------- | ---------------------- | ---------- | ---------- | --------------- |
| 1024          | 10.89 GiB                       | 135904                 | 8494@16    | 132.72@1k  | 64              |
| 2048          | 10.89 GiB                       | 135904                 | 8494@16    | 66.36@2k   | 64              |
| 4096          | 10.89 GiB                       | 135904                 | 8494@16    | 33.18@4k   | 64              |
| 8192          | 10.89 GiB                       | 135904                 | 8494@16    | 16.59x @8k | 64              |
| 16384         | 10.89 GiB                       | 135904                 | 8494@16    | 8.29x @16k | 64              |
| 32768         | 10.89 GiB                       | 135904                 | 8494@16    | 4.15x @32k | 64              |

#### 总结

|模型|并行方式|单卡 KV 显存预算|Engine KV active tokens|16K 满长并发|
|---|---|---|---|---|
|Qwen3-32B-AWQ|PP=3, TP=1|约 10.85 GiB/卡|约 135K|约 8.27|
|Qwen3-32B-GPTQ|PP=3, TP=1|约 10.89 GiB/卡|约 136K|约 8.29|
|Qwen3-14B-FP16|TP=2, PP=1|约 3.8 GiB/卡|约 50K|约 3.07|

满长并发近似公式：

```
满长并发 ≈ engine_KV_tokens / max_model_len
实际可调度并发 ≈ min(max_num_seqs, engine_KV_tokens / 平均 active tokens per request)
active tokens = prompt tokens + 当前已生成 tokens
```

# 4. 上下文限制对并发能力的影响

在 `max-num-seqs=64` 的前提下，即已经约束最大可并行序列数为 64个。三个模型在不同上下文长度的满长请求下，并发能力如下：

|模型|1K|2K|4K|8K|16K|32K|
|---|---|---|---|---|---|---|
|Qwen3-32B-AWQ|64|64|33|16|8|4|
|Qwen3-32B-GPTQ|64|64|33|16|8|4|
|Qwen3-14B-FP16|48|24|12|6|3|1-2|

可以看到，`max-num-seqs=64` 并不代表所有上下文长度下都能跑 64 路并发。它只是调度上限，真正能否达到还取决于 KV Cache active token 容量。

# 5. 核心发现

#### 一、 `max-model-len` 不会显著改变 KV 总容量

同一模型下，KV token 容量基本稳定。改变 `max-model-len` 后，变化的是“满长度请求下的并发能力”。例如 Qwen3-32B-AWQ 的 KV 容量约 135K tokens：

```
135K / 4K  ≈ 33 路
135K / 8K  ≈ 16 路
135K / 16K ≈ 8 路
135K / 32K ≈ 4 路
```

因此，拉高 `max-model-len` 的代价是显著降低最坏情况下的并发能力。

#### 二、32B AWQ 与 GPTQ 的 KV 容量几乎一致

Qwen3-32B-AWQ 和 Qwen3-32B-GPTQ 的 engine KV 容量都在 135K 左右，差异很小。

这说明 AWQ/GPTQ 量化格式主要影响权重显存、计算 kernel、吞吐和精度，不会显著压缩 KV Cache。KV Cache 默认仍然由模型结构、KV dtype、并行方式和剩余显存决定。

### 三、14B FP16 的 KV 并发能力反而更弱

Qwen3-14B-FP16 虽然参数量小于 32B，但由于使用 FP16 权重，单卡可用 KV 显存只有约 3.8 GiB，engine KV 容量只有约 50K tokens。

因此它在长上下文下的满长并发能力明显低于 32B 量化模型：

```
14B-FP16 @ 16K: 约 3 路
32B-AWQ/GPTQ @ 16K: 约 8 路
```

这说明在显存受限环境下，“小模型 FP16”不一定比“大模型量化版”更适合长上下文高并发服务。

# 6. KV Cache 调优结论

### 一、 不应盲目把 `max-model-len` 设置到模型最大支持长度

如果业务大多数请求在 2K-4K，直接开放 32K 会导致调度器按更大的上下文窗口设计，最坏情况下并发能力被压到很低。

建议按业务类型进行分布配置：

|业务场景|推荐策略|
|---|---|
|普通对话、短问答|2K-4K|
|RAG、多轮对话|4K-8K|
|长文档分析|16K|
|极长文档/代码仓库分析|单独部署 32K 实例|

<u><b>短上下文高并发和长上下文低并发最好拆成不同服务实例</b></u>。

### 二、 `max-num-seqs` 应根据 P95 active tokens 设置


```
建议 max_num_seqs = floor(0.7 ~ 0.85 * engine_KV_tokens / P95_active_tokens)
```

保留 15%-30% headroom，用于应对：

- 输出 token 增长；
- 请求长度波动；
- prefix cache 占用；
- block 碎片；
- CUDA graph / runtime 内存波动。

### 三、32B AWQ/GPTQ 推荐配置

|目标上下文|理论满长并发|推荐 `max_num_seqs`|
|---|---|---|
|2K|约 66|48-64|
|4K|约 33|24-32|
|8K|约 16|12-16|
|16K|约 8|6-8|
|32K|约 4|3-4|

### 四、14B-FP16 推荐配置

|目标上下文|理论满长并发|推荐 `max_num_seqs`|
|---|---|---|
|1K|约 48|32-40|
|2K|约 24|16-20|
|4K|约 12|8-10|
|8K|约 6|4-5|
|16K|约 3|2|
|32K|约 1-2|1|

# 7. 最终结论

KV Cache 调优不是简单调大 `max-model-len` 或 `max_num_seqs`，而是根据业务请求的 token 长度分布，在 KV active token 容量约束下做匹配。

Qwen3-32B-AWQ， Qwen3-14B-FP16,  Qwen3-32B-GPTQ 三组模型：
- Qwen3-32B-AWQ 和 Qwen3-32B-GPTQ 的 KV 容量基本相同；
- 32B 量化模型在当前部署下拥有约 135K active token 容量；14B-FP16 只有约 50K active token 容量，长上下文并发能力更弱；
- `max_num_seqs=64` 只适合短上下文，高于 4K 后实际并发会明显受 KV Cache 限制；
- 生产部署应按 P95/P99 active tokens 配置 `max-model-len` 与 `max_num_seqs`，并为长上下文单独部署实例。

32B 模型有更高的并发性能，并且支持长上下文并发。而14B模型，在参数规模更小的情况下，可用的 KV Cache 却更少，并发性能更弱，几乎不支持长上下文并发。

基于并发性能，长上文支持性能方面的考虑，32B量化模型是更好的选择。

vLLM 框架的上下文限制 `max-model-len` 和 请求并发限制 `max-num-seqs` 更详细的讨论，参考 [vLLM上下文限制(max-model-len)与并发限制(max-num-seqs)](/docs/analysis%20&%20research/14-vLLM上下文限制(max-model-len)与并发限制(max-num-seqs).md)
