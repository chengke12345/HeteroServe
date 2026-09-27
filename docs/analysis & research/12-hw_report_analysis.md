我们对硬件状况进行验证。测试硬件的 shell 脚本，详见 [01_hw_verify.sh](/scripts/01_hw_verify.sh)
测试结果，与硬件分析预期完全吻合，详细的硬件测试报告，详见[01-hw_report.txt](/logs%20&%20reports/01-hw_report.txt)

硬件测试报告说明
## 1. GPU 拓扑与通信

通过`nvidia-smi topo -m` 查看三张GPU拓扑结构。

![image](/docs/analysis%20&%20research/assets-hw_report_analysis/c2a90708c6ec234dff51842356988419.jpg)

三张 GPU 两两之间的连接类型都是 PHB(PCIe Host Bridge), 也就是说GPU之间的通信需要穿越 PCIe 总线以及 PCIe 主机桥接器, 即通过 CPU, 任意两张 GPU 之间的通信，都必须先通过 PCIe 总线回到 CPU，再由 CPU 转发给另一张 GPU。它们之间没有直连通道，也没有 PCIe 交换芯片。

其他数据交换方式包括(单/多) PCIe桥, NvLink等。项目第二阶段，会对 NvLink 方案进行测试评估。

## 2. GPU 状态

使用 `sudo lspci | grep -i nvida` 以及 `sudo lspci -vv -s 0x:00.0 ｜ grep -E "LnkCap | LnkSta"` 来查看每个GPU的状态：

![image](/docs/analysis%20&%20research/assets-hw_report_analysis/f612fe7753c61f6d0ae35d97ce1bc7ba.png)

可以看到三张卡 BDF 01:00.0，02:00.0, 04:00.0 的 width 完全正确

| BDF     | LnkCap Width | LnkSta Width | 对应槽位      | 结论                      |
| ------- | :----------: | :----------: | --------- | :---------------------- |
| 01.00.0 |     x16      |      x8      | PCIEX16_1 | 符合预期 ✅                  |
| 02.00.0 |     x16      |      x8      | PCIEX16_2 | 符合预期 ✅                  |
| 04.00.0 |     x16      |      x4      | PCIEX16_3 | 符合预期 ✅ (PCH PCIe2.0 x4) |
## 3. PCIe 链路速度

关于降级(Downgrade)

上面的返回结果中，3 张显卡的 LnkSta 都是 2.5 GT/s, 但是 LnkCap 都是 8GT/s, 并且显示 downgraded. 这完全正常，这是Nvidia 的驱动 ASPM 省电行为。idle 状态下，三张卡都会自动降级到 PCIe 1.0, 2.5 GT/s。我们需要重点关注当前宽度 x8, x8, x4 就没问题。downgraded 是 lspci 看到当前值低于 LnkCap时就会机械的加标签，不是代表硬件故障。speed 是动态调整的，这个拓扑反馈是完全正常的，没有问题。
## 4. BDF 编号

三张GPU的 BDF 编号是 01，02，04，跳过了03。因为 03:00.0 这个 bus 号被 PCH 自己占用了，所以 PCIEX16_3 使用的是更靠后的一个 bus 号。这也说明了 slot 3 确实走的 PCH 那条链路。
## 5. 内存与Swap

![](/docs/analysis%20&%20research/assets-hw_report_analysis/Pasted%20image%2020260614165427.png)

内存可以看到总共 31Gi，使用了3.1Gi 等等。它的 swap 有8Gi, 因为当前我们还没有配置虚拟内存，系统使用的是默认虚拟内存。默认 8Gi，并且它是以文件的形式存在，文件是 `/swap.image`，这与我们后面要自己设置的 32GB `/swapfile` 采用的文件虚拟内存方式一致。 
## 6. Slot / Rank 绑定

PP 流水线里，rank 2 是最后一段，它的输出主要是 token id（数据量极小），对带宽最不敏感。把带宽最弱的 PCH x4 槽分给它，瓶颈影响最小。rank 0/1 在 CPU 直连的 x8 槽，承担前两段较重的 activation 传递。

|PP rank|物理槽位|链路|Bus-Id|
|---|---|---|---|
|rank 0|PCIEX16_1|CPU 直连 PCIe 3.0 x8|01:00.0|
|rank 1|PCIEX16_2|CPU 直连 PCIe 3.0 x8|02:00.0|
|rank 2|PCIEX16_3|PCH，PCIe 2.0 x4（经 DMI 上行）|04:00.0|

**落地保证**：启动时设 `CUDA_DEVICE_ORDER=PCI_BUS_ID`，让 CUDA 按物理总线号给 GPU 编号，保证 rank↔槽位映射稳定（否则 CUDA 默认按性能排序，可能每次不一致，把 rank 2 错配到 x8 槽、rank 0 错配到 x4 槽）。





