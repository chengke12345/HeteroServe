`nginx.conf` 是 Nginx 最核心的配置文件。
nginx.conf 中的配置项分为 3 个部分， 「全局 global」，「事件 events」, 和 「http」。

下面的配置项括号中的部分，指明该配置项是在哪个配置项下面的。
参考的配置文件，详见 [nginx.conf](/deploy/nginx.conf)
# 1. worker_processes (global)

`worker_processes auto` 是指 CPU 自动创建工作进程。这里是指 Nginx 那台服务器所能看到的CPU，不是实际处理业务的后端服务器 CPU，更不是 GPU。

Nginx 采取的是 master/worker 架构：
>- 「master 进程」：读取配置、启动 / 停止 / 重新加载 worker 进程。主要是管理 woker 的职能。
>- 「worker 进程」：实际处理网络请求，包括接受客户端请求，限流，转发给vllm服务，把流式响应送回客户端。

worker_processes auto, 会让 Nginx 根据运行环境可用的逻辑 CPU 核数，自动创建 worker。例如 Nginx 容器可见 4 个 vCPU (virtual), 它通常就会启动 4 个 worker。

<u> 每个 worker 都用事件循环方式, 同时处理大量连接</u>

比如，Nginx 服务器接受到 100 个 TCP 请求。master 会分配给 4 个 worker 来处理，比如每个处理 25 个。worker0 在处理它的 25 个请求的时候，如果要等待数据传输，通信反馈，它不会阻塞等待，而是切换去处理另一个请求，在自己负责的 TCP 请求间进行调度。

>注意⚠️：
>1. worker 的调度是基于事件驱动，不是 CPU 的时间片轮询。
>2. 一个 TCP 请求分配给某个 worker 的时候，就由这个 worker 负责到底。
>3. worker 的工作只是做通信，反向代理和负载均衡后端服务器资源，数据中转。不会做实际的业务处理，业务处理是后端服务器的工作任务。

所以叫做，「每个 worker 事件循环的方式同时处理大量连接」。 
# 2.  worker_connections (events)

`events {worker_connections 1024; }`, 理论上，每个 worker 可以同时处理的连接数是 1024. 理论上 Nginx 可以处理的连接总容量是 `worker 数量 * 1024` 但是在反向代理中，一个活跃请求，会同时占用客户端和 vLLM 服务端两侧的连接，因此实际可同时代理的请求数会更低。

# 3. limit_req_zone (http)

`limit_req_zone $binary_remote_addr zone=api:10m rate=5r/s;`
`limit_req_zone`  用来定义「限流规则」的「共享状态区」。它只定义 「怎么统计流量」，不会直接拦截请求，真正启用限流的是后面的 `limit_seq`。

>- 「`$binary_remote_addr`」: 这个变量中存放的是客户端 IP 地址，二进制形式存放。客户端 IP 作为限流身份，同一个 IP 共用一个配额。nginx 自动提取用户请求中的源 IP，把值赋给该变量。
>- 「`zone=api:10m`」: 创建名为 api 的，大小 10MB 的共享内存区，用于保存各 IP 的限流状态。所有 Nginx worker 共享它，所以不会出现 “不同worker各算各的配额”。
>- `rate=5r/s`: 每个 IP 的稳定速率为每秒 5个请求， 5 request/s。

说明：

> [!NOTE] limit_req_zone 与 limit_req
> 「limit_req_zone」 是定义限流规则状态的共享区。lim_req 才是是真正启用限流的配置。比如`limit_req zone=api burst=10 nodelay;` 放在某个 location下，表示对这个路径的请求，限流规则参考 api 这个共享区设置的限制，允许有10个突发请求的额度，并且会立即转发(nodelay)。所以前者定义限流规则共享区，后者启用了共享区的限流规则进行限流。

> [!NOTE] $binary_remote_addr 变量
> - `$binary_remote_addr` 是 Nginx 内置变量，无需自行定义。`$remote_addr` 是文本形式，如 203.0.113.8。`$binary_remote_addr` 是同一个 IP 的二进制形式, IPV4是4字节，IPV6是16字节。在配置限流时，通常使用 $binary_remote_addr, 因为它占用共享内存更少，更适合作为 `limit_req_zone`  的 key。
> - Nginx 启动时，会注册 `$binary_remote_addr` 这个内置变量，每当worker处理某个连接或请求的时，就会从当前客户端地址信息中取值。 客户端请求的连接中包含了客户端 IP 信息。当我们需要使用 `$binary_remote_addr` 这个变量值的时候，它就会沿着当前 worker 处理的请求去获取客户端 IP 信息。
> - 总结: $binary_remote_addr 的名称和读取规则是全局注册的；当某段配置需要它的值时，Nginx 会从**当前请求关联的连接**中读取客户端 IP。

