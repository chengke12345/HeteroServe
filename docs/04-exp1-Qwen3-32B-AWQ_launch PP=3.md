主线模型上线，启动脚本，详见 [EXP1-Qwen3-32B-AWQ_launch.sh](/scripts/06-exp1-Qwen3-32B-AWQ_launch.sh)
启动参数解析如下：

| 参数                              | 作用            | 备注                              |
| ------------------------------- | ------------- | ------------------------------- |
| `CUDA_DEVICE_ORDER=PCI_BUS_ID`  | 按物理总线号编号 GPU  | 保证 rank↔槽位稳定，否则 rank 可能错配到 x4 槽 |
| `--tensor-parallel-size 1`      | 不做层内切分        | 每一层完整的在一张卡上                     |
| `--pipeline-parallel-size 3`    | 三卡流水线         | 规避 head 整除 + 无 NVLink 通信瓶颈      |
| `--quantization awq_marlin`     | Marlin 加载 AWQ | sm_75 可用路径                      |
| `--dtype float16`               | FP16 计算       | Turing 无高效 BF16                 |
| `--gpu-memory-utilization 0.90` | 每卡用 90% 显存    | 留 ~2GB 给运行时/碎片，过高易 OOM          |
| `--max-model-len 16384`         | 上下文上限         | 起步值，KV 实验再上探                    |
| `--max-num-seqs 64`             | 并发序列上限        | sm_75 并发有限，起步小，压测再调             |
| `--enable-prefix-caching`       | 前缀缓存          | RAG/多轮命中率高，省 prefill            |
| `--enable-chunked-prefill`      | 分块预填充         | 长 prompt 平滑首 token 延迟           |
| `--served-model-name`           | 模型名字          | 内部访问时使用的模型名字                    |
| `--host 0.0.0.0`                | 服务监听所有网络接口。   | 服务能从localhost外的其他设备访问。          |
| `--port` 8001                   | 端口号           | 请求模型服务的端口号。                     |

完整的启动日志，参见[exp1-Qwen3-32B-AWQ_launch.log](/logs%20&%20reports/04-EXP1-vllm_main_depoly/exp1-Qwen3-32B-AWQ_launch.log)

# 启动说明

启动信息中有几点信息，需要特别说明

![](/docs/assets/EXP1_assets/Pasted%20image%2020260621004703.png)

- Fragment 1: 使用最大的上下文长度为 16384个token，与我们脚本中设置的一样。

- Fragment 2: 模型在运行时转换为了 `awq_marlin`， 使用的是 Marlin Kernel。这是 vLLM 针对 AWQ 的量化模型，特别提供的加速kernel, 这里表明，我们确实能正常使用 Marlin Kernel 来为我们做推理加速。

- Fragment 3: 初始化 v1 引擎，使用Qwen3-32B-AWQ 模型。这里就证明了我们确实使用的是 V1 引擎。因此，配置后端算子的时候，我们是按照 V1 的 fallback 路径，选择和调用后端算子的。 

![](/docs/assets/EXP1_assets/Pasted%20image%2020260621010249.png)

- Fragment 4: 这里表明，有三个设备，分别是 rank0, rank1, rank2, 它们之间使用的后端通信是 NCCL 2.28.9

- Fragment 5: 我们使用的后端算子是 FlashInfer

- Fragment 6: 我们使用的是PP=3。 
	- Qwen3-32B-AWQ, 一共有 64 层，PP=3 就是把这 64 层分成 3 段，每段塞进一张卡，数据像流水线一样逐段往后传。所以 `PP=3, TP=1` 的完整含义是：**沿层的方向切 3 段，每段内部不再切**。world_size = PP × TP = 3 × 1 = 3，正好对应三张卡。
	- Hidden Layers 在三张卡之间不是均匀划分的，rank 0 划分了 21 层，rank 1 划分了 22 层，rank 2 划分了 21 层。
	- 三张卡都成功使用了 Marlin Kernel。 
  
 - Fragment 7:  三张卡都是 2080ti, 算力版本为 sm_75. 所以 FA2 在三张卡上都失效，FA2要求的sm ≥ 80. 
   根据vLLM使用 backends 的默认 fallback 顺序。FA2 失效后，从 FlashInfer, Triton-atten, Flex-atten 中选择了 FlashInfer.

![](/docs/assets/EXP1_assets/Pasted%20image%2020260621013045.png)

- Fragment 8: 加载权重文件，花费了3.02 秒

- Fragment 9: 首次启动的时候，vLLM 会对一些采用 AOT 编译模式的算子进行预编译，然后将编译好的二进制的kernel文件, 放在缓存区 `torch_compile_cache`中。下次就可以直接调用而不需要重复编译了。整个预编译阶段，耗时 26.88秒。

- Fragment 10: 可使用的 KV Cache 的大小为 10.85 GB.

