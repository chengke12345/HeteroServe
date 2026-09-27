我们使用的 GPU 设备是 RTX 2080ti, 它基于 Turing 架构， 算力版本 CC (compute compatibility)为 sm_75。硬件架构 arch 在模型运行过程中面临多方面约束。

# 1. 模型数据格式 dtype 约束

Qwen3-32B 官方主发布版本是 BF16，模型以 BF16 数据格式训练。官方也发布了Qwen3-32B-FP8. 所以，模型权重参数本身的数据格式是 BF16 和 FP8，这就要求模型推理时使用的芯片架构，要具备支持这两个数据格式的硬件电路，即 GPU 平台要支持这样的数据格式。

社区对官方发布版进行了量化，发布了社区量化版 AWQ(INT4, W4A16), GPTQ-INT4/INT8。
- AWQ：W4A16，权重 INT4 存储，计算时反量化到 FP16，activation 全程 FP16. 
- GPTQ：IN4/INT8，同样在计算时反量化到 FP16。

# 2. GPU 架构 sm_75约束

sm_75 没有 BP16 的硬件，也没有 FP8 的硬件 。Turing 的 Tensor Core 支持 FP16 / INT8 / INT4 三种数据格式 dtype。GPU arch  无法运行官方主发布版本 Qwen3-32B(BF16), 也无法运行 Qwen3-32B-FP8. 而只能运行社区量化版 AWQ 和 GPTQ。
除此之外，sm_75 还要收到 attention backend 的约束，attention backend 算子实现必须要提供sm_75的 kernel 编译版本。官方的attention backend, FA2, 就不支持，它要求 sm ≥ 80。

Turing sm_75 的约束如下：

| 约束                       | 表现                                    | 应对                                  |
| ------------------------ | ------------------------------------- | ----------------------------------- |
| 无 BF16 硬件                | 只能用 FP16                              | 启动加 `--dtype float16`               |
| 无 FlashAttention v2 官方支持 | 自动 fallback 到 Flashinfer, 或者 xformers | `VLLM_ATTENTION_BACKEND=XFORMERS`等。 |
| 无 FP8 硬件                 | FP8 量化不可用                             | 只做 FP16 / AWQ / GPTQ                |
| 计算能力 sm_75               | 部分新 kernel 需 sm_80+                   | 降级到 vLLM 兼容版本                       |

# 3. vLLM部署框架约束

vLLM 官方文档明确写出：

```
NVIDIA CUDA:
GPU: Compute Compatibility 7.5 or Higher(eg.T4,RTX20xx,A100,L4,H100,B200,etc.)
```

vLLM 官方支持的算力版本 Compute Compatibility, CC 7.5 以上的 Hardware Arch, 即 sm ≥ 75. 所以 sm_75 能够被 vLLM 框架支持。

但是，这里支持是框架本身支持，是最低准入门槛,  vLLM不保证对 sm_75 做到运行时支持。vLLM是否能够全面支持 sm_75, 还要取决 vLLM 中使用的算子是否支持 sm_75. 只有框架中用到的算子都支持 sm_75, vLLM 才能在运行时，真正支持 sm_75。

关于算子与 sm_xx 之间的适配性关系，详见 [03-算子架构与原理](/docs/analysis%20&%20research/03-算子架构与原理.md)

# 4. backend attention 约束

vLLM 中核心的部分是 attention算子，它是具有正式后端的抽象算子。attention 算子调用时，会调度到 attention backend 上执行。只有选择的 backend 的 kernel 提供了 sm_75 编译版本，attention 才算支持 sm_75.

关于 vLLM 中attention抽象算子和正式后端的讨论，详见[06-vLLM attention backend](/docs/analysis%20&%20research/06-vLLM%20attention%20backend.md) 

attention backend 是可插拔的，并且支持第三方插件，对 attention backend 的选择是 sm_75 上运行大模型的一个核心技术决策。对后端算子的选择，详见[09-vLLM backend算子选择](/docs/analysis%20&%20research/09-vLLM%20backend算子选择.md)

## 4. Turing 架构与模型适配性综合考虑

模型要能在硬件架构上正常运行，需要 模型 / 部署框架 / 硬件架构，三者同时适配。部署框架要能够支持模型的种类，硬件架构要能支持模型的数据格式，部署框架的算子要能支持硬件架构的算力版本。所以，三者相互支持适配的情况下，模型才能正常运行。

关于，模型 / 部署框架 / 硬件架构，三者适配关系的讨论， 详见 [04-模型、框架与GPU架构适配性](/docs/analysis%20&%20research/04-模型、框架与GPU架构适配性.md)