> [!NOTE] 限流共享状态区 zone=api:10m
> `zone=api:10m` 的意思是：Nginx 在内存中创建一块名为 `api`、总大小为 10 MB 的**共享状态区**，专门保存限流账本。它是同一个 Nginx 实例的所有 worker 共同访问这一份 10 MB。它只是用来保存限流记录的。比如：
>```text
> worker0 ─┐
> worker1 ─┼─ 共享内存 zone "api"（总共 10 MB）
> worker2 ─┘       ├─ IP A：近期请求速率/超额量
> ...              ├─ IP B：近期请求速率/超额量
> ...              └─ IP C：近期请求速率/超额量
>```
> 这保证 IP A 的请求即使先后被不同 worker 接收，仍会使用同一份限流记录，不会绕过限流。
> 在 64 位平台上，每个 key(IP) 的限流状态约占 128 字节，所以 10 MB 理论上大约能记录 8 万个不同 IP 的状态

> [!NOTE] rate=5r/s
> - 5r/s表示 5 requests/s. 它表示限制每个 IP 长期平均速率低于 5 个请求/s. 不是按自然秒做“每秒计数，超过 5 就立刻拒绝”。`rate=5r/s` 相当于每个 IP 平均每 `200ms` 获得一次请求额度。
> - Nginx 允许短期有一个突发额度，在 `limit_req zone=api burst=10 nodelay;`中配置。同一 IP 可以瞬间发送超过 5 个请求；最多可使用 10 个突发额度并立即转发。之后如果仍然过快，就返回限流错误。随着时间流逝，额度以约 5 请求/秒的速度恢复。`nodelay` 的含义是：突发请求不排队等待，而是立即放行；代价是突发额度耗尽后，后续请求会直接被拒绝，而不是排队。
> - 总结：它表示每个IP长期平均速率为 5 个请求/s, 短期允许一个burst，但是随着时间流逝，长期来看请求平均速度要保持在5个以内。

# 4. upstream (http)

upstream 主要是配置在后台不同服务器资源之间，进行负载均衡。例如：

```nginx
upstream main_backend {
	server vllm-main: 8001;
	keepalive 32;
}
```

upstream 后面的名字可以任意取，主要用于 server 对请求的代理转发。比如后面就会用到：

```nginx
server {
	listen 80;
	...
	location / {
		proxy_pass http://main-backend
	}
}
```

比如这个 server 监听 80 端口。对于根目录的访问，转发到代理 main-backend 上

>- 如果 nginx 在一个 docker compose 的网络中，upstream server 就可以直接使用 docker compose 中的 services 名字。上面的 vllm-main 就是 compose.yaml 中的 services 名称。

### 常规域名解析

通常， 在 upstream 中 server 配置项，会有一个解析的过程，大致为：

```
server vllm:8000
      ↓
向当前运行环境的 DNS 查询 "vllm"
      ↓
得到一个 IP
      ↓
建立 TCP 连接：IP:8000
```

### nginx 与 docker compose 同网络解析

如果 nginx 和 vLLM 在同一台物理机上，同一个docker compose 网络中, compose 会默认给每个启动的服务创建可被同网络容器解析的 DNS 名称。因此，这里的 vLLM 能解析为该容器在 Docker 网络中的私有 IP。端口 8001 不必暴露到物理机。

```
nginx 容器 ── Docker 内置 DNS 查询 vllm ──→ vllm 容器 IP:8000
```

因为 nginx 容器和 vLLM 容器是被 compose 一起启动，是在同一个网络，所以它们之间可以使用服务名，DNS 服务会提供解析服务。
# 5.  keepalive(http/upstream)

`keepalive 32`, 表示 Nginx 与 vLLM 之间最多保留 32 条空闲长连接，供后续请求复用。如果没有设置 keepalive 的情况下，连接建立的方式是：

```
请求 1：建立 TCP 连接 → 调用 vLLM → 关闭连接
请求 2：重新建立连接 → 调用 vLLM → 关闭连接
```

