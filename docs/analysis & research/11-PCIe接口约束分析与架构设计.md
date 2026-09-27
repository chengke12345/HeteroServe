# 1. PCIe接口分析 

项目使用的主板是 华硕 ASUS Prime Z270-A， 主板上有三个 PCIe X 16 插槽。根据ASUS官方给出的主板参数来看, Prime Z270-A 的三个物理插槽信息如下：

| 接口       | 插槽     | 协议       | 宽度  | 连接    |
| -------- | ------ | -------- | --- | ----- |
| PCIEX6_1 | Slot 1 | PCIe 3.0 | x16 | CPU直出 |
| PCIEX6_2 | Slot 2 | PCIe 3.0 | x8  | CPU直出 |
| PCIEX6_3 | Slot 3 | PCIe 2.0 | x4  | PCH   |

我们通过BIOS可以看到主板上三个 slot 的状态，3个GPU。

![image](/docs/analysis%20&%20research/assets-bios/3094311c3b805a63f3633d8e128ca953.png)

slot 1, slot 2 是通过 CPU 直连的 PCIe lanes 以 x8 的方式工作，两个 slot 拆分了 CPU 的 PCIe lanes x16 的通道。slot 3 是以 x4 的方式工作，通过 PCH 芯片组 DMI 3.0 的方式工作。

> 虽然BIOS给出的接口信息是 x16, x8 x4。如果单GPU插入PCIe slot 1, slot 1 将独享 16 通道的 CPU 直连 lanes，那么接口宽度能达到 x16。如果是双GPU插入 PCIe slot 1, slot 2, 这两个 slot 将共享 x16 通道，以 x8x8 的方式工作，接口宽度就是 x8 x8。如果插入三GPU，那么总线宽度实际上只有 x8 x8 x4。

PCIe 实际传输数据宽度，受限于 CPU 提供的 PCIe lanes，从 i7-7700 CPU 直出的 PCIe 3.0 lanes 总数是16条。由于 Slot 1, Slot 2 都是通过 CPU PCIe lanes 直连, 所以双 GPU (使用 Slot1, Slot2)时，CPU PCIe 数据宽度会在 Slot 1, Slot 2 之间进行拆分。

Slot 3 并没有走 CPU lanes 的通道，走的是 PCH 芯片组(DMI 3.0), Slot 3 最大运行在 x4 模式下。它的最初设计意图是用于 PCIe SSD 或 RAID等非 GPU 设备。

<u><b>所以实际上3个插槽的 GPU 拉满工作的时候，PCIe 总线实际使用宽度是 x8 x8 x4 </b></u>。三个 slot 能够提供的理论带宽是：

|          |   slot 1   |   slot 2   |  slot 3   |
| -------- | :--------: | :--------: | :-------: |
| bandwith | ～7.88 GB/s | ~7.88 GB/s | ~2.0 GB/s |

所以，<u><b>GPU数据通信的瓶颈是在 slot 3</b></u>。

# 2. 接口性能分析 

- 项目主线模型采用 Pipeline Parallelism 的 GPU 并行部署方式，即 PP=3 方式部署。Slot 3 就是 PP 流水线的“最慢链路” 。但 PP 跨 stage 传输的是 activation tensor, Qwen3-32B 的 hidden_size = 5120, 每 token 的 activation = 10KB, 即便 2 GB/s 也能传输 ～200K token/s activation, 远超 decode token 吞吐。
- 真正可能受影响的是 prefill 阶段长 prompt 的 activation 传输，一次几千 token x 10KB = 几十MB 量级，但仍然毫秒级。
- PCH上行 DMI 3.0 是共享带宽，和SATA，USB，网卡都在同一条 x4 上行通道上，如果有大量 I/O 或者 网络流量就需要进一步优化。

消费级CPU的 lane 都只有16位宽度，所以 3 x PCIe x 16 的接口是理论值，实际使用过程中的数据宽度只能达到 x8 x8 x4. 服务器级别的CPU提供直连的 PCIe lanes 池要大很多，比如128 lanes，主板可以给每张 GPU 都分配 x16 的lanes。 这就是消费级和服务器平台之间的差距。

# 3. 未来计划

未来会采用 ASUS X99-E-WS 的主板，它主流支持 28 或 40 lanes 的 CPU。4 个 PCIe 3.0, 接口，上行到两个 PLX 芯片(PCIe 桥接芯片)，两两一组连接一个PLX，PLX 直连 CPU x16 通道，这样是完整满血的 32 通道。这是一个准工作站级别的方案。

加入第四张 RTX 2080ti。这样可以实现 TP = 4 的张量并行部署方式，测试 AllReduce 通信模式下，PCIe 是否成为通信瓶颈。

之后计划加入 NvLink, 将 4 张 GPU 分成2个双卡组。这时候，可以再进行 TP = 4 的张量并行部署。系统整体性能是否会产生质的飞跃。

然后可以探索，双卡之间我们采用 TP = 2， 在两个组与组之间，采取 PP = 2 的部署方式，整体上采取 TP x PP + NvLink 的部署方式。这是理论上现有消费硬件条件下的，能做出的生产级推理平台的天花板。





