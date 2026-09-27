Prometheus 是一个开源的监控与警告系统，主要用于监控分析服务器, 容器, 微服务和 K8s 集群。
它的基本工作方式是：被监控的应用程序通过 HTTP 暴露指标，例如请求量，错误，CPU 使用率等。Prometheus 是定期主动抓取这些指标并保存为时间序列数据，保存在 Prometheus 服务器上的 TSDB 时序数据库中。用户通过 PromQL 查询和分析数据。当达到预设条件时，Prometheus 会将警告交给 Alertmanager 处理。Prometheus 通常会配合 Grafana 展示监控图表。

Prometheus 核心组件包括：

>- Prometheus Server: 抓取，存储和查询指标。
>- Exporter：把系统或者第三方服务提供的状态转换成 Prometheus 指标，例如 DCGM Exporter, Node Exporter,  或者 MySql Exporter。
>- PromQL: Prometheus Query Language, Prometheus 专用的时间序列查询语言。
>- Alertmanager: 告警分组，静默和同志，支持邮件，Slack等渠道。
>- Service Discovery: 自动发现 Kubernetes, 云平台等环境中的监控目标。

简单说, Prometheus 负责收集, 存储, 查询指标，Grafana 负责展示，Alertmanager 负责发送警告。

# 1. Exporter/DCGM/DCGM Exporter

Exporter 是 Prometheus 中的一个组件类型或设计规范，不同数据源实现 Exporter 将数据暴露成统一的 HTTP 接口 `/metrics`. Prometheus 对不同的数据源采取统一的数据抓取方式，获取统一格式的 Prometheus 指标数据。

Exporter 更像是一个适配器，连接不同的数据源与 Prometheus，将数据源的数据转换成 Prometheus 指标格式。Prometheus可以统一抓取，统一处理。

Exporter 是一个抽象概念，具体的数据源需要具体的实现，类似于类与对象，接口与实现。

DCGM-Exporter 是 DCGM 实现的 Exporter. DCGM(Data Center GPU Manager)是 NVIDIA 提供的用于采集 GPU 运行数据和状态数据的工具，DCGM-Exporter, 负责把 DCGM 采集的 GPU 数据转换成 Prometheus 指标格式，供 Prometheus 抓取。

关于 DCGM 与 DCGM-Exporter 的详细讨论，参考 [18-DCGM & DCGM-Exporter](/docs/analysis%20&%20research/18-DCGM%20&%20DCGM-Exporter.md)

# 2. PromQL

PromQL, Prometheus Query Language, 是 Prometheus 专用的时间序列查询语言，可用于筛选指标，聚合数据，计算变化率和进行数学运算。用户可以通过 PromQL 查询和分析数据。例如：

```promql
rate(http_requests_total[5m])
```

表示计算 http_requests_total 指标在最近 5 分钟内的平均每秒增长率。

### `■`<b>数据格式统一和指标差异</b>

Prometheus 可以同时抓取多个 Exporter 的数据。

多个 Exporter 从各自的数据源采集指标数据，转换为统一的 Prometheus 格式，暴露在 /metrics 接口上。 Prometheus 用同一种方式抓取不同系统的监控数据。

统一是指露指标数据暴露的接口，数据格式统一，不是指所有数据源都用同一套指标体系和指标名。每个 Exporter 根据自己的数据源特点，有自己的指标体系和名字。比如 DCGM Exporter 和 MySQL Exporter 的指标体系肯定不相同，前者是针对 GPU 的，后者是针对 MySQL 数据库的。但是他们暴露的接口(`/metrics`) 和 指标的格式是统一的。

### `■`<b>指标名称与时间序列 </b>

不同 Exporter 提供不同的指标体系。Promethus 提供统一的 PromQL 查询语言，查询指标数据：

```
指标名称 + 标签集合
```

「指标名称」本身就是一个 PromQL 的查询指令，或者是一条最简单的查询语句。它表示查询这个指标。
「标签集合」表示给定一系列标签，实际上也就是对指标名字下的一系列的筛选和限定条件。

一个指标，是随时间产生的一系列数值，每个数值叫做一个「数据点」。一个指标代表的是多个数据点组成的一个「时间序列」。
一条 PromQL 查询语句，返回的是一个「时间序列」，即<u>指标名称和标签组合完全相同的一组，按时间产生的数据点集合</u>。