设置了 keepalive 之后，连接建立的方式是

```
请求 1：建立 TCP 连接 → 调用 vLLM → 连接放回连接池
请求 2：复用已有连接 → 调用 vLLM → 再放回连接池
```

32 代表每个 nginx worker 最多缓存 32 条空闲的连接。

# 6. server{ } 配置块

`server{listen 8080; ...}` 表示一个虚拟服务器配置块。它不是一个进程，它定义的是，「哪些需求由这组规则处理」。比如：

```
访问的 IP 和端口
    ↓ listen 8080
Host 请求头
    ↓ server_name（如果配置）
请求路径
    ↓ location
```

访问 Nginx 的 8080 端口时，请求会进入这个配置块，再根据路径 location 匹配。例如，`/health`健康检查, `/metrics` 监控指标, `/v1/...` OpenAI 访问大模型 API 等等。如果访问的是 nginx 服务器 8080 下的其他路径，通常返回 404.

<u>这个server{}是虚拟的服务器配置块。要和 upsteam 的 server 配置区分开--它是指定转发到后端哪台服务器上。</u>


# 7. 流式缓存设置(http/server)

```nginx
server {
	...
	proxy_buffering off;
	proxy_cache off;
	proxy_request_buffering off;
	...
}
```

server 配置块中的这三个代理缓存配置。

```
① 客户端
   │ 请求体
   ▼
[proxy_request_buffering]
   │
   ▼
Nginx ──请求──> vLLM


② Nginx <─响应── vLLM
   │
[proxy_buffering / proxy_cache]
   │
   ▼
客户端
```

>- `proxy_request_buffering` 控制的是客户端请求到达 nginx 服务器后，是否提供请求体临时缓存，还是立即转发请求给后端 vLLM 服务。
>- `proxy_buffering` 控制的是，vLLM 服务器返回响应到 nginx 服务器后，nginx 是否提供响应体的临时缓存。
>- `proxy_cache` 控制的是， vLLM 返回响应到 nginx 服务器后，是否提供代理缓存。这个代理缓存可供以后请求复用。

这三个配置都控制的 Nginx 服务器这一层，但只有 `proxy_cache` 是"跨请求复用的缓存"。另外两个是设置 “单次请求的临时缓冲”。

### `◼︎` proxy_buffering off 

关闭的是「上游响应缓冲」。默认开启时，vLLM 返回的数据可能先进入 Nginx 的内存缓冲区，数据较大时，还可能写入 Nginx 临时文件，然后 Nginx 再发送给客户端。

```
vLLM → Nginx 内存/临时文件 → 客户端
```

关闭后
```
vLLM 返回一部分 → Nginx 尽快转发收到部分 → 客户端
```

<u><b>这对 LLM 流式输出最重要</b></u>。它不是永久缓存设置，只存在当前请求。关闭后也不代表绝对实现 "一个 token 到 一个 token 的传输"，仍可能受其他因素影响，比如 vLLM 自身输出缓冲，TCP 和 OS 系统缓冲，客户端 HTTP 库的缓冲，前置 CDN 或负载均衡器缓冲等等因素。

### `◼︎`proxy_cache off

<u>这是真正意义上的 Nginx 代理缓存</u>。开启代理缓存后，Nginx 可以把某个上游响应保存下来，让后续相同请求直接使用

```
第一次：客户端 → Nginx → vLLM
                   ↓
                 缓存响应

第二次：客户端 → Nginx 缓存
                 不再访问 vLLM
```

off 表示不使用这种缓存。配置中没设置 proxy_cache 的情况下，代理缓存默认是关闭的。这个设置是为了防止继承上层配置。

### `◼︎` proxy_request_cache off

关闭的是「客户端请求体缓冲」。默认开启时，Nginx 通常要把完整的请求体接受下来，再发送给后端 vLLM 处理。

```
客户端上传完整 JSON
        ↓
Nginx 收完整
        ↓
发送给 vLLM
```

关闭后，客户端来多少，Nginx 就可以向 vLLM 转发多少

```
客户端发送一部分 → Nginx → vLLM
客户端再发送一部分 → Nginx → vLLM
```

它适合大型上传，例如音频、图片或超大请求体。普通聊天请求的 JSON 通常不大，因此不一定需要关闭。

这三个缓存设置都不会关闭 vLLM 的 KV Cache、Prefix Cache 或模型缓存；「它们只控制 Nginx 代理层的行为」。

