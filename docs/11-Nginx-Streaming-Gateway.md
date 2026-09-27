对客户端的访问，项目采取的是生产级的 OpenAI 兼容网关，用 Nginx 做后端 vLLM 部署大模型的反向代理。统一访问的入口，提供流式转发，限流降级等功能。在未来扩展时，能够支持实现负载均衡、流量控制、和多模型路由。

在 Nginx 的配置项里，最重要的就是流式三件套，流式转发，流量限制，请求路由。

## 1. 流式(stream)

```nginx.conf
server {
	...
	proxy_buffering off;
	proxy_cache off;
	proxy_request_buffering off;
	chunked_transfer_encoding on;
	...
}
```

`proxy_request_buffering` 控制的是客户端请求到达 nginx 服务器后，是否提供请求体临时缓存，还是立即转发请求给 vLLM 服务。
`proxy_buffering` 是控制从 vLLM 返回 nginx 服务器后，是否提供响应体临时缓存。
`proxy_cache` 是控制 vLLM 返回 Nginx 服务器后，是否提供代理缓存，可供以后请求复用。

关掉 proxy_buffering 是流式网关最核心的配置。

# 2. 限流

`limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;`
`limit_req_zone`  用来定义<u>限流规则</u>的共享状态区。它只定义 “怎么统计”，不会直接拦截请求，真正启用限流的是后面的 `limit_seq`。

`limit_req zone=api burst=10 nodelay;` 同一 IP 可以瞬间发送超过 5 个请求(`rate=5r/s`)；最多可使用 10 个突发额度并立即转发。之后如果仍然过快，就返回限流错误。随着时间流逝，额度以约 5 请求/秒的速度恢复。`nodelay` 的含义是：突发请求不排队等待，而是立即放行；代价是突发额度耗尽后，后续请求会直接被拒绝。

所以，它表示每个IP长期平均速率为 5 个请求/s, 短期允许一个burst，但是随着时间流逝，长期来看请求平均速度要保持在 5 个以内。

# 3. 路由

```nginx.conf
upstream vllm-active {

zone llm_backend 64k;
resolver 127.0.0.11 valid=5s ipv6=off;
resolver_timeout 2s;

server vllm-main:8000
	resolve
	max_fails=1
	fail_timeout=10s;

server vllm-backup:8000
	resolve
	backup
	max_fails=1
	fail_timeout=10s;

keepalive 32;
}

server{
	location /v1/ {...proxy_pass http://vllm-active;...}
	location = /health {... proxy_pass http://vllm-active/health;...}
}
```

通过 location, 我们可以将请求转发到不同的后端服务器上，这里设置通过 上传流量 upstream vllm-active 将转发给后端被代理的 vLLM 模型服务器。正常情况下，转发到 vllm-main 主模型服务器上，如果主模型无法访问，就转发给备用模型。
在多模型系统中，还可以根据请求的参数信息，将不同请求发送给不同的模型进行推理。

> 在前端看来，它们都是统一入口，统一流量限制规则，可以提交参数指定推理模型，或者在故障时自动切换模型。未来多模型场景下，或者加设后端服务器时，对前端用户透明。用户对系统的使用，几乎不受影响。

nginx 完整的配置文件，参考 [nginx.conf](/deploy/nginx.conf)
配置文件的详细解析，参考 [nginx.conf 配置解析](/docs/analysis%20&%20research/16-nginx.conf%20配置解析.md)