查询返回的时间序列的格式通常是:

```
时间戳 -> 样本值
例如：
0:00 → 8589934592
10:01 → 8455716864
10:02 → 8321499136
```

>总结: `指标名称 + 标签集合` 就是一条 PromQL 查询语句. 指标名称就是查询这个指标的指令，标签就是添加一系列的筛选条件。查询返回结果是一条时间序列，它由多个 `时间戳->样本值` 的数据点组成。

### `■`<b> 指标与标签</b>

如果 Prometheus 中配置了多个 Targets，Prometheus 会定期抓取所有有效 Targets 暴露到各自 /metrics 的指标，将他们都存储到本地的时序数据库 TSDB 中。存储时，会自动添加 job 和 instance 标签。job + instance 就能唯一确定一个抓取目标，所以不同抓取目标暴露的指标，即使同名也没关系。其工作流程如下：

```
应用/Exporter 提供 /metrics
          ↓
Prometheus 定期抓取
          ↓
添加 job、instance 标签并存储
          ↓
PromQL 查询已存储的数据
```

添加 job 和 instance 标签，并且存储在本地时序数据库中的数据格式，类似于

```
vllm:num_requests_running{
  model_name="Qwen3-32B",
  job="vllm-main",
  instance="vllm-main:8001"
} 8
```

>注意⚠️：Prometheus中，job + instance 能够唯一确定一个常规的抓取目标，指标名称+完整标签集 能够唯一确定一条时间序列。使用 PromQL 查询某指标的时候，如果没有指定标签，就返回该指标下，所有标签组合返回来的时序数据。

Prometheus 中的指标分为内置指标和抓取指标。Prometheus 从数据源抓取一些数据的时候，它会生成一些内置的指标，比如 up。另外一些指标，是由应用的 `/metrics` 接口或者 Exporter 提供，比如 `vllm:xxx`。

同样，指标的标签，一部分也是由 Prometheus 抓取到之后，自动加上去，再存入本地 TSDB(Time Series Database) 中的。还有一些标签，是由应用的`/metrics` 或 Exporter 自带的， 它们是转换原始数据到 Prometheus 指标格式时加上的。

### `■`<b> 统计查询</b>

有时候，我们使用 PromQL 的时候，需要统计计算一些指标数据，然后再展现出来。例如：

```promQL
sum by (job, model_name) (
  rate(vllm:prompt_tokens_total[5m])
)
```

>这条语句会计算每条`vllm:prompt_tokens_total` 指标近 5 分钟的 token/s, 然后找出 job 和 model 完全相同的序列。将他们的 token/s 相加，返回的结果只保留 job 和 model_name 标签。

例如：

```
{job="vllm", model_name="qwen3", instance="server-1"} = 2 tokens/s
{job="vllm", model_name="qwen3", instance="server-2"} = 3 tokens/s
{job="vllm", model_name="qwen7b", instance="server-3"} = 4 tokens/s
```

聚合后得到：

```
{job="vllm", model_name="qwen3"}  = 5 tokens/s
{job="vllm", model_name="qwen7b"} = 4 tokens/s
```

也就是说，它相加的不是原始 Counter，而是各条序列经过 `rate()` 计算后的速率。`instance`、`engine` 等标签即使不同，只要 `job` 和 `model_name` 相同，就会被归入同一组。

### `■`<b> rate()函数</b>

rate() 用来计算 counter 在指定时间窗口平均每秒增长多少。vllm:prompts_tokens_total 是 counter, 记录的是服务启动以来处理的 prompt 总数。
例如：

```
10:00:00   1000
10:01:00   1120
10:02:00   1240
10:03:00   1360
10:04:00   1480
10:05:00   1600
```

执行：

```
rate(vllm:prompt_tokens_total[5m])
```

近似结果为：

```
(1600 - 1000) / 300秒 = 2 tokens/s
```

如果不使用 rate(), `vllm:prompt_tokens_total` 返回的是当前累计值即 `1600`, 如果加上`[5m]`, 那么`vllm:prompt_tokens_total[5m]` 是一个范围选择器，返回最近 5 分钟的所有原始样本：