# 8. 代理超时设置(server)

```nginx
server{
	proxy_read_timeout 600s;
	proxy_send_timeout 600s;
	proxy_connect_timeout 60s;
}
```

这三个超时配置主要控制 Nginx 和 上游 vLLM 服务器之间的通信，不是整个请求的总时长。

```
客户端 → Nginx → vLLM
              ↑
       这三个超时主要管这里
```

>- `proxy_connect_timeout 60s` 表示 Nginx 最多等待 60s 来建立与 vLLM 的连接。
>- `proxy_send_timeout 600s` 表示 Nginx 向 vLLM 发送请求时，连续 600s 无法继续写入数据，就断开连接。方向是 `Nginx --请求体--> vLLM` 它控制的是 Nginx 对 vLLM 发送的请求，不是把模型响应发送给客户端。普通聊天请求体很小，所以这个超时通常很少触发。它在上传大型图片、音频或超长请求体时更有意义。
>- `proxy_read_timeout 600s`, 表示 Nginx 等待 vLLM 返回数据时，两次读取之间最多空闲 600s. 方向是`Nginx <--模型响应--vllm`。这是 LLM 场景最重要的超时。<u>注意：它不是“整个模型生成最多只能运行 600 秒”，而是“vLLM 最长不能连续 600 秒没有返回任何数据”。这也是站在 Nginx 的角度看 vLLM 的返回。 </u>

所以
```
proxy_connect_timeout：Nginx 等多久才能连上 vLLM
proxy_send_timeout：Nginx 向 vLLM 发送请求时，允许多久没有写入进展
proxy_read_timeout：读取 vLLM 返回的响应时，允许多久没有新数据
```

如果要控制 Nginx 向客户端发送响应的超时，使用的是

```nginx
send_timeout 600s
```

而不是 `proxy_send_timeout`。


# 9. chunked_transfer_encoding(server/http)

`chunked_transfer_encoding on`  表示允许 Nginx 在向客户端发送 HTTP/1.1 响应时，使用「分块传输编码」。普通响应可以提前知道完整大小，但 LLM 流式生成时，事先不知道最终响应有多大。这个配置可以让 Nginx 向客户端发送响应时，按数据块边生成边发送。

```
vLLM 生成数据 A → Nginx 发送数据块 A
vLLM 生成数据 B → Nginx 发送数据块 B
vLLM 生成数据 C → Nginx 发送数据块 C
生成结束          → Nginx 发送结束标记
```

客户端不需要等待完整答案，也不需要提前知道响应总大小。它主要是控制 `Nginx -> 客户端` 的 HTTP/1.1 响应格式。HTTP/2 和 HTTP/3 使用自己的数据帧机制，不使用 HTTP/1.1 的 `Transfer-Encoding:chunked`。

虽然`chunked_transfer_encoding on` 允许在完整响应尚未生成时，使用数据块逐步传输；但它本身不保证 Nginx 立即转发数据，它不会保证 "一个 token 对应一个 chunk"。实际行为还要受 Nginx, 操作系统，客户端等各方面的影响。

### encoding

这里的 `encoding` 指"传输编码规则", 不是指字符编码，压缩或加密。`chunked`规定了数据在网络上传输时的组织格式，如以下面的格式传输

```
块大小（十六进制）
块数据
块大小
块数据
……
0（表示结束）
```

所以，这里的 encoding, 表示「将数据编码成哪种格式来传输」。`chunked encoding` 是给每个数据块增加长度和边界标记，使接收方知道每块有多大，以及整个响应什么时候结束。它决定 HTTP/1.1 如何描述这些分段数据。

# 10. proxy_set_header(server/http)

proxy_set_header 是用来设置 Nginx 转发给上游 vLLM 服务器时的 HTTP 请求头。方向是 

```
客户端 → Nginx → vLLM
                  ↑
          proxy_set_header
```

注意⚠️：proxy_set_header 设置请求头指的是，Nginx 发送给 vLLM 的 HTTP 请求中请求头的字段。比如。HTTP 请求头有可能如下：

```http
POST /v1/chat/completions HTTP/1.1
Host: api.example.com
Content-Type: application/json
X-Real-IP: 203.0.113.10

{"model":"qwen","messages":[]}
```

