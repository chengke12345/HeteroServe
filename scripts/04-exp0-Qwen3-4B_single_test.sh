#!/bin/bash

curl http://localhost:8000/v1/chat/completions \
	-H "Content-Type: application/json" \
	-d '{
		"model": "qwen3-4b",
		"messages": [{"role": "user", "content": "你好，介绍一下自己"}],
		"temperature": 0.6,
		"max_tokens": 200
	    }'
