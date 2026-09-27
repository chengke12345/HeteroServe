#!/bin/bash

# 三组配置，三种并发= 9次测试
# 每次跑之前，要切换服务，注意端口

# Qwen3-32B-AWQ
bash scripts/06-exp1-Qwen3-32B-AWQ_launch.sh & sleep 100
for c in 4 16 64; do
	bash 13-exp3-vllm_bench_run.sh /opt/models/Qwen3-32B-AWQ qwen3-32b-awq 8001 $c
done

pkill -f "vllm serve"


# Qwen3-14B-FP16
bash scripts/09-exp2-Qwen3-14B-FP16_launch.sh & sleep 120
for c in 4 16 64; do
	bash 13-exp3-vllm_bench_run.sh /opt/models/Qwen3-14B qwen3-14b-fp16 8002 $c
done

pkill -f "vllm serve"

# Qwen3-32B-GPTQ
bash scripts/10-exp2-Qwen3-32B-GPTQ_launch.sh & sleep 100
for c in 4 16 64; do
	bash 13-exp3-vllm_bench_run.sh /opt/models/Qwen3-32B-GPTQ qwen3-32b-gptq 8003 $c
done

pkill -f "vllm serve"