我们一般把第一行叫做「请求行」，`Host`, `Content-Type`, `X-Real-IP` 叫做 「HTTP 请求头」，实际指的是「请求头字段」。通常所说的请求头指「整个HTTP 请求头」。proxy_set_header 设置的就是其中的一个请求头字段。其基本语法为：

```nginx
proxy_set_header 请求头名字 请求头值
```

它设置的就是上面 `Host`, `X-Real-IP` 等请求头字段的值。例如：

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header Connection "";
```

-  `Host $host` : 告诉 vLLM 客户端访问的域名。这是客户端访问 Nginx 时使用的目标域名，不是客户端自己的域名，也不是上游 vLLM 的域名。是 Nginx 服务器使用的域名。
 
-  `X-Real-IP` : 是请求 Nginx 的直接连接方的 IP，这里设置 `proxy_set_header X-Real-IP $remote_addr` :是让 Nginx 把自己接收到该 TCP 链接时，看到的来源 IP，写入 `X-Real-IP`请求头字段，再发送给 vLLM 服务器.

 -  `x-Forwarded-For` : 记录请求经过的代理 IP链。类似于下面
```
X-Forwarded-For: 203.0.113.10, 10.0.0.20, 10.0.0.30

原始客户端        第一层代理     第二层代理
203.0.113.10 → 10.0.0.20 → 10.0.0.30 → 当前 Nginx
```

`$proxy_add_x_forwarded_for` 的值可能是多个 IP 用逗号分隔开，组成的一个字符串。


> [!NOTE] Nginx 反向代理的两条独立TCP连接
> Nginx 在对客户端请求进行反向代理的时候，涉及到两条独立的 TCP 连接
> ```
> 客户端 ──TCP 连接 A──> Nginx ──TCP 连接 B──> vLLM
> ```
> Nginx 不是原样转发客户端的 TCP 包，而是：
> 1. 接受并解析客户端的 HTTP 请求
> 2. 根据配置重新构造一个HTTP 请求。
> 3. 通过另外新建一条 TCP 连接发送给 vLLM.
>所以，vllm 的角度在 TCP/IP 层通常看到的来源是 nginx, 如果需要知道原始客户端 IP，就要通过HTTP请求头的信息传递。
> ```
>proxy_set_header X-Real-IP $remote_addr;
>proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
> ```

- `Connection ""`: 空值表示 Nginx 向 vllm 转发请求时，不发送 Connection 这个 HTTP 请求头。Nginx 两侧是两条独立连接，如上所示。假设客户端发送时设置了 `Connection: close`，那它只应该影响 客户端与 Nginx 之间 的 A 连接，不应该继续影响 Nginx 与 vLLM 之间的 B 连接。Connection 是逐跳请求头，只对当前两个直接通信节点有效，不应夸代理原样传递。
  Nginx 设置空字符串，就是不传递 Connetion 设置，不设置成 close,  HTTP/1.1 默认允许持久连接，请求结束后，Nginx 和 vllm 的连接可以放回 upstream keepalive 连接池，供后续请求复用.

# 11. 精准匹配与前缀匹配 location = /xxx/ .vs. location /xxx/ (server)

我们在 server 中定义 location 的时候，有两种定义方式：

```nginx
server{
	location /v1/ {...}
	location = /health {...}
}
```

带等号的匹配方式叫做「精确匹配」, 不带等号的方式叫做「前缀匹配」.

「精确匹配」: `location = /health {...}`

> - 只有在 URI 路径恰好是 /health 时才匹配，然后才会按照这个 location 下面的配置进行操作。

| 请求路径           | 是否匹配    |
| -------------- | ------- |
| /health        | 是       |
| /health/?a=1   | 是(参数OK) |
| /health/abc    | 否       |
| /health/ab/abc | 否       |
注意⚠️，查询参数不参与 location 匹配，所以 /health/?a=1 依然匹配。

「前缀匹配」`location /v1/ {...}`

> - 只要 URI 以 /v1/ 开头就能匹配

| 请求路径       | 是否匹配 |
| ---------- | ---- |
| /v1/       | 是    |
| /v1/?a=1   | 是    |
| /v1/abc    | 是    |
| /v1/test/a | 是    |
| /v1        | 否    |
| /v1abc     | 否    |
单一固定端点通常使用精确匹配。某个路径及其全部子路径使用前缀匹配。

>注意⚠️：
>精确匹配 = 匹配成功后，Nginx 会立即使用该 location, 不会继续检查其他前缀或正则 location。普通前缀匹配可能被后续匹配成功的正则 location 覆盖。

# 12. 命名 location

愿配置是

```nginx
error_page 503 = @ratelimited;

