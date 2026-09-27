# Hardware & Environment Setup

## 1. BIOS设置

系统启动后，进入BIOS, 完成如下设置

```
Advanced 标签：
  ├── PCIe Configuration
  │   └── Above 4G Decoding: Enabled       ← 多卡必开
  │   └── Re-Size BAR Support: Enabled     
  │
  ├── CPU Configuration
  │   └── Intel Hyper-Threading: Enabled
  │   └── Intel Virtualization Technology: Enabled
  │
  └── System Agent Configuration
      └── PCIe Speed: Auto (Gen3)          ← PCIe3.0

Boot 标签：
  ├── CSM (Compatibility Support Module): Disabled
  └── Secure Boot: Disabled (Linux 兼容)

Ai Tweaker（如内存频率不对）:
  └── XMP Profile: Profile 1               ← 让内存跑 2666
```

打开 PCIe 接口高于 4GB 的解码寻址，这对于多卡系统是必须打开的设置。系统要打开 PCIe 3.0。将内存频率跑到 2666MHz.

## 2. 硬件配置 

### 生产节点 HeteroServe Production Node

```
═════════════════════════════════════════════════════════
HeteroServe 主节点完整配置
═════════════════════════════════════════════════════════

主板:    ASUS Prime Z270-A
CPU:     Intel Core i7-7700 (4C/8T, 3.6/4.2 GHz, 65W TDP)
内存:    32GB DDR4-2666 (4×8GB, 铭瑄)
                + 32GB Swap on NVMe (vm.swappiness=1)
系统盘:  NVMe SSD on M.2_1
        - /             (Ubuntu 24.04 LTS)
        - /opt/models   (模型仓库)
        - /swapfile     (32GB swap)
电源:    ≥1500W 80+ 金牌
机箱:    开放式矿机架

GPU 配置（阶段 1）:
├── PCIe x16 #1 (CPU 直连 x8): 2080Ti #1 (22GB)
├── PCIe x16 #2 (CPU 直连 x8): 2080Ti #2 (22GB)
├── PCIe x16 #3 (PCH x4):      2080Ti #3 (22GB)
├── M.2_2:                      [空闲，留给阶段 2]
├── PCIe x1 #1, #2:             [预留]
└── 总显存:                     66GB

GPU 配置（阶段 2 升级后）:
├── PCIe x16 #1 (CPU x8):  2080Ti #1 (22GB)
├── PCIe x16 #2 (CPU x8):  2080Ti #2 (22GB)
├── PCIe x16 #3 (PCH x4):  2080Ti #3 (22GB)
├── M.2_2 → ADT-Link R43SR
   → 2080Ti #4 (22GB)        ← 阶段 2 新增
└── 总显存:                88GB
═════════════════════════════════════════════════════════
```

### 1.1 GPU
- 型号：3× NVIDIA RTX 2080Ti 22GB（魔改版） 
- 架构：Turing（SM 75，Compute Capability 7.5）
- Tensor Core：Gen 2（支持 FP16/INT8/INT4，**不支持 BF16/FP8/TF32**） 
- 显存：22GB GDDR6 Per GPU（原版 11GB） 
- FP16 算力：约 26.9 TFLOPS / GPU - 互联：PCIe 3.0 x16（无 NVLink）
### 1.2 主板

- 型号：ASUS Prime Z270-A 
- 芯片组：Intel Z270 - PCIe 3.0 
### 1.3 CPU 
- 型号：Intel i7 7700
- 核心/线程：4核 / 8线程
### 1.4 内存 

系统中使用的内存，8GB x 4 = 32 GB, 主存频率为 DDR4-2666 MHz。

![](/docs/analysis%20&%20research/assets-bios/9ae28a4053206f8dd1043f5b25f6a126.png)

32GB 内存在模型加载到显存的过程中，可能不够用。这时我们需要将部分 Nvme 设置为虚拟内存来使用。内存 + 虚拟内存主要是用在模型的加载阶段，之后使用模型进行推理的阶段，更多使用的是 GPU 的显存了。