```
[
  (10:00, 1000),
  (10:01, 1120),
  (10:02, 1240),
  (10:03, 1360),
  (10:04, 1480),
  (10:05, 1600)
]
```

结果是一个 range vector, 通常不会作为 Grafana Time Series 查询结果，需要交给其他函数计算。

# 3. prometheus.yml 配置文件

Prometheus 的数据源通过配置文件 `prometheus.yml` 进行配置的，主要配置内容是 Exporter，以及可以用 `/metrics` 直接抓取的服务器地址。例如：

```yaml
# prometheus.yml
global: { scrape_interval: 5s, evaluation_interval: 15s }
scrape_configs:
  - job_name: vllm
    metrics_path: /metrics
    static_configs:
	    - targets: ["vllm:8000"]
  - job_name: dcgm
    static_configs: 
	    - targets: ["dcgm-exporter:9400"] 
```

### `■` <b>全局配置</b>

`scrape_interval: 5s`, 表示抓取指标周期是每隔 5s 抓取一次。
`evaluation_interval: 15s`, 计算指标为每隔 15s 计算一次。 
放在 global 下面，表示全局配置。

### `■`<b>job</b>

job 在 prometheus 中表示一组采用相同方式抓取的监控目标。它不是后台任务或者定时作业，而是监控对象逻辑分组。一个分组下面可以配置多个目标抓取端点，比如 vLLM 后端大模型，是一个大抓去运行数据的目标，它就可以做为一个抓取的 job, 表示一个大的逻辑分组。但是，vLLM 后端可能部署在多个物理服务器上，抓取数据的时候，必须分别从每个节点上分别抓取, 但是这 n 个节点上抓取数据的方式是相同的，所以放在同一个 job 分组下面。比如：

```
- job_name: vllm
  metrics_path: /metrics
  static_configs:
    - targets: ["vllm-main:8001"]
    - targets: ["vllm-backup:8002"]
```

Job 名称是 vllm-main。这个Job 分组下面有两个抓取目标，一个抓取地址是 http://vllm-main:8001/metrics 。另一个抓取地址是 http://vllm-backup:8002/metrics 

### `■` <b>static_configs</b>

static_configs 表示：监控目标由用户直接写死在配置文件中，而不是由 Prometheus 自动发现。例如上面的配置片段中，它的含义是 vllm-main 这个 job 固定到 vllm-main:8001 的地址处抓取指标，默认抓取指标的路径是 `/metrics`。

static_configs 叫做「静态配置」。一个静态配置可以包含多个实例, 还可以给这些目标增加共同标签
```
static_configs:
  - targets:
      - "vllm-1:8000"
      - "vllm-2:8000"
    labels:
      environment: production
      model: qwen3
```

「静态」:指的是目标列表由配置文件明确指定。若要删除目标，通常需要修改配置并重新加载 Prometheus。它不代表目标的 IP 永远不变。比如 Docker 服务名背后的容器 IP 可以变化，Prometheus 可以通过 Docker DNS 重新解析。
「动态」 : 与静态对应的是动态服务发现，例如 Kubernetes, Consul, Docker 或云平台服务发现。

### `■`<b> job 与 targets</b>

配置的targets 是配置的 Prometheus 抓取的指标端点。一个 job 下面可以配置多个 targets. Prometheus 会自动给抓到的时间序列添加标签

```
job="vllm-main"
instance="vllm-main:8001"
```

所以，<u>job + instance 能够唯一确定一个抓取目标</u>。同一个job下，可以用不同的 instance 区分不同的抓取目标。逻辑结构可以理解为

```
Job（服务类别）
└── Target / Instance（具体服务实例）
```

<u>同一个job下面的多个 targets，它们的关系就是同一类服务下的多个独立运行实例，需要统一的监控和管理。Prometheus 会分别抓取，Targets 没有主从或依赖关系</u>。比如上面配置中(vllm-1 和 vllm-2)，即使两个 targets 暴露了同名的指标，也不会混淆

```
vllm:num_requests_running{
  job="vllm",
  instance="vllm-1:8000"
} 3

vllm:num_requests_running{
  job="vllm",
  instance="vllm-2:8000"
} 5
```

