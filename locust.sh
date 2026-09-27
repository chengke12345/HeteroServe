#!/bin/bash

# 场景A-短对话场景 短prompt + 短输出，高并发
# 场景A：短对话，50并发，10分钟
locust -f scripts/18-locustfile.py \
    --host http://localhost \
    --headless \
    --tags scene_A \
    -u 50 -r 5 -t 10m \
    --html reports/scene_A_50u.html \
    --csv reports/scene_A_50u

# 场景B-RAG长上下文，长prompt + 中输出
# 场景B：RAG 场景， 20并发，10分钟
locust -f scripts/18-locustfile.py \
    --host http://localhost \
    --headless \
    --tags scene_B \
    -u 20 -r 2 -t 10m \
    --html reports/scene_B_20u.html

# 场景C-推理，长生成(thinking mode), 短prompt + 长输出
# 场景C：推理场景，10并发，10分钟
locust -f scripts/18-locustfile.py \
    --host http://localhost \
    --headless \
    --tags scene_C \
    -u 10 -r 1 -t 10m \
    --html reports/scene_C_10u.html

