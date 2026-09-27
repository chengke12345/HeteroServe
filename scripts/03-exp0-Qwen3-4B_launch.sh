#!/bin/bash

CUDA_VISIBLE=DEVICES=0 vllm serve /opt/models/Qwen3-4B \
	--dtype float16 \
	--gpu-memory-utilization 0.85 \
	--max-model-len 4096 \
	--served-model-name qwen3-4b \
	--host 0.0.0.0 \
	--port 8000  
