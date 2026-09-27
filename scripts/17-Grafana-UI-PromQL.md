我们在 Grafana UI 中，配置 Panel 进行如下查询，显示内容为：

## 第一行: 吞吐与延迟

第一行分为 5个 Panel。
Panel 1 是吞吐量，分为 Prompt 吞吐 和 Generation 吞吐两个 Query. 

```PromQL
# Panel 1: Query A: Prompt 吞吐
sum by (job, model_name)(
	rate(vllm:prompt_tokens_total[1m])
)

# Panel 1: Query B: Generation 吞吐
sum by (job, model_name) (
	rate(vllm:generation_tokens_total[1m])
)
```

Panel 2，Panel 3，Panel 4 分别是 TTFT , TPOT, 和 E2E 的 P95 / P99 

```PromQL
# Panel 2: TTFT P95/P99
histogram_quantile(
	0.99,
	sum by (le, job, model_name)(
		rate(vllm:time_to_first_token_seconds_bucket[1m])
	)
)
histogram_quantile(
	0.95,
	sum by (le, job, model_name)(
		rate(vllm:time_to_first_token_seconds_bucket[1m])
	)
)

# Panel 3：TPOT P99 / P95
histogram_quantile(
  0.99,
  sum by (le, job, model_name) (
    rate(vllm:request_time_per_output_token_seconds_bucket[1m])
  )
)
histogram_quantile(
  0.95,
  sum by (le, job, model_name) (
    rate(vllm:request_time_per_output_token_seconds_bucket[1m])
  )
)

# Panel 4: E2E P99/P95
histogram_quantile(
  0.99,
  sum by (le, job, model_name) (
    rate(vllm:e2e_request_latency_seconds_bucket[1m])
  )
)
histogram_quantile(
  0.95,
  sum by (le, job, model_name) (
    rate(vllm:e2e_request_latency_seconds_bucket[1m])
  )
)
```

Panel 5 vllm 请求处理速率
```PromQL
# Panel 5: 请求处理速率
sum by (job, model_name) (
  rate(vllm:request_success_total{job="vllm-active"}[$__rate_interval])
)
```
## 第二行：Scheduler 与 KV Cache

第二行分为 4 个 Panel, KV Cache 使用率，Running/Waiting 请求数, Preemption, Prefix Cache 命中率。 

```PromQL
# Panel 1：KV Cache 使用率
max by (job, model_name) (
  vllm:kv_cache_usage_perc{job="vllm-active"}
)
```

```PromQL
# Panel 2: Running / Waiting 请求数
# Running
sum by (job, model_name) (
  vllm:num_requests_running{job="vllm-active"}
)
# Waiting
sum by (job, model_name) (
  vllm:num_requests_waiting{job="vllm-active"}
)
```

```PromQL
# Panel 3: Preemption
sum by (job, model_name) (
  increase(vllm:num_preemptions_total{job="vllm-active"}[5m])
)
```

```PromQL
sum by (job, model_name) (
  rate(vllm:prefix_cache_hits_total{job="vllm-active"}[5m])
)
/
clamp_min(
  sum by (job, model_name) (
    rate(vllm:prefix_cache_queries_total{job="vllm-active"}[5m])
  ),
  1e-9
)
```

我们再提供第 5 个 Panel，可以进一步分析排队原因

```PromQL
# Panel 5: reason
sum by (job, model_name, reason) (
  vllm:num_requests_waiting_by_reason{job="vllm-active"}
)
```


## 第三行: GPU 健康 (DCGM)

第三行反映 GPU 的健康程度，分为 5 个 Panel, GPU 利用率，显存使用率，GPU 温度， GPU 功耗，DCGM 抓取状态。

```PromQL
# Panel 1: GPU 利用率
DCGM_FI_DEV_GPU_UTIL{job="dcgm-exporter"}

```

```PromQL
# Panel 2: 显存利用率
DCGM_FI_DEV_FB_USED / DCGM_FI_DEV_FB_TOTAL 
```

```PromQL
# Panel 3: GPU 温度
DCGM_FI_DEV_FB_USED{job="dcgm-exporter"}
/
clamp_min(
  DCGM_FI_DEV_FB_USED{job="dcgm-exporter"}
  +
  DCGM_FI_DEV_FB_FREE{job="dcgm-exporter"},
  1
)
```

```PromQL
Panel 4: 功耗
DCGM_FI_DEV_POWER_USAGE{job="dcgm-exporter"}
```

```PromQL
# Panel 5: DCGM 抓取状态
up{job="dcgm-exporter"}
```


## 第四行: Nginx 业务层

第四行，Nginx 业务层面的数据展示，分为 5 个 Panel,  Nignx 请求总数，请求速率，HTTP成功率， HTTP 5xx 错误率， Nginx 连接状态。

```PromQL
# Panel 1: Nginx 请求总数 和 Panel 2: 请求速率
sum(nginx_http_requests_total{job="nginx"})
sum(
  rate(nginx_http_requests_total{job="nginx"}[5m])
)
```

```PromQL
# Panel 3: HTTP 成功率
sum(
  rate(http_requests_total{
    job="vllm-active",
    handler=~"/v1/(chat/)?completions",
    status=~"2.."
  }[5m])
)
/
sum(
  rate(http_requests_total{
    job="vllm-active",
    handler=~"/v1/(chat/)?completions"
  }[5m])
)
```

```PromQL 
# Panel 4: HTTP 5xx 错误率
(
  sum(
    rate(http_requests_total{
      job="vllm-active",
      handler=~"/v1/(chat/)?completions",
      status=~"5.."
    }[5m])
  )
  or vector(0)
)
/
clamp_min(
  sum(
    rate(http_requests_total{
      job="vllm-active",
      handler=~"/v1/(chat/)?completions"
    }[5m])
  ),
  1e-9
)
```

Nginx 的连接状态 Panel, 我们一共提供了 5 个 Queries

```PromQL
# Panel 5: Nginx 连接状态

# Query A
sum(nginx_connections_active{job="nginx"})

# Query B
sum(nginx_connections_reading{job="nginx"})

# Query C
sum(nginx_connections_writing{job="nginx"})

# Query D
sum(nginx_connections_waiting{job="nginx"})
```