- Fragment 11: 我们设置的GPU最大利用率是 90%， 由于有一些 profiling 的开销。达到同样的 KV Cache的效果，增大设置为 92.33%

- Fragment 12: KV Cache, 总共可以缓存 135440 token. 对于最大的上下文窗口的请求，可以同时并发处理8.27个。

- Fragment 13: 在三张卡上调用 backends 的时候， FlashInfer 都可以正常调用。

vLLM 启动完成后，通过命令 

```bash
watch -n 1 'free -h; echo "---"; nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv'
```

可以观察到
![](/docs/assets/EXP1_assets/Pasted%20image%2020260621115953.png)

vLLM 的 `gpu_memory_utilization`（默认 0.9）一次性预占显存。22528 MiB × 0.9 ≈ 20.3 GiB，实测三张在 0.88–0.89 之间，差的那点是 CUDA context、NCCL 通信 buffer 这些 nvidia-smi 算进 used 但不在 vLLM 预算里的开销。

vLLM 先 profile 出可用显存，把目标比例减去权重和峰值激活后，剩下的全部切成固定大小的 KV cache block 预分配掉，之后 PagedAttention 在这个池子里做页式分配。所以不管有没有请求，显存都会贴着 0.9 这条线，不会随负载涨落——涨落的是池子里被占用的 block 比例，而不是 nvidia-smi 看到的总量。

AWQ 4-bit 下 32B 权重总共约 16–18 GB，PP=3 切三段每卡才 5–6 GB，所以你看到的 ~19 GB 里**绝大部分是 KV cache**。这正是需要的：把显存尽量喂给 KV cache 换取更大的并发/上下文。

三张卡之间 ~4% 的差异（rank 0 19849 / rank 1 19229 / rank 2 20107）主要来自两点：各 PP stage 持有的层数和权重不完全均等（首段带 embedding、末段带 lm_head + sampler），以及每张卡 profile 出的可用余量略有不同，导致分到的 block 数不一样。

**`utilization.gpu` 全是 0%**
这是空载，没有请求在跑，SM 没有 kernel 在执行。这个字段是"过去采样窗口里有 kernel 在跑的时间占比"，不是算力利用率——打 benchmark 进去就会跳起来。而且 PP=3 下大概率**看不到三张同时 100%**：流水线 bubble 会让某些时刻只有部分 stage 在算，这是空泡开销。

**内存侧（无异常）**

`free` 599Mi 完全健康——Linux 的哲学是空闲内存就是浪费的内存。真正要看的是 `available 22Gi`。`buff/cache 23Gi` 基本就是从 NVMe 读 AWQ safetensors 时被 page cache 缓存下来的模型文件页，可回收，无害；`used 8.4Gi` 是 vLLM 的 Python 进程加 pinned host memory。swap 37Gi 几乎没动（600Ki），说明没有任何内存压力。

总结：这是干净的 ready 状态，显存按预期预占满，CPU 内存宽裕。可以正常进行推理工作。

# 启动信息与数据汇总

## 1. 配置 / 引擎决策

| 指标                     | 值                                | 来源行                                          |
| ---------------------- | -------------------------------- | -------------------------------------------- |
| vLLM 版本                | 0.21.0                           | banner / `Initializing a V1 LLM engine`      |
| 引擎                     | V1                               | `Initializing a V1 LLM engine`               |
| 模型                     | Qwen3-32B-AWQ (Qwen3ForCausalLM) | `non-default args` / `Resolved architecture` |
| dtype                  | float16                          | `dtype=torch.float16`                        |
| 量化 kernel              | awq_marlin → MarlinLinearKernel  | `awq_marlin.py:252` / `:420`（三 worker 全部命中）  |
| 并行                     | PP=3, TP=1                       | `pipeline_parallel_size=3`                   |
| max_model_len          | 16,384                           | `Using max model len 16384`                  |
| gpu_memory_utilization | 0.90                             | `non-default args`                           |
| max_num_seqs           | 64                               | `non-default args`                           |
| enforce_eager          | False                            | `enforce_eager=False`                        |
| compile 模式             | VLLM_COMPILE (mode=3)            | `compilation_config`                         |
| cudagraph 模式           | FULL_AND_PIECEWISE               | `cudagraph_mode`                             |
| 注意力后端                  | FLASHINFER                       | `cuda.py:372`                                |
| NCCL 版本                | 2.28.9                           | `pynccl.py:111`                              |

## 2. 资源 / 显存 / KV

