我们采用 vLLM 官方的 Benchmark 工具，对 Qwen3-32B-AWQ 进行 Benchmark，产生标准化性能数据。

我们使用的是 ShareGPT 数据集，从 HuggingFace 上下载数据集文件，`ShareGPT_V3_unfiltered_cleaned_split.json` 大约 642 MB。

```bash
wget https://huggingface.co/datasets/anon8231489123/ShareGPT_Vicuna_unfiltered/resolve/main/ShareGPT_V3_unfiltered_cleaned_split.json
```

然后，使用 `vllm bench serve` 跑标准化 Benchmark。(首先需要下载 `pip install vllm[bench]`)

我们使用脚本 [13-exp3-vllm_bench_run.sh](/scripts/13-exp3-vllm_bench_run.sh) 来启动 vllm bench。详细的参数，详见脚本内容。运行这个脚本的时候，我们需要对这个脚本传递4个参数，如下：

```bash
bash exp3-Benchmark.sh <local-model-path> <served-model-name> <port> <concurrency>
```

将模型路径`<local-model-path>` ，模型名字`<served-model-name>`，端口号`<port>` , 并发请求数 `<concurrency>` 作为参数，传递给测试脚本。

执行 benchmark 的时候。对模型处理并发请求数限制为4，16，64 时，分别各执行 500 次请求 prompt。vllm bench 工具会对每一个测试用例输出测试数据。完整的测试执行脚本，参考 [12-exp3-Benchmark.sh](/scripts/12-exp3-Benchmark.sh)

## Qwen3-32B-AWQ

| Qwen3-32B-AWQ / Maximum<br>concurrency requests | 4       | 16      | 64       |
| ----------------------------------------------- | ------- | ------- | -------- |
| Successful requests                             | 500     | 500     | 500      |
| Failed requests                                 | 0       | 0       | 0        |
| Benchmark duration (s)                          | 1207.34 | 454.13  | 287.40   |
| Total input tokens                              | 107437  | 107437  | 107437   |
| Total generated tokens                          | 109888  | 109781  | 109635   |
| Request throughput (req/s)                      | 0.41    | 1.1     | 1.74     |
| Output token throughput (tok/s)                 | 91.02   | 241.74  | 381.48   |
| Peak output token throughput (tok/s)            | 105.00  | 353     | 768      |
| Peak concurrent requests                        | 7       | 20      | 70       |
| Total token throughput (tok/s)                  | 180     | 478.32  | 755.30   |
| Mean TTFT (ms)                                  | 381.57  | 531.38  | 1941.69  |
| Median TTFT (ms)                                | 243.17  | 351.02  | 831.12   |
| P99 TTFT (ms)                                   | 988.83  | 2354.55 | 16712.51 |
| Mean TPOT (ms)                                  | 41.93   | 62.14   | 175.64   |
| Median TPOT (ms)                                | 40.27   | 60.11   | 147.82   |
| P99 TPOT (ms)                                   | 63.51   | 111.02  | 827.87   |
| Mean ITL (ms)                                   | 41.91   | 61.44   | 145.49   |
| Median ITL (ms)                                 | 39.19   | 47.07   | 85.64    |
| P99 ITL (ms)                                    | 51.91   | 566.03  | 968.68   |
Qwen3-32B-AWQ 的测试数据详见，
最大并发为4，benchmark标准压测的原始测试数据，参见[qwen3-32b-awq_c4.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-awq_c4.json),  统计数据，参见[qwen3-32b-awq_c4.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-awq_c4.log).
最大并发为16，benchmark标准压测的原始测试数据，参见[qwen3-32b-awq_c16.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-awq_c16.json),  统计数据，参见[qwen3-32b-awq_c16.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-awq_c16.log).
最大并发为64，benchmark标准压测的原始测试数据，参见[qwen3-32b-awq_c64.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-awq_c64.json),  统计数据，参见[qwen3-32b-awq_c64.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-awq_c64.log).

Plot the metrics
![image_c4|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701181055.png)![qwen3-32b-awq_c16.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701181413.png)![qwen3-32b-awq_c64.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701181603.png)

## Qwen3-14B-FP16

