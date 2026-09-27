vLLM中的 attention 算子是一个抽象算子，它是有 <u><b>正式后端</b></u> 的算子, 即它的算子实现对用户都是可见且可配置的，并且允许插入第三方 attention 算子实现，这些 attention 算子的实现统一称为 attention backend。`flash-atten`, `flashinfer`, `xFormers` 这些都是 attention 算子的实现。

`flash-attn` 和 `flashinfer` 这两个库本质上**就是**attention 算子（它们除了 attention kernel 几乎不干别的）。但 xFormers 不一样，它是 Meta 提供的一个 transformer 组件库，里面有各种东西。

> [!NOTE] xformers算子的含义
> vLLM attention backend 后端语境下，说 "xformers"，它不是指 transformer 组件库，而是指组件库内那个最常用的，最核心的算子，叫`xformers.ops.memory_efficient_attention` 
> 更准确的说法是，<u><b>xformers 组件的 `memory_efficient_attention` 才是跟 flash-atten, 和 flashinfer 处于同一层级的算子实现，而不是整个xformers库。</u></b>


`memory_efficient_attention` 可以认为是一个分发器(dispatcher), 它背后挂了多个具体的实现(xformers内部叫 op，operator, 算子)，运行时根据硬件，dtype，head_dim, mask 形态等条件自动挑一个。最常见的两个op是：

- <u><b>FlashAttention op（fa2/fa3)</u></b>:  xformers 直接把 Tri Dao 的 FlashAttention-2 kernel vendored 进来包了一层。最快，但约束硬：dtype 只能 fp16/bf16，head_dim 有上限和对齐要求，mask 模式受限，而且 <b>硬件要求 sm_80+(Ampere)起</b>。

- <u><b>Cutlass op</b></u>：xformers 自己用 NVIDIA CUTLASS 模板手写的一套 FMHA 实现。它更"全"——支持 fp32、更多 head_dim、任意 attention bias/mask，并且**支持 Volta/Turing（sm_70/sm_75）**。代价是比 FA2 慢，但适用面广，是 FA2 约束不满足时的兜底。

> [!NOTE] 总结
> XFromers 严格来讲不是 attention backend, 而是 Meta 的一个 Transformer 组件库。只是我们说起 attention backend 的时候，这种语境下 xFormers 被当作算子的实现，实际上它指的是Xformer 里面的 memory_efficient_attention，它才是和 flash-attent, flashinfer 一个层级 kernel算子实现。而它本身是一个指派器，会根据硬件挑选一个kernel，FA2/FA3，或者cutlass 版本实现。</font>


# xFormers 多级分发

站在 attention 的角度上看，xFormers 是一个多级分发的结构。attention是一个抽象的算子逻辑规格，当我们调用 attention 算子的时候，它需要分发/路由到一个实现上去执行, 因此要选择一个backend。`flash-atten`, `flashinfer`, `xFormers`, 都是候选。

注意，选择 backend，是由 vLLM 框架自己的指派器。当我们指定 `backend=xformers` 的时候，用户就自己指定了 backend。它实际选择的是 `memory_efficient_attention`, 它是一个算子内部的分发入口，它对标 flash-atten, flashinfer 的功能层级定位，但是内部是个挑 kernel 的 dispatcher. 

真正的 kernel实现，在 xformers 内部叫op, 有FA2/FA3(FA3 是给 Hopper sm_90写的)，以及cutlass。`memory_efficient_attention` 会选择使用哪个op。

每个 op 又有几个 cc 的编译版本支持不同 arch。FA2 要求 sm ≥ 80, 而 cutlass 支持更广泛，sm_70, sm_75 都可以支持。

所以, 所以调用 attention 算子时，首先由vLLM框架的分派器选择 attention backend。选择了 xFormers 之后，由`memory_efficient_attention` 再次选择具体的op来执行. 比如选择了cutlass，cutlass再根据我们执行硬件 arch 的cc，提供支持的编译版本，比如 sm_70, sm_75。 

# Fallback

当我们使用`memory_efficient_attention` 分发op的时候，我们最好的选择其实是 FA2，但是FA2要求 sm ≥ 80, 所以它没有支持我们硬件 arch 的 sm_75 版本。这时候，我们只能选择 cutlass，虽然它没有FA2速度快，不是最新版，但这是我们唯一的选择。这个过程在路由算子实现时，自动完成，这个自动完成算子路由退回的过程，叫做 <u><b>算子的Fallback</u></b>。

Fallback 不只是发生在 xFormers 内部。在 vLLM 框架选择 attention backend 算子实现时，也会发生。默认情况下，vLLM 为 attention 算子绑定的 backend 是 `flash-atten`，但实际上 flash-atten 的最低要求是 sm >= 80. 所以，当跑在 sm_75 的硬件上时，vLLM 启动时，attention 算子在选择路由实现时，会 Fallback 回 `flashinfer`, 如果还是不行，就继续退回到 `triton`。vLLM 有一个完整的 attention 算子 Fallback 路径，如果所有的 attention 算子实现都匹配失败，那就报错，Fallback Failure, 就是 <u><b>Fallback 失败</b></u> 。

关于xFormers 更详细的介绍，参考 https://github.com/facebookresearch/xformers