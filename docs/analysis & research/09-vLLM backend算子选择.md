# 1. vLLM官方内置的 attention 算子

注意力计算需要专门的 GPU kernel。这些 kernel 是针对特定 compute capability 编译的——为 sm_80（Ampere）编译的 kernel，在 sm_75（Turing）上不存在对应实现。vLLM 内置多个 attention backend，启动时会自动挑第一个"与你的模型 + 硬件兼容"的；**若一个都不兼容，它不会降速运行，而是直接报错并列出每个 backend 的不兼容原因**。

attention 具有正式后端的抽象算子。它是可插拔，并且对第三方开放，关于 attention backend 的讨论 详见 [06-vLLM attention backend](/docs/analysis%20&%20research/06-vLLM%20attention%20backend.md)

vLLM 中内置的 attention backend 有 `FLASH_ATTN`、`FLASHINFER`、`triton`、 `XFORMERS` 
- `FLASH_ATTN`（FlashAttention v2）：要求 ≥ sm_80，Turing 出局。
- `FLASHINFER` / `TRITON`：对部分模型缺少可用的计算路径。需要工程验证。
- `XFORMERS`：两个op, FA2 op / cutlass op. FA2 路径在 Turing 不工作, cutlass支持sm_75。
xFomers 的讨论，详见 [07-xFormers](/docs/analysis%20&%20research/07-xFormers.md)

# 2. Flash-Attention-Turing

除了 vLLM 内置的后端算子之外，社区还提供了一个版本的 attention 算子 ssiu/flash-attention-turing. 这条线已经被上游"收编"，已经是官方认可的 Turing 路线了。它在 Turing 上支持 FlashAttention 的核心功能子集。

FlashAttention官方 Dao-AILab 仓库在 README中 指向了这个第三方实现，作为 Turing 用户的推荐去处，它并没有被 merge 进官方代码库，但算是“官方背书的外部项目”。

vLLM 官方还没有集成这个库。官方也没有可用的 sm_75 的 FA backend。目前，kernel 已被官方(FlashAttention的官方)背书且独立验证，但是还无人集成进vLLM。ssiu 在仓库 issue 中表示，自己实现的 flash-attention-turing 算子在 T4 上比  xformers Memory-Efficient Attention 快约 2 倍。待工程中验证可行性与性能表现。

# 3. FlashQLA / FlashQLA-SM70-SM75 

FlashQLA 是 Qwen 推出的官方算子库，全称叫 Flash Qwen Linear Attention. 
Flash Attention 优化的是标准 softmax attention, $O(n^2)$. 而 FlashQLA 是基于TileLang的线性注意力机制，优化对象是 GDN(Gated Delta Netword) chunked prefill 的前向和反向--GDN是Qwen3-Next 那类混合架构里的线性注意力分支，用递归状态代替softmax的二次复杂度。

对本项目而言，Qwen官方的 FlashQLA 不适配。
- 硬件门槛：FlashQLA 官方要求 sm_90以上，CUDA 12.8+， Pytorch 2.8+. Hopper架构起步，和 Turing sm_75差了三代。
- 模型不匹配：Qwen3-32B 是纯 softmax attention(GQA), 没有 GDN 层。即使在 H100 上，FlashQLA 对这个模型也无事可做，它只能服务于 Qwen3-Next 系混合线性注意力模型。

社区项目 weicj/2080Ti-LLM-Toolbox/FlashQLA-SM70-SM75, 提供了一个支持 sm_70 和 sm_75的第三方移植。作者声明项目可行，并且推理速度可以达到惊人的 101 token/s，目前无第二人复现。

方案采取双卡 2080ti + NVLink, 模型切换至Qwen3.6-27B，它是 64 层 Gated DeltaNet + Gated Attention 混合架构，每 4 个子层中 3 个用 GDN 线性注意力，所以这个算子在这个模型上才有用武之地。vLLM 采用最新的0.21.0。本项目采用的 vLLM 0.8.5.post1 没有 GDN/混合注意力机制支持。

该项目的可行性，性能，支持稳定性目前都只是个人验证。具体可行度和性能，不是已知结论，待工程实践验证。这个算子的验证过程，不是本项目基于 PP=3方案的升级，而是一个并行策略，模型，运行时全部不同的独立方案。

本项目在后期，会将该方案，作为 side-project，进行部署，验证其可行性和性能表现。
两个独立方案对比，探索 2080ti Turing sm_75架构下，评估不同方案的表现。

# 4.  算子选择方案

本项目中，以上提及的算子都会逐一验证，以做出最佳的 attention backend 选择。工程实践中，我们将按顺序，对算子逐一做如下探索：

- 主线模型 Qwen3-32B-AWQ 采用默认的官方 FA 算子 `flash-atten`, 测试它是否支持sm_75 算力版本。
- 如果默认FA失效，attention backend 会 fallback 到 Flashinfer / triton，这两个算子理论上对sm_75的支持，不稳定，需要工程实践过程验证是否有可用的 kernel 版本。
- 如果前两者都失效，attention backend 就会 fallback 到 xFormers. xFormers的 FA2 op 同样要求 sm ≥ 80. 需要验证是否最终fallback到了cutlass，cutlass是否稳定支持sm_75, 以及使用该算子下的推理效率
- 对 ssiu/flash-attention-turing 算子进行独立编译，接入attention backend 进行替换。验证工程可行性和性能表现。
- 更换整体方案，双 2080ti + NvLink, vLLM 0.21.0, 在 Qwen3-27B-AWQ 上用 QLA-SM70-SM75 算子替换 attention backend. 验证工程可行性和性能表现。