location @ratelimited {
    default_type application/json;
    return 503 '{"error":{"message":"rate limited, retry later","type":"rate_limit"}}';
}
```

以 @开头的 location 不是 URL 路径，而是一个仅供 Nginx 内部跳转的命名处理位置。可以理解为一个内部处理标签。<u>表示如果产生了 503 错误，就跳到名为 ratelimited 的处理逻辑上去</u>。整体处理逻辑为：

```
请求进入 location /v1/
        ↓
limit_req 判断请求超过限制
        ↓
Nginx产生 503
        ↓
error_page 503 = @ratelimited
        ↓
内部转到 location @ratelimited
        ↓
返回自定义 JSON
```

客户端最终收到的是类似下面的信息

```
HTTP/1.1 503 Service Temporarily Unavailable
Content-Type: application/json

{"error":{"message":"rate limited, retry later","type":"rate_limit"}}
```

这不是 HTTP 302 重定向，不会要求客户端重新请求，客户端 URL 也不会变化。

= 的含义
`error_page 503 = @ratelimited` 中 = 表示最终状态码由 @ratelimited 中的处理结果决定。这里location 内部逻辑中返回的也是 503. 
不能请求访问这个 location，它只用于内部跳转。

# 13. Nginx 中 location 匹配规则

一个请求到达 Nginx 服务器后，Nginx 要匹配到相应的 location 做处理。请求可能会和多个location成功匹配，但是 nginx 只会选择其中一个。选择匹配的规则如下：

> 1. 查找 = 精确匹配。精确匹配上之后，就立即执行，不再检查后面匹配了。
> 2. 普通前缀匹配。如果请求能够匹配上多个普通前缀匹配，选出最长的普通前缀匹配
> 3. 检查正则 location，按配置文件从上到下的顺序，第一个匹配成功的正则获胜。
> 4. 如果没有正则匹配，使用2中找到的普通前缀匹配。

注意⚠️，如果有正则 location 匹配上，那么正则 location 可能会覆盖前面找到的普通前缀匹配候选。如果不希望某个普通前缀被正则匹配覆盖，可以使用

```nginx
location ^~ /v1/ {...}
```

这样，如果这个普通前缀 location 匹配上之后，就直接使用，不会再检查正则。

## 正则 location 

location 后面的定义，以 `~` 或 `～*` 开头的，表示这是一个要正则匹配的 location. ～表示正则匹配时要区分大小写，~* 表示不区分大小写。

所以 location 的匹配可以总结如下：

| location 形式         | 匹配方式                  |
| ------------------- | --------------------- |
| `location = /path`  | 精准匹配                  |
| `location /path`    | 普通前缀匹配                |
| `location ^~ /path` | 优先前缀匹配，匹配<br>之后不再检查正则 |
| `location ~ regex`  | 区分大小写正则匹配             |
| `location ~* regex` | 不区分大小写正则匹配            |
| `location @name`    | 内部命名 location         |

# 14. proxy_next_upstream (http/location)

我们在 location 中，设置 `proxy_pass` 到`upstream`处理之外，还可以设置 `proxy_next_stream`，比如：

```nginx
upstream vllm_backend {
    server vllm-1:8000;
    server vllm-2:8000;
}
proxy_pass http://vllm_backend

proxy_next_upstream error timeout http_502 http_503 http_504;
proxy_next_upstream_tries 2;
proxy_next_upstream_timeout 30s;
```

proxy_pass 把这个请求传递给 vllm_backend 这个 upstream 来处理。upstream 中指定了可以处理的服务器有多个。当上游服务器发生指定故障时，尝试同一个 upstream 组里的下一台服务器。比如，当`vllm-1` 发生连接错误，超时或返回指定错误状态码时，尝试连接 `vllm-2`。

这个配置是说，发生了`timeout`, `http_502`, `http_503`, `http_504`, 这几个错误的时候，可以尝试连接下一台服务器。`proxy_next_upstream_tries 2`, 表示总尝试次数为 2 次，允许尝试其他上游的总时间不超过 30 秒。 

>它只能切换到同一个 upstream 组中的其他 server，不能自动切到另一个 upstream 块。
>如果 upstream 只有一台服务器，就没有下一台可尝试。
>流式响应一旦已经发送给客户端，就无法中途切换
