import gradio as gr 
import httpx
import json
import time 
import re

API_URL = "http://192.168.31.221/v1/chat/completions"

def render_thinking(text):
    """ 把 <think>...</think> 快渲染成浅灰色斜体"""

    pattern = r'<think>(.*?)</think>'
    return re.sub(pattern, 
                  r'<span style="color:#888;font-style:italic;background:#f5f5f5;padding:8px;display:block;border-left:3px solid #ccc">☁️思考过程：\1<span>',
                  text, flags=re.DOTALL
                )

def chat_stream(message, model_name, history):
    if not message:
        return "", "", history

    # 构建消息历史
    messages = []
    for h in history:
        messages.append({"role": "user", "content": h[0]})
        messages.append({"role": "assistant", "content": h[1]})
    messages.append({"role": "user", "content": message})

    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
        "max_tokens": 2000,
        "temperature": 0.6,
    }

    t_start = time.time()
    ttft = None
    token_count = 0
    full_text = "" 

    try:
        with httpx.stream("POST", API_URL, json=payload, timeout=300) as r:
            for line in r.iter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            if ttft is None:
                                ttft = (time.time() - t_start) * 1000
                            token_count += 1
                            full_text += delta
                            elapsed = time.time() - t_start
                            tpot = (elapsed - ttft/1000) * 1000 / max(1, token_count - 1) if token_count > 1 else 0

                            stats = (
                                f"### 实时性能指标\n\n"
                                f"- ** 首 token 延迟 (TTFT) **: {ttft:.0f} ms\n"
                                f"- ** 每 token 延迟 (TPOT) **: {tpot:.1f} ms\n"
                                f"- ** 生成 tokens **: {token_count}\n"
                                f"- ** 生成速度 **: {token_count / elapsed:.1f} tokens/s"
                                f"- ** 总耗时 **: {elapsed:.1f}"
                            )

                            yield render_thinking(full_text), stats, history
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        yield f"❌ 错误: {e}", "", history
        return 
    hisotry = history + [(message, full_text)]
    yield render_thinking(full_text), stats, history

# ============= UI =============
with gr.Blocks(title="HeteroServe Demo", theme=gr.themes.Soft()) as demo:
    gr.Markdown("""
    # 🚀 HeteroServe 实时演示
    
    **生产级 LLM 推理服务** | 3×2080Ti 22GB | Qwen3-32B-AWQ | PP=3
    """)
    
    with gr.Row():
        with gr.Column(scale=3):
            model = gr.Dropdown(
                choices=["qwen3-32b-awq", "qwen3-14b-fp16"],
                value="qwen3-32b-awq",
                label="模型选择"
            )
            input_box = gr.Textbox(
                label="输入",
                lines=3,
                placeholder="输入你的问题..."
            )
            with gr.Row():
                btn_send = gr.Button("发送", variant="primary", scale=2)
                btn_clear = gr.Button("清空", scale=1)
            output = gr.HTML(label="回答")
            history = gr.State([])
        
        with gr.Column(scale=2):
            stats = gr.Markdown(label="实时指标", value="*等待请求...*")
    
    btn_send.click(
        chat_stream,
        inputs=[input_box, model, history],
        outputs=[output, stats, history]
    )
    btn_clear.click(lambda: ("", "", []), outputs=[output, stats, history])

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False)
