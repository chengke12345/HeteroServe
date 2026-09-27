# Software & Environment Setup

## 1. 核心软件组件与版本

本项目使用的核心软件组件及其版本汇总如下：

| 组件              | 锁定版本             | 备注                         |
| --------------- | ---------------- | -------------------------- |
| OS              | Ubuntu 24.04 LTS | 操作系统                       |
| NVIDIA Driver   | 595.71.05        | 支持 CUDA 13.2               |
| CUDA Toolkit    | 13.0             | vLLM 官方镜像对应                |
| Python          | 3.11             | 3.12 部分库尚未完全适配             |
| PyTorch         | 2.11.0+cu130     | vllm 版本要求                  |
| **vLLM**        | 0.21.0           | **原生支持 Qwen3**             |
| Transformers    | ≥ 4.51.0         | Qwen3 必需                   |
| sm_75 attention | FlashInfer       | 全注意力。FA2失效                 |
| xFormers        | 0.0.29.post2     | 支持sm_75的硬件arch cc          |
| 量化 kernel       | AWQ-Marlin       | vLLM 针对AWQ量化格式加速           |
| Docker          | 24+              | 配 nvidia-container-toolkit |
| docker-compose  | v2               | profile 功能必需               |
| Prometheus      | latest           | metrics 抓取                 |
| Grafana         | latest           | 可视化面板                      |
| DCGM Exporter   | 3.x              | GPU 指标                     |
| Nginx           | alpine latest    | 流式网关                       |
| Locust          | 2.46.4           | 压力测试                       |

## 2. Conda 虚拟环境与软件安装说明

项目使用 Conda 虚拟环境，只使用 Conda 安装基础环境，而不用它安装 Pytorch 等依赖软件。Pytorch 从 2.5.0 之后，就停止经过 conda channel 分发预编译包。我们使用 conda channel 和 nvidia channel. 会出现错误，要么是 `Package Not Found Error`。要么是 CPU-only 构建版本。

Conda 只创建一个干净的 Python 环境(隔离，按名中心化管理，删环境即清理干净)， Pytorch 与 vLLM 以及其他软件走 pip。conda 的环境管理仍好用——`conda activate` 与当前目录无关；环境装在 `~/miniconda3/envs/<name>/`，删环境一键清净；适合做"Python 解释器 + 隔离"的容器。只是不让它管 torch。

完整的软件栈安装配置文件，参考 [environment.yml](/environment.yml)

## 3. vLLM 的版本选择 v0.8.5.post1  .vs.  0.21.0

我们在使用 vLLM 的时候，考虑两个版本 vLLM 0.8.5.post1 与 vLLM 0.21.0.。
它们最大的区别是前者是使用 v0 引擎，并行 v1 引擎，而后者只使用 v1 引擎，彻底抛弃 v0 引擎。

v0 和 v1 引擎直接导致后端算子的选择和 Fallback 路径完全不同。v0 引擎采用的是 `flash-atten --> xFormers` 路径， v1 采用的是 `flash-atten --> Flashinfer --> Triton-atten --> Flex-attention`.

所以 v0 和 v1 的区别如下: 

|backend|V0|V1|
|---|---|---|
|XFORMERS|✅|❌(不存在)|
|FLASHINFER|✅|✅|
|TRITON|✅|✅|
|FLEX_ATTENTION|❌|✅(V1 专属)|
v0.8.5走的 v0，v0.21.0 走的 v1。本质区别是 v0.8.5 使用的后端算子是 xFormers，v0.21.0 使用的后端算子是 FlashInfer.

不同引擎 v0 和 v1 的讨论，详见 [10-vLLM引擎-V0与V1](/docs/analysis%20&%20research/10-vLLM引擎-V0与V1.md)
0.8.5.post1 版本的完整环境配置文件，参考 [environment-vllm0.8.5.yml](/environment-vllm0.8.5.yml)
0.21.0 版本的完整环境配置文件，参考 [environment.yml](/environment.yml)

## 4. 系统环境调优 

软件版本确定后。我们需要对系统环境进行设置调优。
####  - Swap设置

- 在 Nvme 上 配置 32GB 的 Swap，以文件的形式提供虚拟内存。
- 调整 Swap 倾向，尽量不用 Swap，仅加载时使用。
- 允许内存超额分配，fork 大进程的时候是必须的设置。
- 将文件缓存压力降低
#### -  网络性能

设置高并发 http 服务监听队列，将连接数设置为

```sh
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=65535
```

#### - THP(Transparent Huge Pages) 关闭

关闭透明大页的功能
```bash
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
echo never | sudo tee /sys/kernel/mm/transparent_hugepage/defrag
```

关于透明大页的讨论，详见 [13-THP Transparent Huge Pages](/docs/analysis%20&%20research/13-THP%20Transparent%20Huge%20Page.md)

#### - CPU 性能模式

```bash
sudo apt install -y cpufrequtils
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils
```

将 CPU 调整为性能模式。

更详细的系统优化选项，参见系统优化脚本 [02_sys_opt.sh](/scripts/02_sys_opt.sh)
系统优化脚本执行，优化结果为 [02-sys_opt_report.txt](/logs%20&%20reports/02-sys_opt_report.txt)

