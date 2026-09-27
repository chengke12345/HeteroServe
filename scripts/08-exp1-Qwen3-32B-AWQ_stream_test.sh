#!/bin/bash

curl -N http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-32b-awq",
    "messages": [{"role":"user","content":"<think>请慢慢思考</think>计算 23×47"}],
    "stream": true,
    "max_tokens": 1000
  }'
