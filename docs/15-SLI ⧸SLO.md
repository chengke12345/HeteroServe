SLI (Service Level Indicators) , 表示服务层面系统表现指标。SLO(Service Level Objectives)，表示在服务层面表现，目标达到什么样的水平。

根据 HeteroServe 目前的 Locust 的压测结果。系统在正常情况下稳定运行的性能目标为: 

| SLI          | 计算方式或含义            | SLO      |
| ------------ | ------------------ | -------- |
| 请求成功率        | 成功请求数 / 有效成功总数     | > 99%    |
| TTFT P99     | 首个输出 token, 延迟分位数  | < 1500ms |
| TPOT P99     | decode 阶段要求能够流畅生成  | < 80ms   |
| 请求错误率        | 5xx, 超时，OOM 请求占比   | < 0.1%   |
| 吞吐量          | tokens/s, 正常短，中对话。 | > 500    |
| KV Cache 利用率 | 至少留出 10% 的显存作为安全边际 | < 90%    |
| GPU Util     | GPU 利用率            | > 90%    |
| 并发容量         | P99 不恶化并发          | < 64     |
