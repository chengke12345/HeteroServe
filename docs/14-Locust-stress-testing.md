Locust 是基于 Python 的开源性能与压力测试工具，能模拟多用户并发请求推理服务。项目使用 Locust 对 HeteroServe 系统进行压力测试。Locust 压测工具的详细讨论，参考[Locust 压力测试](/docs/analysis%20&%20research/21-Locust%20压力测试.md)

---
# 1.  Locust 压测设计

我们设计了三类场景做压测，分别是短对话，RAG 长上下文，推理长生成场景。

| 场景  | 名称                 | 描述            | 特征          | 压测重点               |
| --- | ------------------ | ------------- | ----------- | ------------------ |
| 场景A | chat_short         | 短对话，高并发       | 短prompt+短输出 | 吞吐上限，排队延迟          |
| 场景B | rag_long_context   | RAG 长上下文      | 长prompt+中输出 | prefill成本, cache命中 |
| 场景C | reasoning_thinking | 长生成(thinking) | 短prompt+长输出 | TPOT稳定性, decode吞吐  |


---
## 场景A：chat_short

短对话场景下，设定一个短 prompt 的字符串列表。Locust 每次从中列表随机选取一个字符串作为 prompt，发送给LLM。一个模拟任务执行完成后，随机间隔 0.5～2 秒，循环进行下一次请求。

场景A是一个短对话，高并发场景，我们并发 50 个用户。起始阶段，以每秒 5 个的速度创建新用户，整个场景总共运行 10 分钟。

注意 vLLM 中的 `max-num-seqs` 参数, 它是 vLLM 同时处理的最大并发请求数，如果有更多的推理请求到达，就要加入队列排队。在场景A下，我们将 `max-num-seqs` 的值分别设置为 8,  16，32， 64。以测试吞吐上限和排队延迟情况。

Locust 测试结果数据，存储在文件 scene_A.html 中

---
## 场景B：RAG Long Context

RAG 长上下文场景。首先，从问题列表 RAG_QUESTIONS 中随机抽取一个问题，
然后我们用长文档列表 RAG_DOCUMENTS 中随机抽取两个不重复的长文本，模拟 RAG 检索返回的长文本结果。1 个 RAG_QUESTIONS 元素 与 2 个 RAG_DOCUMENTS 元素组合成一个长 prompt 再发送给 LLM 进行推理。

这种场景下，我们模拟 20 个并发用户，起始阶段每秒创建 2 个新用户，每个用户用上面的方式模拟长 RAG 上下文的请求方式，循环请求 LLM 推理服务。

该场景下我们设置 vLLM 参数 `max-num-seqs`分别设置为 8，16， 32，64，以观察 RAG 长文本场景下，排队与不排队的并发处理情况。

Locust 测试结果数据，存储在文件 scene_B.html 中。

---
## 场景C：Reasoning Thinking

推理场景下，模拟生成长文本。在 MATH_PROBLEMS 中随机挑选一个数学问题作为短 prompt 输入，推理求解数学问题的过程为长文本推理输出。

我们模拟 10 个并发用户，起始阶段每秒创建 1 个新用户，用上面的方式请求 LLM 的推理服务。

该场景下我们设置 vLLM 参数 `max-num-seqs`分别设置为 8， 16，32， 64 以观察 RAG 长文本场景下，排队与不排队的并发处理情况。

---
完整的 Locust 测试逻辑，详见 Locust 测试脚本 [locustfile.py](/scripts/18-locustfile.py)
完整测试流程，详见 Locust 压测命令脚本 [locust.sh](/locust.sh)

# 2. Locust 压测结果

运行 Locust 压测命令脚本，执行测试脚本 `locustfile.py`, 在指定的目录下，我们会得到 Locust 测试输出的 HTML 压测结果数据报告。同时因为使用了 Promtheus + DCGM + Grafana 的可视化监测架构，在 Grafana 面板上，我们也能得到 LLM 在推理服务层面的性能表现。 

Locust 输出的压测性能报告

