from locust import HttpUser, task, tag, between
import random
import json

#======== 场景数据 ========
# 短 prompt, 短输出，高并发
SHORT_PROMPTS = [
    "你好，今天天气怎么样? ",
    "解释一下，什么是 Paged Attention?",
    "写个 Python 函数计算斐波那契",
    "推荐三本机器学习入门书?",
    "用一句话总结 Transformer",
] 

# 模拟检索到的长文档(每段约 200 tokens)
RAG_DOCUMENTS = [
    "vLLM 是一个高吞吐量的 LLM 推理引擎， 由 UC Berkeley 开发..." * 10,
    "Paged Attention 借鉴了操作系统的虚拟内存管理思想..." * 10,
    "Flash Attention 通过 IO 感知的 attention 计算..." * 10,
]

RAG_QUESTIONS = [
    "vLLM 的核心创新是什么？",
    "Paged Attention 如何提升显存利用率?",
    "Flash Attention 适用于什么场景?",
]

MATH_PROBLEMS = [
    "证明：对任意整数 n , n^3 - n 必能被 6 整除",
    "求方程 x^2 + 3x + 2 = 0 的解",
    "一个圆的周长是 31.4cm, 求圆的面积",
    "0.1 + 0.2 在浮点数下, 为什么不等于3?",
]

class LLM(HttpUser):
    wait_time = between(0.5, 2)

    def on_start(self):
        self.client.headers = {"Content-Type": "application/json"}

    #========== 场景A：短对话。短prompt + 短输出，高并发 ============
    @tag("scene_A")
    @task(5)
    def chat_short(self):
        self.client.post("/v1/chat/completions", json={
            "model": "qwen3-32b-awq",
            "messages": [{"role": "user", "content": random.choice(SHORT_PROMPTS)}],
            "max_tokens": 200,
            "temperature": 0.7,
            "stream": False,
        }, name="A_chat_short")

    #=========== 场景B：RAG 长上下文。 长prompt + 中输出

    @tag("scene_B")
    @task(3) 
    def rag_long_context(self):
        long_ctx = "\n\n".join(random.sample(RAG_DOCUMENTS, 2))
        question = random.choice(RAG_QUESTIONS)
        self.client.post("/v1/chat/completions", json={
            "model": "qwen3-32b-awq",
            "messages": [{"role": "user", "content": f"基于以下文档回答问题: \n\n{long_ctx}\n\n问题: {question}"}],
            "max_tokens": 200,
            "temperature": 0.5,
            "stream": False,
        },name="B_rag_long")

    # ============= 场景C：推理，长生成(thinking mode), 短prompt + 长输出
    @tag("scene_C")
    @task(2)
    def reasoning_thinking(self):
        self.client.post("v1/chat/completions", json={
            "model": "qwen3-32b-awq",
            "messages": [{"role": "user", "content": random.choice(MATH_PROBLEMS)}],
            "max_tokens": 3000,
            "temperature": 0.6,
            "stream": False
        }, name="C_reasoning")
    

