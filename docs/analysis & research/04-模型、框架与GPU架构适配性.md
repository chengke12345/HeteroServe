# 1. 框架支持compute capability

<b>Compute Capability, CC, 叫做算力版本</b>，如 7.5, 8.0, 它是 NVIDIA 定义的硬件属性，描述的是芯片的 SM 架构版本和它支持的指令集。注意：CC 不是 vLLM 框架的东西，不存在"vLLM的compatibility"，只有 "vLLM 对某个 CC 是否支持"。

sm_75, 严格说，它叫做 <u>编译目标</u>。某个算子实现在编译的时候，要指定编译目标，编译出来的二进制可执行程序，才能支持在某个硬件架构上执行。因此，编译目标和硬件算力版本CC是一一对应的关系。可以说 "某个算力版本的编译目标是 sm_xx", 比如 算力版本 7.5 对应的编译目标是 sm_75.也可以说 "sm_80 就是算子的编译目标二进制代码，是面向算力版本为 8.0 的GPU硬件"。

vLLM 框架本身来说也是一个软件，要运行在 GPU 硬件平台上，vLLM 框架本身的编译代码对硬件 arch 有下限要求，这就是 vLLM 支持的CC。说的是这个软件平台本身对硬件 arch 的要求。而框架中的算子实现，调用 kernel 执行的部分，会针对硬件 arch 编译产生可执行程序，这是算子 kernel 支持的 cc 版本。

<u>所以vLLM整体的cc声明</u> 和 <u>算子内部实际的cc覆盖</u>是两回事。vLLM的声明是编译执行vLLM这个框架软件的一个最低下限，算子内部 cc 的覆盖可以是算子自己的决策。


> [!NOTE] vLLM框架结构
> vLLM 大体上由框架软件本身和一些列的算子组成。框架软件本身负责主逻辑的运行，算子是提供功能的部件。
>- <b><u>框架本身</b></u>: 调度、内存管理（KV cache 分页/块表）、批处理（continuous batching）、请求队列、API server、并行编排（PP/TP 怎么切怎么通信）——这些是"组织和调度"的逻辑，主体是 Python，本身不怎么吃 CC 版本。
>- <b><u>算子</b></u>：真正在 GPU 上做数值计算的部件——attention、量化反量化、rotary、AllReduce 等，CUDA/SASS 编出来的，吃 CC 的就是这层。
>
>  🌟 vLLM = 调度逻辑 + 一整包算子。
>
>  vLLM 支持 sm_70" 这条门槛线，本身不是框架那层（Python 调度）提的要求——它就是替算子那层提的。框架的调度逻辑本身（Python，不编 GPU 机器码）不因 CC 不同而跑不跑得动；但 vLLM 作为一个整体软件包，对外声明的那条 CC 下限，是被它打包的算子决定的。

所以，vLLM框架声明的 cc, 是框架能够正常编译运行支持硬件 arch 的<u>最小</u> cc。本质上是替框架内部的算子实现，对硬件 arch 做初筛。只有高过这个版本，框架才会对这个硬件 arch 准入。
![image](/docs/analysis%20&%20research/assets-模型、框架与GPU架构适配性/Pasted%20image%2020260607185335.png)

但是，对于这个最低的 arch，算子内部 kernel 实现，不一定覆盖最低 cc，这是由算子自己决定的。比如vLLM声明的最低 cc 是 sm_75, 但是 GEMM 算子实现要求最低 ≥ sm_80. 意思就是sm_75框架对硬件 arch 才准入，但不是说里面的算子都覆盖 sm_75, 是否覆盖这个 arch 是由算子自己决定的。vLLM自己提供的算子实现如此，第三方算子实现的 cc 覆盖，它就更管不着了。

# 2. 算子实现覆盖 CC

算子是一个抽象的逻辑规格。算子具体的会有不同的实现。例如 vLLM 的 `Backend Attention`后端算子, 它的具体实现是可替换的。它可以有多个具体的算子实现，`FlashAttention`/ `FlashInfer`/ `Triton`/ `XFomers` , 这些都是具体对 Attention 算子的实现，是真正干活的具体组件。而 Attention (Backend Attention的简称) 算子，是一个schema，只是抽象逻辑定义。

算子的具体实现，还需要调用底层的 kernel 在 GPU 上去执行真正的计算，kernel 本身是针对硬件架构 arch 编写的。不同 kernel 会支持不同的 cc 版本，算子执行时 Runtime 也会根据不同的硬件 arch CC 调用相应的 kernel 编译版本。

因此，会出现 Attention 算子的实现 Flash Attention(FA算子) 支持 sm80, sm86, sm89 架构。而 Attention 另一个实现 xFormers 支持 sm75，sm80等。也就是说，同一个算子实现，还提供了不同的二进制编译版本。比如 FA 算子实现，一份实现代码，提供了三个编译版本 sm80, sm86, sm89。