| 场景 /并发 | 8                                                                                  | 16                                                                                   | 32                                                                                   | 64                                                                                   |
| ------ | ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| 场景A    | [scene_A_50u_8.html](/logs%20&%20reports/08-locust_report/scene_A/scene_A_50u_8.html) | [scene_A_50u_16.html](/logs%20&%20reports/08-locust_report/scene_A/scene_A_50u_16.html) | [scene_A_50u_32.html](/logs%20&%20reports/08-locust_report/scene_A/scene_A_50u_32.html) | [scene_A_50u_64.html](/logs%20&%20reports/08-locust_report/scene_A/scene_A_50u_64.html) |
| 场景B    | [scene_B_20u_8.html](/logs%20&%20reports/08-locust_report/scene_B/scene_B_20u_8.html) | [scene_B_20u_16.html](/logs%20&%20reports/08-locust_report/scene_B/scene_B_20u_16.html) | [scene_B_20u_32.html](/logs%20&%20reports/08-locust_report/scene_B/scene_B_20u_32.html) | [scene_B_20u_64.html](/logs%20&%20reports/08-locust_report/scene_B/scene_B_20u_64.html) |
| 场景C    | [scene_C_10u_8.html](/logs%20&%20reports/08-locust_report/scene_C/scene_C_10u_8.html) | [scene_C_10u_16.html](/logs%20&%20reports/08-locust_report/scene_C/scene_C_10u_16.html) | [scene_C_10u_32.html](/logs%20&%20reports/08-locust_report/scene_C/scene_C_10u_32.html) | [scene_C_10u_64.html](/logs%20&%20reports/08-locust_report/scene_C/scene_C_10u_64.html) |

Locust 输出具体的 HTML 性能报告如下：
## 场景A

LLM 并发数分别为 8， 16，32，64 时，场景 A下， Locust 压测输出报告 
max-num-seqs = 8 / 16
![scene_A_u50_8|350](/logs%20&%20reports/08-locust_report/scene_A/Pasted%20image%2020260908205512.png)![scene_A_u50_16|350](/logs%20&%20reports/08-locust_report/scene_A/Pasted%20image%2020260908205649.png)

max-num-seqs = 32 / 64
![scene_A_50u_32|350](/logs%20&%20reports/08-locust_report/scene_A/Pasted%20image%2020260908195022.png)![scene_A_50u_64|350](/logs%20&%20reports/08-locust_report/scene_A/Pasted%20image%2020260908222704.png)


## 场景 B：

max-num-seqs = 8 / 16
![scene_B_u20_8|350](/logs%20&%20reports/08-locust_report/scene_B/Pasted%20image%2020260908210025.png)![scene_B_20u_16|350](/logs%20&%20reports/08-locust_report/scene_B/Pasted%20image%2020260908210342.png) 

max-num-seqs = 32 / 64
![scene_B_u20_32|350](/logs%20&%20reports/08-locust_report/scene_B/Pasted%20image%2020260908210604.png)![scene_B_u20_64|350](/logs%20&%20reports/08-locust_report/scene_B/Pasted%20image%2020260908222836.png)

## 场景 C

max-num-seqs = 16 / 32
![scene_C_u50_8|350](/logs%20&%20reports/08-locust_report/scene_C/Pasted%20image%2020260908211238.png)![scene_C_10u_16|350](/logs%20&%20reports/08-locust_report/scene_C/Pasted%20image%2020260908211450.png)

max-num-seqs = 32 / 64
![scene_C_10u_32|350](/logs%20&%20reports/08-locust_report/scene_C/Pasted%20image%2020260908211722.png)![scene_C_10u_64|350](/logs%20&%20reports/08-locust_report/scene_C/Pasted%20image%2020260908223026.png)

# 3. Grafana 面板指标时序图

Grafana 面板展现出来的指标数据，是在同一个 LLM 推理服务下，场景 A，场景 B，场景 C 依次执行，每个场景执行10分钟。通过 Grafana 面板数据，我们可以看出三种场景下，不同性能指标的时序走势图。

max-num-seqs = 8
![](/logs%20&%20reports/08-locust_report/grafana/Pasted%20image%2020260908204315.png)

max-num-seqs = 16
![grafana_16](/logs%20&%20reports/08-locust_report/grafana/Pasted%20image%2020260908113517.png)

