# HeteroServe 迭代路线图

---
# 迭代 1：投机解码（Speculative Decoding / MTP）

「**原理**」：用一个小 draft 模型（或模型自带的 MTP 头）一次猜测多个 token，再由大模型一次 forward 并行验证，接受正确前缀。decode 阶段大模型的 forward 次数减少，吞吐提升。

「**价值**」：decode 是 LLM 推理延迟的主要来源，投机解码是工业界标配的加速手段，社区在 sm_75 上已验证 MTP K=3 有效（如 decode 从 32→54 tok/s 量级）。

**落地步骤**：

>- 主线模型已选定（bake-off）。确认其是否自带 MTP 头（Qwen3.6 系列有），或选一个同 tokenizer 的小模型作 draft。
>- vLLM 启动加投机解码参数（具体 flag 以版本为准）：
>```
>vllm serve <主线模型> \  
>	--speculative-config '{"method":"<mtp 或 draft>","num_speculative_tokens":3}' \  
>	--pipeline-parallel-size 3 ...
>```
>- 对比开启前后 TPOT 与吞吐，记录"接受率（acceptance rate）"——这是投机解码效果的核心指标。
>- 产出对比数据。分析接受率与决定加速比之间的决定关系。

「**重点**」： 接受率与 draft 质量、温度、领域分布的关系；验证机制不改变输出分布，投机解码不改变输出分布，是工业界标配的加速手段。

---
# 迭代 2：SM75 attention 深化（FlashQLA 性能优化）

「**原理**」：HeteroServe 项目第一阶段，主线是 "让 attention 在 sm_75 跑通" 。本迭代转向性能深化——分析 FlashQLA 在 Turing 上的 kernel 效率，尝试融合 ragged GDN prefill kernel、优化 shared memory 使用(Turing 每 SM 仅 64KB，是新模型大 head_dim 的硬约束)。

「**价值**」：这是一个硬核、且稀缺的方向，是 kernel 层改动。能把 FlashQLA 优化出可量化的提升，是一个价值极高的探索。

**落地步骤**：

>- profile 现有 SM75 attention 路径（用 nsight-compute 看 kernel 占用、shared memory、occupancy）。
>-  对照社区 patch 的实现，定位瓶颈（多半在 shared memory 压力或 ragged batch 拆分开销）。
>- 尝试优化并 benchmark，提 PR 回社区仓库。

**重点**：Turing 64KB shared memory 上限如何限制大 head_dim 模型.ragged/packed batch 在 attention kernel 里的处理。

---

# 迭代 3：LMCache 分布式 KV 缓存

「**原理**」：把 KV cache 外置到独立缓存层（CPU 内存/磁盘/远端），跨请求、跨会话复用前缀 KV，减少重复 prefill。

「**价值**」：RAG 和多轮对话场景下，相同前缀（system prompt、检索文档）反复出现，复用 KV 能大幅降 TTFT。

**落地步骤**：

>-  集成 LMCache 到 vLLM（按其文档）。
>-  设计复用场景：固定 system prompt + 变化 query 的多轮对话。
>- 对比有无 LMCache 的 TTFT 与 prefix-cache 命中率。

「**重点**」：KV 复用的粒度(block 级)外置 KV 的带宽/延迟权衡(CPU 内存 vs 本地 NVMe vs 远端)。

---

# 迭代 4：PD 分离部署（Prefill/Decode Disaggregation）

「**原理**」：prefill (计算密集、一次性) 和 decode (访存密集、逐 token) 特征不同。把它们分到不同卡组，各自优化资源配置，避免互相干扰（prefill 的长任务阻塞 decode 的低延迟需求）。

「**价值**」：这是推理优化的前沿方向（DeepSeek、Mooncake 等都在做），结合 x8/x8/x4 拓扑做亲和性调度，贴合硬件。可用备用 Z270-A 主板扩展卡组。

**落地步骤**：

>- 用 vLLM 的 disaggregated prefilling 能力（或 Mooncake 集成）。
>- 分配：prefill 实例放算力强的卡组，decode 实例放另一组，KV 通过传输层交接。
>- 对比 PD 分离前后的 TTFT/TPOT 与资源利用率。

「**重点**」：为什么 prefill 和 decode 该分离（资源特征 + SLO 隔离）；KV 在两组间传输的开销与拓扑亲和。

---
# 迭代 5：多引擎横向对比

「**原理**」：同一模型同一硬件，对比 vLLM / SGLang / llama.cpp / TensorRT-LLM 的吞吐、延迟、显存、易用性。

「**价值**」：这几个框架是现在最主流的推理框架。每个框架各有其长处，短板，最佳适用场景。通过引擎对比，可以根据应用场景，选择最合适的推理框架。

**落地步骤**：

>- llama.cpp 作 sanity 基线（稳但慢，GGUF 量化），vLLM 作主力，SGLang 作研究性对照（RadixAttention 前缀复用）。
>- 固定同一组 prompt 与硬件，跑同一压测。
>- 产出对比表（引擎 × {吞吐, TTFT, TPOT, 显存, sm_75 兼容性, 易用性}）。

「**重点**」：不同引擎的核心差异（vLLM 的 PagedAttention、SGLang 的 RadixAttention、llama.cpp 的 CPU/GPU 混合）。

---

# 迭代 6+：前沿探索

K8s 编排多实例、新量化方案（如更激进的 2bit）、MoE 模型部署、Long Context 优化、成本优化(动态扩缩容) 等。