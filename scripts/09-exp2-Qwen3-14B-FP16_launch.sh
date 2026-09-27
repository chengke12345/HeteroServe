#!/bin/bash

set -euo pipefail

CUDA_VISIBLE_DEVICES=0,1 vllm serve /opt/models/Qwen3-14B \
	--tensor-parallel-size 2 \
	--dtype float16 \
	--gpu-memory-utilization 0.9 \
	--max-model-len 16384 \
	--max-num-seqs 64 \
	--enable-chunked-prefill \
	--enable-prefix-caching \
	--served-model-name qwen3-14b-fp16 \
	--host 0.0.0.0 \
	--port 8002 2>&1