| Qwen3-14B-FP16 / Maximum<br>concurrency requests | 4      | 16      | 64      |
| ------------------------------------------------ | ------ | ------- | ------- |
| Successful requests                              | 500    | 500     | 500     |
| Failed requests                                  | 0      | 0       | 0       |
| Benchmark duration (s)                           | 934    | 369.55  | 189.57  |
| Total input tokens                               | 107437 | 107437  | 107437  |
| Total generated tokens                           | 109697 | 109763  | 109761  |
| Request throughput (req/s)                       | 0.54   | 1.35    | 2.64    |
| Output token throughput (tok/s)                  | 117.42 | 297.02  | 579.01  |
| Peak output token throughput (tok/s)             | 132.00 | 384     | 910.00  |
| Peak concurrent requests                         | 8      | 21      | 72      |
| Total token throughput (tok/s)                   | 232.43 | 587.75  | 1145.76 |
| Mean TTFT (ms)                                   | 206.94 | 283.09  | 879.10  |
| Median TTFT (ms)                                 | 145.94 | 194.68  | 395.11  |
| P99 TTFT (ms)                                    | 489.06 | 1692.98 | 6865.28 |
| Mean TPOT (ms)                                   | 33.01  | 51.17   | 109.01  |
| Median TPOT (ms)                                 | 32.29  | 50.30   | 96.58   |
| P99 TPOT (ms)                                    | 44.39  | 76.28   | 403.00  |
| Mean ITL (ms)                                    | 32.89  | 50.63   | 94.58   |
| Median ITL (ms)                                  | 31.61  | 44.33   | 71.01   |
| P99 ITL (ms)                                     | 56.14  | 263.51  | 442.75  |
Qwen3-14B-FP16 的测试数据详见，
最大并发为4，benchmark标准压测的原始测试数据，参见[qwen3-14b-fp16_c4.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-14b-fp16_c4.json),  统计数据，参见[qwen3-14b-fp16_c4.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-14b-fp16_c4.log).
最大并发为16，benchmark标准压测的原始测试数据，参见[qwen3-14b-fp16_c16.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-14b-fp16_c16.json),  统计数据，参见[qwen3-14b-fp16_c16.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-14b-fp16_c16.log).
最大并发为64，benchmark标准压测的原始测试数据，参见[qwen3-14b-fp16_c64.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-14b-fp16_c64.json),  统计数据，参见[qwen3-14b-fp16_c64.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-14b-fp16_c64.log).

Plot the metrics
![qwen3-14b-fp16_c4.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701183815.png)![qwen3-14b-fp16_c16.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701183904.png)
![qwen3-14b-fp16_c64.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701184017.png)


## Qwen3-32B-GPTQ

| Qwen3-32B-GPTQ / Maximum<br>concurrency requests | 4       | 16      | 64       |
| ------------------------------------------------ | ------- | ------- | -------- |
| Successful requests                              | 500     | 500     | 500      |
| Failed requests                                  | 0       | 0       | 0        |
| Benchmark duration (s)                           | 1202.11 | 458.48  | 292.25   |
| Total input tokens                               | 107437  | 107437  | 107437   |
| Total generated tokens                           | 109888  | 109888  | 109821   |
| Request throughput (req/s)                       | 0.42    | 1.09    | 1.71     |
| Output token throughput (tok/s)                  | 91.41   | 239.68  | 375.77   |
| Peak output token throughput (tok/s)             | 108.00  | 352     | 764      |
| Peak concurrent requests                         | 7.00    | 20      | 71       |
| Total token throughput (tok/s)                   | 180.79  | 474.01  | 743.39   |
| Mean TTFT (ms)                                   | 384.73  | 545.25  | 2027.66  |
| Median TTFT (ms)                                 | 243.44  | 360.00  | 878.92   |
| P99 TTFT (ms)                                    | 1007.58 | 2386.34 | 17297.07 |
| Mean TPOT (ms)                                   | 41.77   | 62.48   | 177.59   |
| Median TPOT (ms)                                 | 40.08   | 60.57   | 150.34   |
| P99 TPOT (ms)                                    | 64.11   | 115.51  | 891.42   |
| Mean ITL (ms)                                    | 41.71   | 61.96   | 147.73   |
| Median ITL (ms)                                  | 38.92   | 47.36   | 87.13    |
| P99 ITL (ms)                                     | 52.58   | 576.29  | 1057.17  |
Qwen3-32B-GPTQ 的测试数据详见，
最大并发为4，benchmark标准压测的原始测试数据，参见[qwen3-32b-gptq_c4.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-gptq_c4.json),  统计数据，参见[qwen3-32b-gptq_c4.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-gptq_c4.log).
最大并发为16，benchmark标准压测的原始测试数据，参见[qwen3-32b-gptq_c16.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-gptq_c16.json),  统计数据，参见[qwen3-32b-gptq_c16.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-gptq_c16.log).
最大并发为64，benchmark标准压测的原始测试数据，参见[qwen3-32b-gptq_c64.json](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-gptq_c64.json),  统计数据，参见[qwen3-32b-gptq_c64.log](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/results/qwen3-32b-gptq_c64.log).

