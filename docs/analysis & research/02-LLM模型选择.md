## 1. 主模型选型：Qwen3-32B-AWQ

| 维度              | 评估                                              |
| --------------- | ----------------------------------------------- |
| 参数量             | 32.8B                                           |
| FP16 显存         | ~66GB（4 卡 88GB 够，3 卡 66GB 不够）                   |
| AWQ INT4 显存     | ~18GB（无论 3 卡 / 4 卡都富裕）                          |
| 原生上下文           | 32K（YaRN 可扩到 128K）                              |
| 架构特色            | GQA（64 Q heads + 8 KV heads）、thinking mode、工具调用 |
| Attention heads | 64（不被 3 整除，被 4 整除）                              |
| vLLM 支持         | 原生（vLLM ≥ 0.8）                                  |
| 备注              | ⭐⭐⭐⭐⭐ 当下主流基准模型                                  |

## 2. 为什么不选 FP16 / 其他模型

- Qwen3-32B 是完全版模型，参数权重占用显存 66GB，3 x 2080ti 加起来刚好 66GB， 装载模型之后，没有空间做 KV Cache 以及其他一些显存必要开销。这个方案不可行。
- Qwen3-14B 支持 FP16，显存足够，但是模型“含金量”低于 32B
- AWQ 32B 是消费级硬件能跑的“最大模型”甜点。

## 3. 量化为什么 AWQ 而非 GPTQ

主线模型选择 Qwen-32B-AWQ, 主线用 AWQ，走 Marlin kernel。

AWQ 是 4bit 权重量化，把 32B 模型的权重显存从 FP16 ～66GB 压缩到 ～ 18GB-20GB。这是它能在 66GB 三卡GPU系统上运行的前提，显存容量富足。其次，AWQ在Turing架构上能做计算。 Marlin kernel 可以加载 AWQ (以及FP8) 量化权重，在计算时反量化到 FP16 / BP16，这条路在 sm_75 上(Turing+) 可行。

AWQ 是激活感知量化，保留重要的通道精度，质量通常优于GPTQ。并且，AWQ 在 vLLM 中有 Marlin kernel 优化，推理速度快。

重要判断：AWQ 在 Turing 上运行完全没问题。Turing架构真正面临的挑战，在 attention 层，如何选择合适的 attention backend 后端算子是关键。

## 4. 对照组模型

除了主线模型选择 Qwen3-32B-AWQ之外，我们也对照了其他模型在同一个平台上的部署和测试。根据项目的目标，每个模型扮演的角色和作用各不相同。下面就是在部署主线模型上线过程中，我们考虑和对照的一些模型，以及它们的作用。

- Qwen3-4B: 在硬件环境测试正常，软件环境搭建完成时，用这个较小的模型，进行单卡冒烟测试，smoke test. 验证整条链路，vLLM 启动 --> API相应。冒烟测试 smoke test，详见[Qwen3-4B smoke test](/docs/03-exp0-Qwen3-4B_smoke_test.md).
- Qwen3-14B FP16: TP=2 与 Qwen3-32B-GPTQ: pp=3. 三个模型的对比分析，详见[Three-Models-Comparison](/docs/05-exp2-Three-Models-Comparison.md) 
- Qwen3.6-27B-AWQ: 我们原方案默认主线上线模型 Qwen3-32B-AWQ(dense 全注意力)，还有一个竞争的模型方案，Qwen3.6-27B-AWQ(GDN混合)

#### Qwen3-32B-AWQ(dense) VS Qwen3.6-27B-AWQ(GDN混合)

| 维度         | Qwen3-32B-AWQ（dense）                                | Qwen3.6-27B-AWQ（GDN 混合）                    |
| ---------- | --------------------------------------------------- | ------------------------------------------ |
| 注意力        | 纯全注意力（head_dim=128）                                 | 全注意力 + GDN 线性注意力                           |
| sm_75 解锁路径 | 只需全注意力 backend（FlashInfer 路径，或者fallback 到 xFormers） | 需 FlashInfer + **FlashQLA SM75 GDN patch** |
| Turing 实证  | xFormers FA2无效，CutlassF 可以                          | **已完整验证**                                  |
| 落地复杂度      | 低（若全注意力路径可用）                                        | 中（需打 GDN patch）                            |

两个模型走**不同的 attention 解锁路径**。dense 的 32B 不需要 FlashQLA（它没有 GDN 层），只需要全注意力层在 sm_75 上有可用 backend；FA2/FA3 在 Turing上失效，FlashInfer 官方声称支持 sm_75, 但是实际需要工程实践确认。xFormers中有两个op, FA2 和 cutlass，需要实践能否支持 sm_75。

主线模型决策方式：
决策方式：分别冒烟两条路，只看"能不能起 + 落到哪个 backend"，用数据决定主线模型。
决策规则：dense 能起 → 主线保留 Qwen3-32B-AWQ；dense 起不来而 GDN 能起 → 主线切 Qwen3.6-27B-AWQ。

结论：attention backend，FA2/ FA3 不支持。FlashInfer 对 sm_75 支持，  xFormers，在 FlashAttention op (FA2/FA3) 上，硬件要求 sm ≥ 80。但是 cutlass op 支持 sm_70/sm_75, 但是代价是比 FA 慢。我们选择 Qwen3-32B-AWQ 作为主线模型上线。

## 未来计划

- Qwen3.6-27B-AWQ, TP=2，采用 dual-2080ti GPU + NvLink。打GDN patch 之后，推理速度应该会有质的飞跃。这种部署方案，未来会实测。
- 项目后期，我们会探索，再加一张 2080ti, 4 x 2080ti, 采用 TP=4，模型采用Qwen3-32B FP16 完整版。验证工程可行性与实际运行效率。