max-num-seq = 32
![](/logs%20&%20reports/08-locust_report/grafana/Pasted%20image%2020260908191636.png)

max-num-seqs = 64
![](/logs%20&%20reports/08-locust_report/grafana/Pasted%20image%2020260908222025.png)


# 4. Locust / Grafana 测试结果分析 

## ▪︎ 局部分析(max-num-seqs = 16)

LLM 并发上限数设为 16 时，依次执行场景A，场景B，场景C，时序，分为三段: 13:15～13:25, 13:25～13:35, 13:35～13:45，分别对应场景A，场景B，场景C。

场景 A, 模拟50个用户，向 LLM 发送短对话推理请求。prompt 吞吐量只有 27 tokens/s, 但是生成 token 的吞吐量能达到 360 tokens/s. 但在场景 B 下，prompt 吞吐量就猛增到 660 tokens/s，是因为 RAG 场景下，长上下文文本，被连续处理，并发数只有20， 限制为16。但是generation 吞吐量量维持在 340 token/s。说明这是这个场景下，推理速度的上限。在解数学题的推理场景下，由于prompt 处理的复杂度高，推理复杂且比较长，所以 prompt 吞吐降到了个位数，而推理速度降到了 180 tokens/s. 说明 Qwen3-32B-AWQ 模型并不擅长数学推理。

TTFT 在 A 场景下平均为 38.4s, B 场景下 4.88s, C 场景下 0.249s。短对话时，TTFT较大，是因为LLM 限制了并发处理请求数为 16，而 A 场景下的并发用户数有 50 个，B 场景下就骤降到了 4.88s, 到了，C场景更是降到了 0.249s。但是 TPOT 在A，B 几乎一样，但是到了C场景下，延迟几乎增大一倍，E2E 时间也有类似的恶化。vllm RPS, 从 A, B 场景下接近 2 req/s, 恶化到了 0.1 req/s。这些与C场景下generation的吞吐量降低了接近一半一起证明了，C场景下的推理难度变大了，Qwen3-32B-AWQ 模型并不适合做数学推理任务。

系统中正在等待处理的请求，A场景下，平均27-34个， B场景下平均 0-4个，C场景下几乎为 0个，这是因为，LLM 限制同时处理请求数为 16，场景A 并发用户数为 50， 场景B为20，场景C为10，在等待原因的分析中，多数waitiing是正常的 deferred, 符合设置。值得注意的是场景C下，虽然等待的请求数为0，但是正在处理的请求数为 10， 而不是LLM的上限16， 这说明这种场景下，LLM已经达到推理能力的上限。

Prefix Cache的命中率场景A下大约是 21.8%，场景B 大约是 97.8%，场景C大约是 58.2%。说明 RAG下的 KV Cache 几乎100%命中，长文本推理下也超过50%，短对话也有20%左右。这样的命中率说明，KV Cache 确实在加速推理过程。

在多用户的情况下，GPU 的利用率达到 100%，证明我们已经拉满了GPU性能。GPU显存使用率一直维持在 90% 左右，是因为，我们在启动 vllm 的时候，设定了显存利用率 0.9，vllm采用的是预分配机制，就是在 vllm 正常启动后，就会占用 90% 的显存。

在 Nginx 服务层面，HTTP请求成功率是 100%，5xx的错误率是0，HTTP 连接数，也是稳定在三个场景的设定，50，20，10。这说明 HeteroServe 整体系统的稳定性较高。

LLM 并发数，`max-num-seqs=16`, `max-num-seqs=32`, `max-num-seqs=64` 我们可以分析得出类似的结论。
## ▪︎ 深度分析

完整的指标数据如下：

