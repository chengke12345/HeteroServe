
HeteroServe 将使用的所有服务 进行 Docker 容器化，然后用 Docker Compose 容器编排工具进行编排。总体上，模型服务采取主备模式，部署主模型和备用模型，通过 nginx 实现流式网关，用 Prometheus + DCGM / DCGM Exporter + Grafana 的架构，进行生产节点的观测和统计分析展示。
docker compose 需要编排的服务如下：

| 服务名称           | 说明            | 基础镜像                                    | 备注                           |
| -------------- | ------------- | --------------------------------------- | ---------------------------- |
| vllm-main      | 主服务模型         | 从Dockerfile 构建                          | 部署 Qwen3-32B-AWQ             |
| vllm-backup    | 备用服务模型        | 从Dockerfile 构建                          | 部署 Qwen3-14B-FP16            |
| nginx-main     | 主模型流式网关       | nginx:1.30.4-alpine                     | 依赖 vllm-main 服务先启动           |
| nginx-backup   | 备用模型流式网关      | nginx:1.30.4-alpine                     | 备用nginx主要是分开依赖               |
| nginx-exporter | nginx数据格式转换服务 | nginx / nginx-prometheus-exporter:1.5.1 | 转化nginx数据成prometheus 指标格式    |
| prometheus     | 监测服务          | prom/prometheus:latest                  | 从 /metrics 接口抓取指标            |
| grafana        | 看板系统          | grafana/grafana:latest                  | web服务,连接prometheus           |
| dcgm-exporter  | GPU 数据格式转换器   | nvidia/dcgm-exporter:latest             | 将 GPU 的性能数据转换为prometheus指标格式 |

关于 docker-compose 的完整配置文件，详见 [compose.yml](/compose.yml)。 

# 1. 主备模型服务

项目采用主备模型的方式提供服务，主模型为 Qwen3-32B-AWQ, 采取 PP=3 的流水线部署方式(Pipeline Parallelism)，在 compose 网络中，对应的是 vllm-main 服务。备用模型采用 Qwen3-14B-FP16, 采取 TP=2 的张量并行部署方式(Tensor Parallelism)，在 compose 网络中对应的是 vllm-backup 服务。

vllm-main 分组在 "main" profile 中, vllm-backup 分组在 "backup" profile 中，在主模型出现故障的时候，可以启动备用模型并切换到备用模型。

注意⚠️：HeteroServe 项目中，主模型和备用模型，在同一时刻，只有一个模型是启动并活跃提供推理服务，不是两个模型实现主-主的高可用性架构的关系。因为模型和传统服务器不同，它启动之后，会占用大量 GPU 和 显存资源。本项目以及其他大多数项目中，GPU 算力，显存，带宽都是紧缺资源，在本项目中尤其显著。所以本项目的备用模型，采用冷备份的方式。正常情况下，只有主模型上线并提供服务，备用模型作为冷备份存在。

# 2. nginx 流式网关服务

HeteroServe 系统对客户端的 HTTP 访问，采用 nginx 反向代理后端 vLLM 部署模型的方式。这样可以统一客户端请求入口，执行流式转发，未来进行扩展时，方便进行负载均衡和流量限制。我们将 Nginx 单独作为一个服务容器，接受客户端 HTTP 请求，然后转发到后端 vLLM 部署的大模型服务器，执行推理计算。

配置文件中，配置了两个 Nginx 服务，nginx-main 和 nginx-backup，这里的主备 nginx 服务不是为了高可用， Nginx 的服务要依赖模型服务的启动，为了将依赖关系分开，而将 Nginx 也分开为主备两个不同的服务。

nginx 详细的配置说明, 参考 [11-Nginx-Streaming-Gateway](/docs/11-Nginx-Streaming-Gateway.md)
nginx 完整的配置文件，参考[nginx.conf](/deploy/nginx.conf)
配置文件的详细解析，参考 [16-nginx.conf 配置解析](/docs/analysis%20&%20research/16-nginx.conf%20配置解析.md)

另外，Prometheus 在抓取指标数据的时候，将 nginx 视为一个单独的数据源，以监测和分析 nginx 流式网关的运行状态。Prometheus 不会直接访问 nginx 服务，而是访问 nginx-exporter 服务，在统一接口 /metrics 处抓取 Prometheus 标准格式的指标数据。
# 3. Prometheus  + DCGM-Exporter + Grafana 可视化监测服务