Plot the metrics
![qwen3-32b-gptq_c4.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701201136.png)![qwen3-32b-gptq_c16.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701201234.png)
![qwen3-32b-gptq_c64.log|345](/docs/assets/EXP3-assets/Pasted%20image%2020260701201344.png)


matplotlib 绘制的并发-性能曲线对比图如下：
![](/docs/assets/EXP2_assets/three_configs_comparison.png)


## 总结

|模型|并发|输出 tok/s|mean TTFT|p99 TTFT|mean TPOT|p99 TPOT|
|---|---|---|---|---|---|---|
|Qwen3-14B-FP16|4|117.4|207ms|489ms|33.0ms|44.4ms|
|Qwen3-14B-FP16|16|297.0|283ms|1693ms|51.2ms|76.3ms|
|Qwen3-14B-FP16|64|579.0|879ms|6865ms|109.0ms|403.0ms|
|Qwen3-32B-AWQ|4|91.0|382ms|989ms|41.9ms|63.5ms|
|Qwen3-32B-AWQ|16|241.7|531ms|2355ms|62.1ms|111.0ms|
|Qwen3-32B-AWQ|64|381.5|1942ms|16713ms|175.6ms|827.9ms|
|Qwen3-32B-GPTQ|4|91.4|385ms|1008ms|41.8ms|64.1ms|
|Qwen3-32B-GPTQ|16|239.7|545ms|2386ms|62.5ms|115.5ms|
|Qwen3-32B-GPTQ|64|375.8|2028ms|17297ms|177.6ms|891.4ms|

结论很明确：
1.  **Qwen3-14B-FP16 全面领先**：吞吐和延迟在所有并发下都是最好。相对 32B 量化模型，输出吞吐高约 **23%-54%**，mean TTFT 低约 **46%-57%**。追求线上交互体验：**Qwen3-14B-FP16 + c16**
2. **32B-AWQ 和 32B-GPTQ 性能几乎一样**：AWQ 在 c16/c64 略快一点，大概 **1%-2%**，尾延迟也略低，但差距很小。二者更适合按部署兼容性、显存、模型质量来选，不建议只按性能区分。
3. **c16 是最均衡的并发点**：相比 c4，吞吐提升约 **2.5-2.7 倍**，但延迟还没有失控。c64 虽然吞吐最高，但 p99 延迟恶化明显。
4. **c64 更像批处理场景**：32B 两个模型在 c64 下 p99 TTFT 已经到 **16.7-17.3 秒**，p99 TPOT 接近 **0.8-0.9 秒/token**，交互体验会很差。
5. 32B：优先 c16；c64 谨慎用于非交互批量任务**。

分析数据和结论详见：[qwen3_benchmark_analysis](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/qwen3_benchmark_analysis.md) 与 [qwen3_benchmark_summary](/logs%20&%20reports/06-EXP3-vllm_bench_benchmarks/qwen3_benchmark_summary.csv)

注意⚠️：以上分析仅仅针对性能，对模型质量与输出结果的好坏，在这个benchmark基础压测中无法评估。所以 Qwen-3-14B-FP16 的模型只有 140 亿参数，并且数据格式未经量化，所以性能表现更好。而 Qwen-3-32B-AWQ/GPTQ, 拥有 320亿参数，并且是量化模型，所以性能表现稍差，但是参数规模是14B 约 2.5倍，模型质量肯定高于14B模型。选择模型的时候，不能单一以性能考量，还要考虑效果和质量。

4B模型启动后，每张卡被占用～14GB显存，只有 3.84 GiB 的 KV Cache, 但是32B量化模型只有6.5 GiB 的显存占用，留有约11GB显存，理论上可以提供更多的并发处理能力。

benchmark 数据表明，32B量化模型，在 c16  的时候，综合表现最好。 c64 虽然系统整体吞吐量提高明显，但是 P99 TTFT 和 P99 TPOT 退化严重已经失控。所以 32B 量化模型最好选择 c16 的运行模式。

