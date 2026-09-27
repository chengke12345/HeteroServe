主模型顺利上线之后。为了评估主模型在硬件上运行情况。引入对照组，进行量化对比实验。在关键的系统性能指标上进行对比分析，例如核心的延迟和响应数据。

除了主模型 Qwen3-32B-AWQ 之外, 我们还引入了 Qwen3-14B-FP16 完整版，以 TP = 2 的并行策略部署和运行。 我们还引入了 Qwen3-32B 的另一个量化版本，Qwen3-32B-GPTQ-Int4, 以 PP = 3 的并行策略部署和运行。

对比三个模型的 TTFT(Time To First Token), TPOT(Time Per Output Token), TPUT(Throughput), weights(权重显存)，等指标，并对它们进行统计对比 (P50/P99等)。

## 1. 模型启动

- 主模型的启动脚本，详见 [06-exp1-Qwen3-32B-AWQ_launch.sh](/scripts/06-exp1-Qwen3-32B-AWQ_launch.sh)
- Qwen3-14B-FP16 的启动脚本，详见[09-exp2-Qwen3-14B-FP16_launch.sh](/scripts/09-exp2-Qwen3-14B-FP16_launch.sh) . 注意，这个模型启动时，需要设置 `--tensor-parallel-size=2` 并且需要绑定设备，`export CUDA_VISIBLE_DEVICES=0,1`。
- Qwen3-32B-GPTQ-Int4 的启动脚本，详见 [10-exp2-Qwen3-32B-GPTQ-Int4_launch.sh](/scripts/10-exp2-Qwen3-32B-GPTQ_launch.sh). 注意，这个量化模型启动的时候，需要设置 `--pipeline-parallel-size 3`. 同时，需要把 vLLM 使用的 Marlin Kernel 改为 GPTQ, 即 `--quantization gptq_marlin`.

三个模型的基础启动数据对比如下：

| 模型                                                      | Qwen3-32B-AWQ | Qwen3-14B-FP16 | Qwen3-32B-GPTQ |
| ------------------------------------------------------- | ------------- | -------------- | -------------- |
| 并行                                                      | pp = 3        | TP = 2         | PP = 3         |
| GPU数                                                    | 3             | 2              | 3              |
| 注意力后端算子                                                 | FlashInfer    | FlashInfer     | FlashInfer     |
| Marlin Kernel                                           | awq_marlin    | None(非量化模型)    | gptq_marlin    |
| 权重显存/卡(GiB)                                             | 6.49          | 13.88          | 6.45           |
| 权重加载时间(s)                                               | 11.15         | 23.76          | 11.24          |
| 模型加载时间(s)                                               | 13.16         | 24.12          | 11.63          |
| profiling/warmup(s)                                     | 1.11          | 1.41           | 1.12           |
| init engine(profile, create <br>kv cache, warmup model) | 39.69         | 46.02          | 40.05          |
| KV Cache 大小(tokens)                                     | 135440        | 50304          | 135904         |
| Available KV Cache Mem GiB                              | 10.85         | 3.84           | 10.89          |
| 最大并发                                                    | 8.27x @16k    | 3.07x @16k     | 8.29x @16k     |
| 总墙钟启动(s)                                                | ~73           | ~88            | ~71            |

详细的启动日志，参考如下：
Qwen3-32B-AWQ 的详细启动日志，参考 [Qwen3-32B-AWQ_latency_launch.log](/logs%20&%20reports/04-EXP1-vllm_main_depoly/exp1-Qwen3-32B-AWQ_launch.log)
Qwen3-14B-FP16 的详细启动日志，参考 [Qwen3-14B- FP16_latency_launch.log](/logs%20&%20reports/05-EXP2-three_models_comparison/exp2-Qwen3-14B-FP16_launch.log)
Qwen3-32B-GPTQ 的详细启动日志，参考 [Qwen3-32B-GPTQ_latency_launch.log](/logs%20&%20reports/05-EXP2-three_models_comparison/exp2-Qwen3-32B-GPTQ_launch.log)

## 2. 性能测试

性能测试使用流式访问，获取以下指标，对比三个模型：
- TTFT(Time to First Token)，首次获取 token 响应时间，。
- TPOT(Time Per Ouput Token)，Decode阶段每个 Token 输出时间。
- TPUT(Throughput)，吞吐量。
- 总 token 数， tok。
对数据进行统计分析，包括 TTFT 的 50百分位, TPOT 的 50 百分位，平均吞吐量等等。

测试采用的提示次是固定 prompt 集，5组短对话，5组长对话，5组长prompt。为了让模型输出的token 不致于过长而影响整个测试。我们将模型token输出长度，限制在256个字符。

详细的测试脚本，参考[11-exp2-Three-Comparison-bench-latency.py](/scripts/11-exp2-Three-Comparison-bench_latency.py)

性能测试访问方式是流式访问，模型端一个 token 一个 token 的产生并立马推送，而程序端是一个惰性生成器，收到一个 token 就立马处理，而不是收集完所有的输出之后再处理。这样可以准确的测得 TTFT 与 TPOT。然后我们可以测得 50 百分位的 TTFP，TPOT，TPUT。