为了让 HeteroServe 推理服务平台能够稳定运行，我们还为模型配备了一套可视化监测服务。监测服务上主要有三个组件，`prometheus`, `grafana`, `dcgm-exporter`

`prometheus`  负责从各个目标处抓取指标数据并存储。prometheus 目标数据源分为两部分，一部分是 vLLM 部署框架提供的 /metrics 抓取点，一部分是 DCGM-Exporter 经过数据转换，提供的 GPU 指标数据抓取点。关于 Prometheus 工作原理的详细讨论，详见 [17-Prometheus](/docs/analysis%20&%20research/17-Prometheus.md)

`dcgm-exporter` 负责将采集的 GPU 性能数据和运行数据转换为 Prometheus 标准格式的指标数据，并且暴露在 Prometheus 统一抓取的 HTTP 接口 /metrics 处。 `DCGM` 负责真正调用 NVIDIA 驱动，获取 GPU 的真实运行数据和状态数据。 NVIDIA 提供的镜像中包含了 DCGM 库，如果没有配置远程 DCGM服务，那就默认启用镜像中内嵌的DCGM。所以通常启动 `dcgm-exporter` 服务就足够了。关于 DCGM/DCGM-Exporter的详细讨论，参考 [18-DCGM & DCGM-Exporter](/docs/analysis%20&%20research/18-DCGM%20&%20DCGM-Exporter.md)

`grafana` 负责访问 prometheus，通过 PromQL 读取指标数据，进行分析统计和展示。关于 grafana的详细讨论， 参考[19-Grafana](/docs/analysis%20&%20research/19-Grafana.md)

Prometheus 与 DCGM-Exporter 详细的指标体系，数据获取，架构设计，以及 Grafana 看板 Panel 的详细设置与 Prometheus 的 PromQL 交互， 参考 [12-Prometheus+DCGM](/docs/12-Prometheus+DCGM.md) 与 [13-Grafana-Dashboard](/docs/13-Grafana-Dashboad.md)

# 4. Compose 网络中的服务架构

docker compose up 启动整个编排服务之后，compose 网络中的服务架构如下：

```
┌─────────────────────────────────────────────────────┐
│                     Client                          │
└───────────────────────┬─────────────────────────────┘
                        │ HTTPS
                        ▼
┌─────────────────────────────────────────────────────┐
│         Nginx Gateway (流式 / 限流 / 路由)            │
└───────────┬───────────────────┬─────────────────────┘
            │                   │
   ┌────────▼────────┐  ┌──────▼─────────┐
   │  vLLM Main      │  │  vLLM Backup   │
   │  Qwen3-32B-AWQ  │  │  Qwen3-14B-FP16│
   │  PP=3           │  │  TP=2          │
   │  3×2080Ti 22GB  │  │  2×2080Ti 22GB │
   └────────┬────────┘  └──────┬─────────┘
            │                   │
   ┌────────▼────────────────────▼─────────────────┐
   │       Prometheus + DCGM Exporter              │
   └────────────────────┬──────────────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │     Grafana      │
              └──────────────────┘
```

# 5.  一键启动

我们将 `docker compose up` 启动 compose 编排容器的命令写入到一个启动脚本中 launch.sh，以便加入前后一些处理，让启动过程更加安全可靠。完整的启动脚本，详见 [launch.sh](/launch.sh) 核心启动语句

```bash
docker compose --profile main --profile backup down
echo "Starting HeteroServe with profile: $PROFILE"
docker compose --profile $PROFILE up -d --build
```

首先将 main 和 backup 的模型确认关闭，这是一个防御性操作。然后启动 `docker compose up` ，正常情况下，我们只启动主模型和一些相关服务。

启动后我们能看到 compose 网络中的各正在运行的容器服务

![](/docs/assets/docker-compose-assets/151fcfbe91e60f9324ccd6742c8a8fc1.png)

可以看到目前启动起来的服务, 包括:

| Service        | Port |
| -------------- | ---- |
| dcgm-exporter  | 9400 |
| grafanan       | 3000 |
| nginx-exporter | 80   |
| prometheus     | 9090 |
| vllm-main      | 8000 |
当需要停止服务的时候，我们也提供了安全退出的停止脚本, 详见 [stop.sh](/stop.sh)