框架要能在某个硬件 arch 上运行，框架内算子的 kernel 实现，也要能够覆盖该硬件 arch 的cc。
# 3. 模型，dtype / 量化 Kernel

模型本质上就是一堆权重文件，如何使用这些权重文件，需要的是框架，比如 HuggingFace提供的Transformer或Ollama等，它们实现了attention的算法，flash attention加速，以及其他跟使用权重文件相关的工具。

模型本身不存在 "支持的GPU型号“ 这个说法，模型就是权重 + 架构,它对硬件无知。真正决定我们能不能使用某个 GPU 的是使用的部署框架。同一份权重, 在 vLLM / SGLang / llama.cpp / TensorRT-LLM 上对硬件的要求完全不同。各框架有自己的 hardware support matrix。各框架在使用模型的时候，都有自己对模型的使用方式。

模型文件本身和GPU无关，在 repo 里就是一堆权重+config。权重以某个 dtype 存储, (BF16 / FP16/ FP8 / 或 IN4+scale这种量化打包)。
问题不在于模型是否支持某显卡，而在于这个 dtype 要跑起来，硬件 arch 支持这种数据格式。因为kernel 计算时，是把数据放到硬件上去执行，所以要求硬件必须要支持模型参数的数据格式。

比如 2080ti 的Turing 架构的 sm_75 没有 BF16 的硬件计算电路，所以 vLLM 就不为 sm_75 提供 BF16 Kernel。所以实践结论确实是：**BF16 权重在 2080Ti 上必须 `--dtype float16` 转成 FP16 跑**——而 FP16 的 Tensor Core 路径 Turing 是有的，所以 FP16 的 dtype 就可以跑
## 4. GPU 架构

Compute Capability, CC, 叫做算力版本，如 7.5，8.0。CC 是 NVIDIA 定义的硬件属性，描述的是芯片的 SM 架构版本和它支持的指令集，不是 vLLM 框架的东西，不存在"vLLM 的 Compute Compatibility"，只有"vLLM对某个CC 是否支持"。

sm75 sm80 是编译目标，sm 代表的是 stream multiprocessor 是流多处理器。更准确的说，sm_xx 代表的是，算子的编译目标。它与GPIU 架构的算力版本 CC 匹配，那么它就可以在这个设备上运行。编译的目标 sm_xx 也可以直接用来描述 GPU 芯片架构的规格。

GPU 的算力版本 CC 和 算子的编译目标 sm_xx 是一一对应的关系。比如 CC 7.5 对应的编译目标就是 sm_75, CC 8.0 对应的编译目标就是 80. 因此，可以说 "sm_80 就是算子的编译目标二进制代码，是面向算力版本为 8.0 的GPU硬件"。

vLLM 框架中的某些特性，要根据GPU架构来，因为vLLM中使用的 kernel 是针对不同的硬件架构编写的。算子实现调用 kernel 是否提供了某个 GPU 架构目标编译版本，决定了这个 feature 是否支持该硬件。

![image](/docs/analysis%20&%20research/assets-模型、框架与GPU架构适配性/Pasted%20image%2020260608124427.png)

GPU 中本身架构规格决定了它是否能支持一些数据格式.
比如 sm75 Turing 架构，支持FP16，但是没有BP16 和 FP8 硬件，所以不能做 BP16 和 FP8 的计算。也就是说这些数据格式的模型，在 Turing 架构上都得不到支持.


# 5. GPU架构适配性考虑

我们在考虑GPU和模型适配性的时候，要从三个方面考虑 「 部署框架 / GPU硬件架构 arch / 模型 dtype 」这三者之间相互适配，模型才能顺利在GPU上跑起来。

![image](/docs/analysis%20&%20research/assets-模型、框架与GPU架构适配性/Pasted%20image%2020260609064254.png)
一个模型要能跑起来，需要考虑三个因素的适配，也就是模型，硬件，部署框架。

>- ① 首先，框架本身对cc有一个最低要求的声明，框架软件要在支持的cc的arch上才能运行。每个框架有自己的 hardware support matrix，可以查看是否支持某种硬件arch。
>- ② 框架对cc的声明只是框架的准入门槛，我们还要查看框架内提供的算子实现，是否覆盖了硬件cc。如果我们要使用该算子，但是算子没有覆盖我们硬件arch的cc，那也不行。
>- ③ 部署框架本身，对模型的支持有自己的支持列表。模型必须是框架支持的模型，才能使用该框架进行模型的推理部署。
>- ④ 除了cc之外，GPU的显存还必须足够，否则无法装下权重文件。
>- ⑤ 模型本身对硬件 arch 没有要求，但是模型的参数是由数据格式的，数据格式必须是硬件arch支持的数据格式，推理的计算才能在硬件上执行。


### 附：查阅

| ✅   |     |
| --- | --- |
|     |     |