### 1.5 存储

Nvme SSD(M.2_1, PCIe 3.0 x 4)。容量 512GB。
SSD 关键目录划分如下：

| 目录          | 用途               |
| ----------- | ---------------- |
| /           | Ubuntu 24.04 TLS |
| /opt/models | 存放模型文件           |
| /swapfile   | 32GB 虚拟内存        |

### 1.6 已知瓶颈与硬件约束汇总

| 约束硬件      | 系统影响                        | 详情                                                                                       |
| --------- | --------------------------- | ---------------------------------------------------------------------------------------- |
| PCIe 拓扑架构 | x8 x8 x4 限制 TP=3 可行性        | [11-PCIe接口约束分析与架构设计](/docs/analysis%20&%20research/11-PCIe接口约束分析与架构设计.md)     |
| GPU 架构    | Turing架构GPU 缺 BF16/FP8/FA-3 | [08-Turing架构sm_75约束分析](/docs/analysis%20&%20research/08-Turing架构sm_75约束分析.md) |
| 内存        | 32GB不够加载模型，需要设置虚拟内存         |                                                                                          |

## 3. PCIe 接口拓扑关键约束

GPU与 PCIe 接口的拓扑结构如下：

```
                  CPU (i7-7700, LGA1151)
                  16 lanes PCIe 3.0
                          │
            ┌─────────────┼─────────────┐
         x8 │          x8 │             │
    [Slot 1]│      [Slot 2]│             │
    GPU #1  │      GPU #2  │             │
    (22GB)  │      (22GB)  │             │
                                         │ DMI 3.0 (~4 GB/s)
                                         │
                                  Z270 PCH
                  ┌──────────────────────┼──────────────┐
               x4 │                   x4 │              │
         [Slot 3] │              [M.2_2] │              │
         GPU #3   │              GPU #4  │              │
         (22GB)   │              (22GB)  │              │
                                         │ x4
                                  [M.2_1] NVMe SSD
                                  
                                  (其他 PCH 设备：
                                  SATA, USB, x1 槽, 网卡)
                                  
                                  全部共享 DMI 3.0 总带宽
```


| 插槽        | bus来源 | 单卡模式 | 三卡模式 |
| --------- | ----- | ---- | ---- |
| PCIEX16_1 | CPU   | x16  | x8   |
| PCIEX16_2 | CPU   | x16  | x8   |
| PCIEX16_3 | PCH   | x4   | x4   |

-  实际三卡运行：**x8 / x8 / x4（PCIe 3.0）** 
-  带宽换算：x8 ≈ 7.88 GB/s 单向，x4 ≈ 3.94 GB/s 单向 
-  PCIEX16_3 与 M.2_2 共享带宽（M.2_2 启用时第三槽降级）

PP 流水线里，rank 2 是最后一段，它的输出主要是 token id（数据量极小），对带宽最不敏感。把带宽最弱的 PCH x4 槽分给它，瓶颈影响最小。rank 0/1 在 CPU 直连的 x8 槽，承担前两段较重的 activation 传递。

| PP rank | 物理槽位      | 链路                        | Bus-Id  |
| ------- | --------- | ------------------------- | ------- |
| rank 0  | PCIEX16_1 | CPU 直连 PCIe 3.0 x8        | 01:00.0 |
| rank 1  | PCIEX16_2 | CPU 直连 PCIe 3.0 x8        | 02:00.0 |
| rank 2  | PCIEX16_3 | PCH，PCIe 2.0 x4（经 DMI 上行） | 04:00.0 |
**落地保证**：启动时设 `CUDA_DEVICE_ORDER=PCI_BUS_ID`，让 CUDA 按物理总线号给 GPU 编号，保证 rank↔槽位映射稳定（否则 CUDA 默认按性能排序，可能每次不一致，把 rank 2 错配到 x8 槽、rank 0 错配到 x4 槽）。