| 指标/场景                 | A-8  | B-8   | C-8     | A-16  | B-16 | C-16    | A-32 | B-32  | C-32    | A-64  | B-64  | C-64    |
| --------------------- | ---- | ----- | ------- | ----- | ---- | ------- | ---- | ----- | ------- | ----- | ----- | ------- |
| prompt吞吐量tokens/s     | 15   | 370   | 2.5     | 27    | 660  | 3       | 46   | 664   | 3.04    | 50    | 635   | 3.18    |
| generation吞吐量,token/s | 197  | 192   | 185     | 360   | 341  | 183     | 577  | 332   | 188     | 663   | 331   | 180     |
| TTFT(P99), s          | 92   | 19.8  | 38.3    | 38.4  | 4.88 | 0.249   | 9.92 | 0.243 | 0.243   | 0.494 | 0.243 | 0.242   |
| TPOT(P99),ms          | 49.8 | 49.8  | 49.8    | 49.8  | 49.8 | 74.8    | 75   | 75    | 75      | 74.8  | 74.8  | 74.8    |
| E2E(P99), s           | 59.6 | 29    | 220/240 | 35.2  | 14.6 | 120/180 | 19.6 | 15.1  | 120/180 | 14.95 | 14.5  | 220/240 |
| vllm RPS              | 1    | 1     | 0.1     | 1.93  | 1.71 | 0.48    | 2.93 | 1.65  | 0.55    | 3.45  | 1.69  | 0.5     |
| KV Cache使用用率， %       | 0.6  | 2.07  | 8.05    | 1.42  | 2.56 | 6.87    | 2.61 | 2.71  | 9.88    | 3.38  | 2.88  | 7.64    |
| Running, req          | 8    | 8     | 8       | 16    | 16   | 10      | 32   | 18-20 | 10      | 45    | 18-20 | 10      |
| waitiing，req          | 42   | 12-12 | 2       | 27-34 | 0-4  | 0       | 5-17 | 0     | 0       | 0     | 0     | 0       |
| Prefix Cache 命中率，%    | 21.4 | 97.7  | 57.9    | 21.8  | 97.8 | 58.2    | 21.2 | 98.2  | 57.6    | 19.3  | 97.8  | 58.9    |
| GPU利用率, %             | 100  | 100   | 100     | 100   | 100  | 100     | 100  | 100   | 100     | 100   | 100   | 100     |
| 显存使用率, %              | 90   | 90    | 90      | 90    | 90   | 90      | 90   | 90    | 90      | 90    | 90    | 90      |
| GPU 温度，$\degree C$    | 80   | 80    | 80      | 80    | 80   | 80      | 80   | 80    | 80      | 80    | 80    | 80      |
| 功耗，watt               | 220  | 220   | 220     | 220   | 220  | 220     | 220  | 220   | 220     | 220   | 220   | 220     |
| Nginx请求速率req/s        | 1.2  | 1.2   | 0.285   | 2     | 2    | 0.2     | 3    | 1.86  | 0.29    | 3.52  | 1.86  | 0.3     |
| HTTP 连接数              | 50   | 20    | 10      | 50    | 20   | 10      | 50   | 20    | 10      | 50    | 20    | 10      |

prompt 处理吞吐量在三个场景下，最并发限制8，16，32，64 逐步升高并稳定，因为这时处理速度不受并发数限制。prompt 的处理速度与场景任务有关，短对话在 50 tokens/s, 长上下文能达到 660 tokens/s, 而数学推理只有 3 token/s。这是因为，统计口径时 1 min 内平均值，短对话的开销在大量请求的切换等待上，数学推理的开销在大量推理上，所以 RAG 场景下更能反映系统极限的处理 prompt 的速度，大概在 660 tokens/s。

推理生成 token 的吞吐量，短对话场景不受并发请求数影响，下最高也能达到 660 tokens/s 的速度。长上下文场景下的推理速度统计口径，会被处理 prompt 的速度影响。在数学推理上，这种长生成的输出，只能达到 180 tokens/s。说明真实推理速度，与推理任务的难度相关。 

TTFT 在并发数为 8, 16, 32, 64 时，呈指数级下降，说明大量时间耗费在排队等待上，在不受并发数限制的情况下，99% 的请求，TTFT都在 243 ms 内，而且三个场景差别不大，只有短对话时，需要一些等待开销。所以基本上正常情况下的 TTFT 就是 240 ms 左右。
TPOT 在不受并发约束时，逐步达到 75ms，并且真正进入到 Decode 阶段后，推理的速度不再受任务类型的影响。
E2E 相反，表现与任务类型高度相关，除了并发限制，排队等待造成的端到端延迟恶化外，任务本身会导致 E2E 差别巨大。一般正常推理任务，消除并发限制后，99%都稳定在 15s 左右，但是数学推理任务，平均返回时间是 3.5min～4min。这时正常的，因为数学推理是长生成文本，推理内容长但是每个 token 的平均生成速度并没有恶化，依然维持 75ms。E2E 的数值恶化是正常任务需求。

