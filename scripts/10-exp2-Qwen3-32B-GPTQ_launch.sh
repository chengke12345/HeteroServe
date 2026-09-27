#!/bin/bash
set -euo pipefail

MODEL_PATH="/opt/models/Qwen3-32B-GPTQ"
SERVED_NAME="qwen3-32b-gptq"
PORT=8003

export NCCL_TIMEOUT=1800

CUDA_DEVICE_ORDER=PCI_BUS_ID vllm serve $MODEL_PATH \
	--pipeline-parallel-size 3 \
	--tensor-parallel-size 1 \
	--dtype float16 \
	--quantization gptq_marlin \
	--gpu-memory-utilization 0.9\
	--max-model-len 16384 \
	--max-num-seqs 64 \
	--enable-prefix-caching \
	--enable-chunked-prefill \
	--served-model-name $SERVED_NAME \
	--host 0.0.0.0 \
	--port $PORT 2>&1 