我们会对 Qwen3-14B-FP16, Qwen3-32B-AWQ, Qwen3-32B-GPTQ, 对三个模型分别执行相同的测试脚本。

```bash
python bench_latency.py --base "http://localhost:8001" --model "qwen3-32b-awq" --out "EXP2-Qwen3-32B-AWQ_run.json"

python bench_latency.py --base "http://localhost:8002" --model "qwen3-14b-fp16" --out "EXP2-Qwen3-14B-FP16_run.json"

python bench_latency.py --base "http://localhost:8003" --model "qwen3-32b-gptq" --out "EXP2-Qwen3-32B-GPTQ_run.json"
```

## 3. 测试结果

Qwen3-32B-AWQ, Qwen3-14B-FP16,  Qwen3-32B-GPTQ, 三个模型，执行同一个测试脚本。每次更换模型，重启 vLLM 服务，重新运行一遍测试用例，获得测试数据。

测试脚本详见[11-exp2-Three-Comparison-bench-latency.py](/scripts/11-exp2-Three-Comparison-bench_latency.py)

得到的测试结果汇总如下：

| 模型/指标          | TTFT(s) | TPOT(s) | TPUT(tk/s) | 权重显存(GiB/卡) | 最大并发       |
| -------------- | ------- | ------- | ---------- | ----------- | ---------- |
| Qwen3-32B-AWQ  | 0.079   | 0.036   | 27.12      | 6.49        | 8.27x @16k |
| Qwen3-14B-FP16 | 0.055   | 0.028   | 35.29      | 13.88       | 3.07x @16K |
| Qwen3-32B-GPTQ | 0.080   | 0.036   | 27.31      | 6.45        | 8.29x @16k |

以上是经过统计计算的 TTFT P50, TPOT P50, TPUT P50 数据。
全部完整的测试数据，请参看在各个模型上测试输出的数据文件(json)

对Qwen3-32B-AWQ 模型，运行测试脚本后，得到的测试数据，详见[exp2-Qwen3-32B-AWQ_run.json](/logs%20&%20reports/05-EXP2-three_models_comparison/exp2-Qwen3-32B-AWQ_run.json)
对Qwen3-14B-FP16 模型，运行测试脚本后，得到的测试数据，详见[EXP2-Qwen3-14B- FP16_run.json](/logs%20&%20reports/05-EXP2-three_models_comparison/exp2-Qwen3-14B-FP16_run.json)
对Qwen3-32B-GPTQ 模型，运行测试脚本后，得到的测试数据，详见[EXP2-Qwen3-32B-GPTQ_run.json](/logs%20&%20reports/05-EXP2-three_models_comparison/exp2-Qwen3-32B-GPTQ_run.json)

## 4. 结论

Qwen3-32B-AWQ, Qwen3-14B-FP16, Qwen3-32B-GPTQ 三个模型是相同架构的模型。

两个量化模型的推理性能，比较接近。AWQ 和 GPTQ 都采用的是 PP=3 的 GPU 并行部署方式，首个 token 产生的时间都大约为 0.08s, 推理时产生每个 token 平均用时为 0.036s。模型推理过程中的吞吐量约为 27 tokens/s。由于它们是量化版模型，它们的权重显存，大约 6.5GiB /卡，共 ～20GB。因此，留出了大量的 KV Cache，大约 11 GiB/卡。

完整版 FP16 模型 Qwen3-14B-FP16, 采用 FP16 完整数据格式，TP=2 并行方式。它首次产生Token的时间更短，约 0.055s. 推理速度也更快，产生一个 token 平均用时为 0.028。吞吐量也更大，达到 35 tokens/s。由于这是完整版模型，没有量化版模型的量化与反量化的开销，它的推理性能在速度和吞吐量上表现更好。

但是，它占用的权重显存就达到了 ～14 GiB / 卡，总共 ~28 GiB(双卡). 模型权重没有经过量化，对显存的占用就会大很多。留给 KV Cache 的缓存容量只有 3.84 GiB/卡。因此，它的并发性能远低于量化模型。3.07x @16k VS 8.29x @16K , 即在最大上下文窗口下，14B 模型最多可以同时处理3个请求，而 32B 的两个量化模型都能同时处理约 8.3 个请求。如果并发数量小，那多个请求的时候，造成的推理等待时间，反而会更长。

>注意⚠️，这是根据 KV Cache 容量以及窗口大小的设定，估计的同时处理能力，并不是大模型能够并发处理的真实能力。因为，任务不可能每个都拉满 16K, KV Cache的大小也是动态变化的。真实的并发处理能力，需要通过后期的 Locust 在不同场景下，根据不同类型的任务，详细评测。

这还只是一个 14B 的模型，如果使用 Qwen3-32B 完整版模型，总共需要大约 64GiB ～ 66GiB 的权重显存。加上 KV Cache, 将需要更大的显存空间。

因此，Qwen3-32B 的量化版是最佳选择，代价就是会损失一部分数据精度，但是 vLLM 采用了 Marlin Kernel，对 AWQ 量化版本的反量化和推理速度上都进行了优化。Qwen3-32B-AWQ 是目前硬件条件下的最佳选择。