KV Cache 命中率也和任务类型相关，短对话 20%左右，长上下文能达到 98%，长推理文本的场景下能达到 60%。 KV Cache 的设置和调度，让命中率处于比较好的状态。

在所有场景下，GPU层面的表现非常稳定，100%利用率，温度 80 $\degree C$ , 显存利用率 90%，功耗220w。整体性能表现良好，且稳定，对 GPU 的开发利用几乎达到最佳水平。 nginx服务器上 ，HTTP请求成功率是 100%，5xx的错误率是0，HTTP 连接数，也是稳定在三个场景的设定，50，20，10。这说明 HeteroServe 整体系统的稳定性较高。 

## ▪︎ 总结

heteroserve 系统处理 prompt 的吞吐量和推理生成的吞吐量，极限都在 660 tokens/s 左右。实际速度还要受并发限制，处理请求开销等因素的影响。推理生成 token 的速度，还与任务的难度相关.
TTFT 正常情况下在 240 ms 左右，主要受高并发下排队的影响，TPOT 正常情况下 75 ms 左右。TTFT 与 TPOT 均不太受任务类型影响，只与请求等待时间相关。RPS 就和任务相关度比较高，短对话，可以 3.5 req/s, 长上下文 1.7 req/s, 长推理任务只能 0.5 req/s。 KV Cache 命中率在短文本，长文本，长推理下，分别 20%， 98%， 60%，说明 KV Cache 调度管理是有效的，起到了加速推理的作用。GPU 性能充分利用且表现稳定，GPU 利用率 100%，显存利用率 90%，温度工作状态下 80 $\degree C$, 闲置状态 30 $\degree C$。GPU功耗，闲置状态下 20w 左右，满负荷工作下 220w 左右。nginx请求速率与任务相关，但是 nginx 的 HTTP 请求成功率 100%，没有出现 5xx 错误。说明系统有相当好的稳定性。

HeteroServe 系统整体表现，总结如下：

| 指标                  | 最高值                             | 约束指标表现因素            |
| ------------------- | ------------------------------- | ------------------- |
| prompt 吞吐量          | 660 tokens/s                    | 受并发数，任务类型约束         |
| 生成token吞吐量          | 660 tokens/s                    | 任务类型约束              |
| TTFT                | 240 ms                          | 高并发，会导致排队等待         |
| TPOT                | 75 ms                           | Decode 速度不受任务类型影响   |
| E2E                 | 15s                             | 数学推理(长文本推理)会显著增加    |
| vllm RPS            | 3.5/1.7/0.5                     | 任务相关，短对话/长上下文/长生成   |
| Prefix KV Cache 命中率 | 20% / 98% / 60%                 | 任务相关，短对话/长上下文/长生成   |
| GPU 利用率             | 100%                            | 充分利用                |
| GPU 温度              | 30 $\degree C$ / 80 $\degree C$ | 闲置 / 满载             |
| GPU 功耗              | 20w / 220w                      | 闲置 / 满载             |
| Nginx HTTP 请求速率     | 3.5 / 1.7/ 0.5                  | 短对话 / 长文本 / 长推理     |
| 5xx 错误率             | 0                               | HTTP 各种场景下，连接成率100% |

结论：HeterServe 系统在短文本，长上下文，长推理的场景下，都有良好的表现. 在合理规划推理任务是，能够获得较好的 tokens 吞吐量。TTFT 和 TPOT 有较好表现，重点是要尽量避免请求排队。KV Cache 命中率较高，显存的利用效率很高。整个系统的软硬件运行都非常稳定，GPU 各项指标表现都正常，GPU 充分利用并且运行稳定。HeteroServe 系统可以作为一个性能良好的生产级推理平台。 
