# 1. Prometheus + DCGM 架构 

Prometheus 通常与其监测节点之间的关系就是一对多。在分布式情况下，Prometheus 通常单独一个监测节点，定期从各个服务节点上的 Exporter 拉取 Prometheus 格式的指标数据，然后添加标签并且存储在本地时序数据库 TSDB 中。整个架构可以用下面的架构图来表示。

![image|500](/docs/analysis%20&%20research/assets-Prometheus+DCGM+Grafana/Pasted%20image%2020260825095352.png)

当然，Prometheus 还可以拉取其他节点上的其他 Exporter 提供的指标数据，比如 vLLM, Node Exporter 等。只需要在 prometheus.yml 配置文件中，配置不同的 job 和 target 就可以了。

# 2. Prometheus + Grafana 架构

Grafana 是一个输出展示的服务，它本身就是一个Web服务，可以直接通过浏览器访问。通常它和 Prometheus 的关系是一对一，即 Grafana 将 Prometheus 服务器作为后端服务器，从它那里查询数据，然后组织和编排展示面板，提供给前端浏览器展示使用。它们之间关系可以用下图表示
![](/docs/analysis%20&%20research/assets-Prometheus+DCGM+Grafana/Pasted%20image%2020260825103125.png)
# 3. Grafana + 多 Prometheus 架构

除了上面一台 Grafana 连接一台集中式 Prometheus 的架构外，还可以一台 Grafana 连接多台 Prometheus 的架构。这种场景下，不同 Prometheus 节点监控多个不同的集群。
```
Grafana
├── Prometheus-生产集群
├── Prometheus-测试集群
└── Prometheus-GPU集群
```

这种情况下，在 Grafana 侧，每个 Dashboard 固定一个 Prometheus, 每个 Panel 单独选择数据源，可以创建数据源变量，让用户在 Dashboard 顶部切换集群。这样同一个 Dashboard 可以复用到不同集群。

如果要把多个集群数据汇总计算，比如所有集群的整体吞吐量，通常还需要引入 Thanos, Mimir 或 Prometheus Federation.

# 4. 多 Grafana + Prometheus 架构

通常，多台电脑，电视或浏览器展示同一个 Dashboard 时，只需要一个 Grafana 服务。

```
浏览器1 ─┐
浏览器2 ─┼→ 一个 Grafana → 一个 Prometheus
大屏幕  ─┘
```

Grafana 本身就是 Web 服务，可以同时服务多个浏览器。

多个Grafana 服务器节点，在大的集群下，也有应用场景，比如 Grafana 服务具有高可用性，用户较多时分担访问压力，进行负载均衡。在不同的地域部署，不同团队或租户的隔离。

这些 Grafana 可以对应同一个 Prometheus, 这就是多对一的关系。

```
Grafana-1 ─┐
Grafana-2 ─┼→ Prometheus
Grafana-3 ─┘
```

这种情况下，自动 provisioning 就很重要，即每个 Grafana 节点都有相同的 Prometheus 数据源，Dashboard Provider, Dashboard JSON, 警告规则。它们都有相同的配置文件，`prometheus-datasource.yml`, `provider.yml`, `heteroserve.json`, `alerting-rules.yml`。

多Grafana节点比较复杂，通常还需要负载均衡器，共享 MySQL/PostgreSQL 数据库。一致的插件版本，一致的密钥和环境变量，相同的 provisioning 文件，等等。这些是为了保证用户，权限，UI配置保持一致。

>多 Grafana 对一 Prometheus 是需要自动部署的典型场景之一；但即使只有一个 Grafana，为了容器重建、迁移和灾难恢复，也值得把配置文件化。

多 Grafana 的最主要使用场景是，<u>负载均衡</u> 和 <u>主动-主动的高可用副本</u>，

```
	            ┌→ Grafana-1 ─┐
用户→负载均衡器-> ｜→ Grafana-2 -|→ 同一个 Prometheus
                └→ Grafana-3 ─┘
                         ↓
                 共享 PostgreSQL/MySQL
```

这样，某 Grafana 故障时可以继续提供服务，在有大量用户访问时，可以实现负载均衡。只有在需要高可用或较大访问压力时，才把 Grafana 扩展成多个实例。

> 注意⚠️：多个 Grafana 对 一个 Prometheus 架构，基本上就是为了 Grafana 服务器的高可用性，以及需要负载均衡的环境。如果是为了让不同用户群体看到不同的监测面板，不用多个 Grafana 节点，只需要一个 Grafana，在里面创建不同的 Dashboard, 然后对不同用户进行 Dashboard 的权限划分就可以了。

# 5. 多 Grafana + 多 Prometheus

还有一种情况是，多对多的情况。这种情况本质上，是多套独立的 Grafana + Prometheus 架构。一般是下面这样的场景

```
开发环境一套 Grafana
测试环境一套 Grafana
生产环境一套 Grafana
```

这些 Grafana 相互独立，不是备份，也不做负载均衡，provisioning 只是保证它们使用相同的标准化看板。

>结论：普通情况下一个 Grafana 足够，多 Grafana 实例主要用于高可用，负载均衡，地域隔离，provisioning 用来保证所有实例的配置一致且可恢复。