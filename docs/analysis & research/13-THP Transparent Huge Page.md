# 1. THP 透明大页

Linux 下内存按分页管理。标准页的大小是 4KB，即 Linux 默认把内存切成 4KB 的小块管理，每个块叫做一页 Page。

CPU 的 MMU 通过页表把虚拟地址翻译成物理地址，翻译结果缓存在 TLB(Translation Lookaside Buffer)里。

对于大内存的进程，比如 vLLM 要管理几十 GB，4KB 的页面意味着海量页表项，TLB 容量有限，通常是几百到几千项。访问的时候 TLB 命中率就会很低，LB 缓存每次 miss，都要走多级页表查找，延迟上升。

「大页，Huge Page(2MB 或者 1GB)」 : 把标准页至少放大 512 倍到 2MB， 同样大小的内存，只需要 1/512 的页表项，这样就会使得 TLB 命中率大幅提升。

>大页的核心目标，是为了大内存进程在内存中分页管理时，能有更高的 TLB 命中率，降低延迟。

「透明大页(Transparent Huge Page)」: 传统大页(HugeTLB)需要程序员显示申请，提前预留，使用门槛高。THP是 Linux 内核里做的“自动优化”，运行时可以偷偷把多个 4KB 页合并成2MB大页，程序无感知。

这样的优化听上去很好，但是，<u><b>对延迟敏感的服务来说，THP是个灾难。</b></u>

# 2. THP 对 vLLM 是个灾难

① 合并和拆分开销不可预测

>THP由内核线程 `khugepaged` 在后台扫描和合并页面。当它工作时，会拿锁，暂停部分内存操作，造成不定时的延迟刺尖。如果服务延迟 99% 都是100ms以内，某时刻突然 500ms，通常就是THP造成的。

② 内存碎片化引发分配延迟

>当系统申请 2MB 的大页时，需要找到一段物理上连续的 2MB 空间。系统运行时间长了就会内存碎片化，内核要做 compaction(内存压缩)来腾出连续空间，这个过程会冻结进程几毫秒到几十毫秒不等。

③ 加剧swap时的延迟

>THP 被换出 swap 时，要先拆回 4KB 小页才能写入，换回内存又要重新合并。这层操作，让 swap延迟更加恶化。

<u><b>几乎所有内存密集型 + 延迟敏感的服务都明确推荐关闭THP</b></u> 包括 Redis, MongoDB, PostgreSQL等等。它们的共同特点是，进程持有大量内存，且对延迟敏感。

# 3. THP enabled 文件

THP 的 enabled 文件中有三个值

```bash
cat /sys/kernel/mm/transparent_hugepage/enabled
```

会看到

```shell
always [madvise] never
```

`always`:  对所有进程，激进的合并大页 (老内核默认值，有很大问题)
`madvise`: 只对显示调用 madvise(MADV_HUGEPAGE)的进程合并 (现代内核默认)
`never`: 完全关闭(生产服务推荐)

vLLM 的场景下,即使是 `madvise` 也不够保险——因为 PyTorch/CUDA runtime 可能内部就调了 madvise。所以最佳方案是直接关闭 `never`。

## 持久化设置关闭

这个设置重启后会丢失
`/sys/` 是内核运行时接口，重启后会回到默认，要做持久化设置，有两种方法

方法一：写进 systemd service
```bash
sudo tee /etc/systemd/system/disable-thp.service << 'EOF'
[Unit]
Description=Disable Transparent Huge Pages
After=sysinit.target local-fs.target
Before=mongod.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c "echo never > /sys/kernel/mm/transparent_hugepage/enabled"
ExecStart=/bin/sh -c "echo never > /sys/kernel/mm/transparent_hugepage/defrag"

[Install]
WantedBy=basic.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable disable-thp.service
sudo systemctl start disable-thp.service
```

方法二：写进 GRUB内核参数 (更早生效)
编辑 `/etc/default/grub`,在 `GRUB_CMDLINE_LINUX_DEFAULT` 里加 `transparent_hugepage=never`:
```bash
sudo sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="\(.*\)"/GRUB_CMDLINE_LINUX_DEFAULT="\1 transparent_hugepage=never"/' /etc/default/grub
sudo update-grub
# 下次重启生效
```

# 4. THP defrag 文件

`defrag` 控制的是**当内存碎片化时,内核是否主动做碎片整理来腾大页**。同样设为 `never`,彻底关闭这条延迟来源。

`enabled` 和 `defrag` 两个文件，是两个独立的开关,**两个都要关才算彻底**。
```bash
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag
```

---
### 附：查阅

| ✅   |     |
| --- | --- |
|     |     |