| 指标               | 值                            | 来源行                                       | 备注                           |
| ---------------- | ---------------------------- | ----------------------------------------- | ---------------------------- |
| 单 rank 权重显存      | 6.49 GiB × 3                 | `Model loading took ... memory`（每 worker） | 全模型 ≈ 19.5 GiB；日志无总和行，需自行 ×3 |
| 层切分              | 21 / 22 / 21                 | `Hidden layers were unevenly partitioned` | 64 层，PP1 多扛 1 层              |
| KV cache 容量      | 135,440 tokens               | `kv_cache_utils.py:1710`                  | /                            |
| 最大并发             | 8.27x @ 16K                  | `kv_cache_utils.py:1711`                  | /                            |
| 可用 KV 显存         | 10.85 GiB                    | `gpu_worker.py:462`                       | /                            |
| CUDAGraph 显存池    | 0.24 GiB (实际) / 0.50 GiB (估) | `gpu_worker.py:621`                       | 从 KV 中扣除的部分                  |
| gpu_mem_util 等效值 | 0.90 ≈ 0.8767（扣 CUDAGraph 后） | `gpu_worker.py:477`                       | 拉平 EXP0 需提到 0.9233           |

## 3. 启动耗时（分阶段）

| 阶段                 | 耗时                    | 来源行                                  |
| ------------------ | --------------------- | ------------------------------------ |
| 权重加载               | 11.04 s               | `Loading weights took`               |
| 模型加载（含建结构）         | 5.01 s                | `Model loading took ... seconds`     |
| Dynamo bytecode 转换 | 6.59 s                | `backends.py:1148`                   |
| 编译 range (1,2048)  | 11.73 s               | `backends.py:393`                    |
| torch.compile 合计   | 26.88 s               | `monitor.py:53`                      |
| CUDAGraph capture  | 2 s                   | `Graph capturing finished in 2 secs` |
| profiling / warmup | 1.11 s                | `monitor.py:81`                      |
| engine init 合计     | 39.69 s（其中编译 27.27 s） | `core.py:299`                        |
| **总墙钟启动**          | **~73 s**             | 首尾时间戳                                |

## 4. CUDAGraph capture 验证

|项|值|来源行|
|---|---|---|
|PIECEWISE 图（prefill-decode 混合）|19 个 size，全部成功|`Capturing CUDA graphs (... PIECEWISE)`|
|FULL 图（decode）|11 个 size，全部成功|`Capturing CUDA graphs (decode, FULL)`|
|capture size 列表|1, 2, 4, 8, 16, 24, ..., 128|`cudagraph_capture_sizes`|

## 5. 解读注意点（分析时的干扰变量）

-  **6.49 GiB 是单卡值，不是总权重**——日志无"总权重显存"行，全模型需自行 ×3 (≈19.5 GiB)。
- 0.21.0 默认为 CUDAGraph 预留显存（实占 0.24 GiB），从 KV 中扣除。 做 eager vs compile 吞吐对比时，两组 KV 容量不等是干扰变量： 需在 compile 组将 `--gpu-memory-utilization` 提到 0.9233 对齐，或在分析中明确标注 KV 容量差异并将请求长度控制在远低于 KV 上限。
- **3.02s 权重加载是热盘（page cache 命中）**——EXP0 冷盘为 11.04s。 启动耗时对比必须区分冷/热盘（冷启动前 `echo 3 > /proc/sys/vm/drop_caches`，或统一测热启动）。 torch.compile 的 ~27s 已落盘缓存（`torch_compile_cache/`），下次同配置启动会大幅缩短。
-  **采样参数被模型 `generation_config.json` 覆盖**（temp=0.6, top_k=20, top_p=0.95）—— benchmark 时须在请求中显式固定采样参数（或用贪心 temp=0），否则随机性会破坏 latency 可复现性。

# 冒烟测试

主线模型启动完成后，我对其进行 <u>单个服务访问的测试</u> 和 <u>流式访问测试</u>

单个服务访问测试，执行脚本 [07-exp1-Qwen3-32B-AWQ_single_test.sh](/scripts/07-exp1-Qwen3-32B-AWQ_single_test.sh)
脚本执行的结果日志，参考 [exp1-Qwen3-32B-AWQ_single_test.log](/logs%20&%20reports/04-EXP1-vllm_main_depoly/exp1-Qwen3-32B-AWQ_single_test.log)

流式测试，执行脚本参考 [08-exp1-Qwen3-32B-AWQ_stream_test.sh](/scripts/08-exp1-Qwen3-32B-AWQ_stream_test.sh)
流式测试的结果日志，参考 [exp1-Qwen3-32B-AWQ_stream_test.log](/logs%20&%20reports/04-EXP1-vllm_main_depoly/exp1-Qwen3-32B-AWQ_stream_test.log)

测试结果，正常服务访问，和流式访问，都能正确执行。并且通过服务端的日志，可以看出，流式访问时，推理速度平均是 27 tok/s。

![](/docs/assets/EXP1_assets/Pasted%20image%2020260621143633.png)


# 结论
 
使用 vLLM 0.21.0 部署框架，在 sm_75 (Turing) + FlashInfer + PP=3 组合下，部署大模型 Qwen3-32B-AWQ,  torch.compile 与 CUDAGraph（PIECEWISE + FULL）capture 均成功，无回退、无报错。 主模型顺利上线。
