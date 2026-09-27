import openai
import json
import re
from datasets import load_dataset, get_dataset_config_names
from tqdm import tqdm

def make_client(port):
    return openai.OpenAI(base_url=f"http://192.168.31.221:{port}/v1", api_key="dummy")

def extract_choice(text):
    if "<think>" in text and "</think>" not in text:
        return ""
    if "</think>" in text:
        text = text.split("</think>",1)[-1]
    m = re.search(r"\b([ABCD])\b", text.strip())
    return m.group(1) if m else ""

def eval_subject(client, model_name, subject):
    ds = load_dataset("ceval/ceval-exam", subject, split="val")
    correct = 0
    total = len(ds)

    for ex in tqdm(ds,desc=subject):
        prompt = f"请只输出一个大写字母 A/B/C/D,不要解释。 {ex['question']}\nA. {ex['A']}\nB. {ex['B']}\nC. {ex['C']}\nD. {ex['D']}\n 答案是："
        resp = client.chat.completions.create(
            model = model_name,
            messages = [{"role": "user","content": prompt}],
            max_tokens = 8192, 
            temperature = 0,
            extra_body = {"chat_template_kwargs": {"enable_thinking": False}},
        )
        ans = resp.choices[0].message.content.strip()
        pred = extract_choice(ans)

        print(prompt)
        print(ans)
        print("提取答案：", pred, "标准答案：", ex["answer"])
        if pred == ex["answer"]:
            correct += 1
        
    return {
        "subject": subject,
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else 0
    }

def eval_ceval_all(client, model_name):
    subjects = get_dataset_config_names("ceval/ceval-exam")
    #subjects = ["computer_network", "operating_system", "computer_architecture", "college_programming",]
    
    results = []
    total_correct = 0
    total_questions = 0

    for subject in subjects:
        result = eval_subject(client, model_name, subject)
        results.append(result)

        total_correct += result['correct']
        total_questions += result['total']
        print(f"{subject}: {result['accuracy']}: .3f"
              f"({result['correct']}/{result['total']})")
    
    macro_avg = sum(r["accuracy"] for r in results) / len(results)
    micro_avg = total_correct / total_questions

    final = {
        "model": model_name,
        "macro_average": macro_avg,
        "micro_average": micro_avg,
        "total_correct": total_correct,
        "total_questions": total_questions,
        "subjects": results,
    }
    return final

results = {}
for port, name in [(8001, "qwen3-32b-awq")]:
    client = make_client(port)
    result = eval_ceval_all(client,name)
    results[name] = result

    print(f"\n{name}")
    print(f"Macro average: {result['macro_average']:.3f}")
    print(f"Micro average: {result['micro_average']:.3f}")

with open("ceval_val_qwen3-32b-awq_nonthinking.json", "w") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)