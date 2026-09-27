#!/bin/bash

curl -N http://localhost:8000/v1/chat/completions \
	-H "Content-Type: application/json" \
	-d '{
		"models": "qwen3-4b",
		"messages": [{"role": "user", "content": "写首关于秋天的诗"}],
		"stream": true,
		"max_tokens": 200
	}'
