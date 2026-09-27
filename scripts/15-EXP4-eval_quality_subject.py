""" 用 CEval 子集评估三组配置"""
import openai
import json
import time
import re
from datasets import load_dataset, get_dataset_config_names
from tqdm import tqdm

# 通过 OpenAI 接口连接
def make_client(port):
    return openai.OpenAI(base_url=f"http://192.168.31.221:{port}/v1", api_key="dummy")

def extract_choice(text):
    if "</think>" in text:
        text = text.split("</think>")[-1]

    m = re.search(r"\b([ABCD])\b", text.strip())
    return m.group(1) if m else ""

def eval_ceval(client, model_name, num_samples=200):
    ds = load_dataset("ceval/ceval-exam", "computer_network", split="val")
    total = min(num_samples, len(ds))
    correct = 0
    for ex in tqdm(ds.select(range(total))):
        prompt = f"请只输出一个大写字母 A/B/C/D,不要解释。 {ex['question']}\nA. {ex['A']}\nB. {ex['B']}\nC. {ex['C']}\nD. {ex['D']}\n 答案是："
        resp = client.chat.completions.create(
            model = model_name,
            messages = [{"role": "user","content": prompt}],
            max_tokens = 8192, 
            temperature = 0,
            extra_body = {"chat_template_kwargs": {"enable_thinking": True}},
        )
        ans = resp.choices[0].message.content.strip()
        pred = extract_choice(ans)

        print(prompt)
        print(ans)
        print("提取答案：", pred, "标准答案：", ex["answer"])
        if pred == ex["answer"]:
            correct += 1
    return correct / total

#启动服务后分别跑
results = {}
for port, name in [(8002, "qwen3-14b-fp16")]:
    t0 = time.perf_counter()
    client = make_client(port)
    acc = eval_ceval(client, name)
    results[name] = acc
    print(f"{name}: {acc:.3f}, time: {time.perf_counter() - t0}")
    
json.dump(results, open("quality_results_qwen3-14b-fp16.json", "w"), indent=2)