指标名称 + job + instance + 其他标签 唯一标识一条时间序列。job 和 instance 本身也是标签的一种。所以，也就是 指标名 + 全部标签 唯一标识一条时间序列。

### `■`<b>targets 与 instance</b>

targets 是配置文件中写入的抓取地址列表。instance 是Prometheus 抓取后，自动附加到指标上的标签。它们通常是一一对应的。所以一个job配置的一个target可以理解为
```
配置目标：vllm-main:8001
抓取地址：http://vllm-main:8001/metrics
指标标签：instance="vllm-main:8001"
-----------------------------------
job名称 + 指标标签 --> 唯一确定抓取目标(不同job下面可能存在相同的指标标签)
```

`target` 是 Prometheus 要连接的实际抓取目标；`instance` 是用于标识这个目标的时间序列标签。如果没有指定instance, 默认值通常就是 `target` 的 `主机名:端口`，但可以被重写。


```
job_name：一类服务  → job 
├── target 1 → instance 1
└── target 2 → instance 2
```

job_name 和 target 是数据源配置文件里面的静态配置，Prometheus 从数据源抓取指标数据，然后会给它打标签 job_name 对应 job标签，target 对应 instance 标签，他们是一一对应的。

```
job_name + target1 <----> 标签job + instance1 (一一对应)
job_name + target2 <----> 标签job + instance2 (一一对应)
```

### `■`<b>targets 与 Exporter</b>

targets 配置的是 Exporter 的地址，更准确的说，暴露 Prometheus 指标的 HTTP 端点，它不一定是独立的 Exporter, 也可能是应用直接提供的指标，不需要独立 Exporter, 比如：

```
vLLM -> vllm-main:8001/metrics -> Prometheus
```

Exporter 负责从数据源读取原始状态，然后转换为 Prometheus 指标格式，通过 /metrics 提供给Prometheus 抓取。当然应用自己提供这样的功能也没问题，就是上面 vLLM 框架提供的功能。

>所以，targets 配置的是 Prometheus 抓取的「指标端点」，这个端点既可能由独立 Exporter 提供，也可能由应用直接提供。<u>Exporter 通常是在数据源上或者靠近数据源部署，但不是硬性要求</u>。

# 4.  Prometheus 的主动拉取(pull)工作模式

Prometheus 的工作模式就是 Pull (主动拉取)。它运行流程为：

>Prometheus 会读取 prometheus.yml 中配置的所有有效 Target，按 scape_interval 定期请求每个 Target 的 `/metrics`. 默认抓取该端点本次返回的全部指标。为指标添加 job, instance 等标签。然后将样本写入本地时序数据库 TSDB。用户再通过 PromQL 查询已经存储的数据。

PromQL 查询的是 Prometheus 中已经采集放在 TSDB 数据库中的数据，本质上是查询 TSDB 数据库。而不是在 PromQL 查询时，临时访问 Exporter。

Prometheus 进程正在运行。Target 地址可以访问， `/metrics` 路径，端口，协议和认证配置正确。Exporter 或应用正在正常提供指标。配置修改后已重新加载或重启 Prometheus。

<b>▪︎ up 指标</b>

job + instance 可以唯一确定一个抓取目标，使用 up 指标，抓取现在目标的状态

```
up
结果：
up{job="vllm-main", instance="vllm-main:8001"}1
```

1 表示最近一次抓取成功，结果为0表示目标存在但抓取失败。

Prometheus 默认会抓取目标的`/metrics` 的全部指标，但是如果配置了过滤或限制规则，部分指标可能丢弃。

> up 查询如果没有加任何标签的筛选条件，那么结果将列出指标名为 up 的所有现存时间序列。up 是 Prometheus 自动生成的一个内置指标。它不是由被监控应用或 Exporter 主动暴露的。

Prometheus 每次抓取一个target 后都会记录对应的 `up{job="...", instance="..."} 0或1`，它反映的是 Prometheus 能否成功抓取该目标，不一定能反映应用的业务功能是否健康。

up 指标包含这台 Prometheus 服务器已配置或发现的每个抓取目标的状态。可以把 up 理解为 Prometheus 视角下的抓取目标状态表，它会为每个 target 自动生成 up 指标。

