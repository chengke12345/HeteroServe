算子可以理解为一个基本的三层结构：

>- 第一层：接口。抽象定义, 规定算子长什么样、输入输出契约。
>- 第二层：实现。具体逻辑,怎么把这个算子算出来，这是具体的算法描述。
>- 第三层：kernel。实现里真正下到 GPU 的 device code,可以有不同 sm_xx 的编译产物。

“算子Operator" 概念本身的结构，接口 / 实现 / Kernel，使得算子: 接口稳定，实现可替换，kernel按硬件特化。这是算子框架很经典的分层。

算子实现会在运行时根据硬件算力版本，调用匹配的 kernel 版本执行计算。但是一般我们不会为kernel 编写多份代码。而是编写一份代码, 交由 nvcc 编译成不同 sm_xx 版本的二进制代码。

kernel 在实际编译过程中，有两种不同的编译模式，AOT (ahead-of-time) 与 JIT (just-in-time)。中文也可以称为 <u><b>预编译(AOT) 与 运行时编译(JIT)</b></u>。

## 1. AOT, Ahead-Of-Time

一份 kernel 源码，编译期就把编译目标 sm 列入 gencode，用 nvcc 编译出 sm_70/75/80... 多个cubin, 往 fat library 里塞好多个版本的 kernel，运行时按卡挑一份。这样的 kernel 支持哪些sm，在编译期间就定好了。

大多数算子 kernel 都是采用的 AOT 全编译(预编译)模式，包括 Pytorch, cuBLAS, vLLM自己的`.cu`
AOT 预编译多版本的模式的优点是:

>- 运行速度快，因为都是已经编译好的二进制代码，直接调用执行就可以。
>- kernel 是否支持某 sm_xx，一目了然。看编译时 sm_xx 是否加入 gencode。

编译时除了考虑 sm_xx 版本问题外，还有其他参数需要考虑，比如数据格式(fp16/bf16), page size, sliding window 等等。它们组合起来的数目爆炸太大，不可能 AOT 把所有组合和所有 sm 版本都预编译进包里。对于有些算子，AOT 大小还能接受，而对于有一些算子，如果采用 AOT，预编译包就会大到无法接受。

JIT 编译模式就能解决这个问题。

## 2. JIT, Just-In-Time

vLLM中的 attention backend, FlashInfer 就采取JIT的编译模式。FlashInfer 的特点是，大量 kernel不是预编译成多个 sm 版本，而是运行时 JIT。

它不是提供 <u>“我有sm_75的编译版本可选”</u>， 而是<u>“等你真的需要跑这个 kernel 的时候，拿你的 head_dim/dtype/page_size等参数给我，我现场为当前这块 GPU 编译一份”。</u>

AOT 模式下查看 gencode 就可以知道算子是否支持某个 sm_xx，JIT模式下变成了运行时为某 sm_xx 现场编译一个版本能不能成功。算子三层架构，变成了 接口-->实现-->kernel(JIT)。

运行过程为: FlashInfer 首先有个准入门槛 `arch≥75`。准入检查通过之后，它会真的去编译当前参数组合的kernel。可能编译失败，也可能编译成功但使用用了 Turing 架构没有的指令，而在跑的时候挂掉。与AOT相比，失败点从 “编译期缺版本” 变成了 “运行期JIT失败”。报错形态完全不同。
#####  - 触发JIT

对于 FlashInfer 而言，是否现场编译 kernel, 编什么，取决于一组运行时确定的参数：head_dim, 数据类型(fp16/bf16), page size, 是否带 sliding window, 是否 casual 等等，再加上目标硬件的 compute compatibility。AOT 把这些组合穷举编译进包里，会让包大小爆炸。所以，FlashInfer 选择 JIT 模式，运行时拿到 “具体参数 + 当前卡sm” 这个完整上下文，现场编译出恰好匹配的一份。

##### - 首次编译，后续复用

"现场编译"并不是每次推理都重新编译一遍。第一次遇到某个参数组合时编译(这一次会有明显延迟,你能在日志里看到 nvcc/ptxas 被调起来、首个请求或 warmup 卡几秒到几十秒)。
首次编译完后缓存到磁盘中(通常在某个 cache 目录);之后同样的组合直接命中缓存,不再重编。所以是"**首次现编 + 后续复用**"。

vLLM中，FlashInfer 和 Triton 都是走的 JIT 的编译模式。