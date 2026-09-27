#!/bin/bash

LOCAL_MODEL_PATH=$1
SERVED_MODEL_NAME=$2
PORT=$3
CONCURRENCY=$4
RESULT_DIR="benchmarks/results"

mkdir -p $RESULT_DIR

vllm bench serve \
	--backend openai-chat \
	--base-url http://localhost:$PORT \
	--model $LOCAL_MODEL_PATH \
	--served-model-name $SERVED_MODEL_NAME \
	--endpoint /v1/chat/completions \
	--dataset-name sharegpt \
	--dataset-path benchmarks/datasets/ShareGPT_V3_unfiltered_cleaned_split.json \
	--num-prompts 500 \
	--max-concurrency $CONCURRENCY \
	--temperature 0.7 \
	--save-result \
	--result-dir $RESULT_DIR \
	--result-filename "${MODEL}_c${CONCURRENCY}_$(date +%Y%m%d_%H%M%S).json" 
