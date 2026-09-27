#!/bin/bash

curl http://localhost:8001/v1/models
curl http://localhost:8001/v1/chat/completions \
	-H "Content-Type: application/json" \
	-d '{
    		"model": "qwen3-32b-awq",
    		"messages": [{"role":"user","content":"用一句话解释 PagedAttention"}],
    		"max_tokens": 200
  	}'
