import time, json, statistics, requests, argparse

def run(base, model, prompts, max_tokens=256):
    rows = []
    for p in prompts:
        t0 = time.perf_counter(); first = None; n = 0 # number of tokens
        with requests.post(f"{base}/v1/completions", 
                           json={"model": model, "prompt": p, "max_tokens": max_tokens, "stream": True},
                           stream=True, timeout=300) as r:
            for line in r.iter_lines():
                if not line:
                    continue
                s = line.decode().removeprefix("data: ").strip()
                if s == "[Done]":
                    break
                if first is None:
                    first = time.perf_counter() - t0 #TTFT
                n += 1
            total = time.perf_counter() - t0
            tpot = (total - first) / max(n - 1, 1)
            rows.append({"ttft": first, "tpot": tpot, "tok": n, "tput": n/total})
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8001")
    ap.add_argument("--model", default="qwen3-32b-awq")
    ap.add_argument("--out", default="run.json")
    a = ap.parse_args()

    prompts = ["你好，简单介绍一下你自己。"] * 5 + ["请详细解释 PagedAttention 的工作原理，并举例。"] * 5 \
        + ["（长文）" + " 背景信息。" * 400 + "\n请总结上述要点。"] * 5

    rows = run(a.base, a.model, prompts)
    agg = {"ttft_p50": statistics.median(r["ttft"] for r in rows),
           "tpot_p50": statistics.median(r["tpot"] for r in rows),
           "tput_p50": statistics.median(r["tput"] for r in rows)}
    
    json.dump({"rows": rows, "agg": agg}, open(a.out,"w"), ensure_ascii=False, indent=2)
    print(json.dumps(agg, ensure_ascii=False, indent=2))