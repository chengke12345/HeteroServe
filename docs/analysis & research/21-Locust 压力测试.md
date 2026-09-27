Locust 是一个基于 Python 的开源性能与压力测试工具，能够模拟大量用户并发访问 Http/API 服务。它主要有以下特点：

> - 用 Python 编写用户行为，如登录，查询，下单。
> - 通过 HttpUser 和 @task 定义每个用户的行为。
> - 提供Web 控制台，可设置并发用户数，启动速率，并查看 RPS，响应时间，失败率等指标。
> - 支持命令行无界面运行，以及多机器分布式压测。
> - 它更适合压测接口和服务端性能，它不是浏览器自动化工具，不执行 js 或渲染网页

使用 Locust 压力测试的基本结构为：

```python
from locust import HttpUser, task

class MyUser(HttpUser):
	@task
	def home(self):
		self.client.get(/)
```

启动：`locust -f locustfile.py`, 然后访问控制台设置目标地址和并发量。

# 1. HttpUser 基类

HttpUser 是 Locust 中用于模拟 HTTP 客户端用户的基类。我们自己定义的用户类继承它，成为一个 HTTP 用户，并且拥有自己这类用户特有的行为模式。

> - 继承 HttpUser 之后，每个用户都会拥有 `self.client` 成员对象, 它可以发送 GET，POST，等 HTTP 请求。例如 `self.client.get(/)`。
> - 请求会自动记录到 Locust 报表，包括响应时间，成功/失败，响应大小等。
> - client 会保持 cookie, 因此可以模拟登录后继续访问的会话。
> - 每个并发用户对应一个 HttpUser 实例，并按照 @task 定义的行为循环执行。

<b>模拟用户行为</b>

Locust 会将每个 Http 用户对应生成一个 HttpUser 的实例来模拟。
> 注意⚠️，一个 HttpUser 对象模拟的是一个用户，而不是一个用户的 Http 请求。

# 2. @task 装饰器

继承 HttpUser 类，定义自己的客户端用户之后，在自己定义的类中，我们可以将一些成员方法用 @task 装饰器进行标记。

task 是 Locust 包提供的一个函数。Python 提供的 @... 装饰器语法，task 的具体实现和任务权重等功能是由 Locust 提供的。所以使用 @task 装饰器的时候，我们需要首先引入包和函数 `from locust import task`。

@task 装饰器还可以传入一个整数，表示设置该任务被调度的权重。@task 装饰器标记后，不会直接调用这个成员方法，它只负责“标记并登记”。真正调用它的是 Locust 的任务调度器。

# 3. 循环与多任务

在模拟用户(HttpUser对象)生成之后，标记为 @task 的成员函数，就会被 Locust 调度执行。@task 成员函数执行完成之后，会循环进入下一次执行，中间会等待 wait_time。

如果 HttpUser 中只定义了一个 @task，那么这个任务就会循环执行。如果定义了多个 task, 那么每次就会在这些任务之中，随机挑选执行。@task 装饰器中可以设置一个权重整数，在随机挑选的时候，会让任务被选中的概率更高。 

# 4.  任务调度器和执行过程

真正调度任务执行的是 Locust 任务调度器，它的执行过程可以理解为：

> 1. 定义类时，给方法加上 "这是任务，权重是多少"的标记，即@task 或 @task(5)。
> 2. Locust 收集这些方法，生成 HttpUser.tasks 任务列表，权重高的任务在列表中出现更多。
> 3. 压测启动后，每个 HttpUser 实例先执行一次 on_start().
> 4. 调度器从任务列表中随机取一个任务
> 5. 调度器以当前用户实例的 self 调用它。概念上可以认为是 `任务函数(当前用户实例)`
> 6. 任务结束后等待 wait_time, 然后回到第 4 步。

注意，HttpUser.tasks 任务列表是类级别的(HttpUser是类名)，同一个HttpUser类的不同实例，共享这个用户类的任务列表。类级 tasks 列表属于该类用户的行为清单与权重配置，不是执行队列，

比如：
```python
class ShopUser(HttpUser):
    @task
    def browse(self): ...

    @task(3)
    def search(self): ...
```
概念上可以认为
```
ShopUser.tasks = [browse, search, search, search]
```

即，ShopUser 类型的用户可以做 browse 和 search, 其中 search 被选中的概率更高。所以，假设创建了 3 个 ShopUser 实例：

```
ShopUser.tasks  ← 三个实例共同读取同一份行为清单

用户实例 A：random.choice(ShopUser.tasks) → 执行
用户实例 B：random.choice(ShopUser.tasks) → 执行
用户实例 C：random.choice(ShopUser.tasks) → 执行
```

真正调度执行的是实例内部循环，该实例的调度器决定这个用户下一步选哪个方法执行，什么时候执行。所以，Locust 调度器是属于实例层面的，实例调度器决定实例下一次执行哪个任务。

但是，类的 tasks 任务列表决定了，这个类“可选的行为有哪些，比例是多少？”。它只是实例在调度执行下一个任务时查询使用的一份共享规则表。

比如上面的 ShopUser.tasks 列表，ShopUser 实例要进行下一个任务时，就会参考 ShopUser 类的任务表，它会在 `[browse, search, search, search]` 中随机选一个，search 出现了三次，它被调用的概率自然是 browse 的 3 倍。

>全局的 Runner 负责创建和停止用户实例。 task 列表存在于每个用户类，供该类所有实例共享。实例自己有调度器，调度实例本身下一次循环执行的是哪个任务，但它调度时，能执行的任务和选择权重，参考该类的 task 列表。

只要一个成员方法被 @task 标记，它就会加入 task 列表，然后在实例调度执行任务时，该成员方法就会被实例调度器，按一定概率调度执行(循环执行多次，一定会被执行)。

# 5. on_start() 方法

on_start() 是 Locust 的用户实例启动的钩子方法。每个 HttpUser 实例被创建并开始运行时，Locust 会先调用一次 on_start(), 然后才进入 "选择并循环执行 @task" 的流程。

它是用户实例在启动时会调用一次，对应的在用户实例停止时，会调用一次 on_stop()。
例如：
```python
def on_start(self):
        self.client.headers = {"Content-Type": "application/json"}
```

这一句就是给当前模拟用户的 HTTP 会话设置默认请求头，之后该用户通过 self.client 发出的请求，默认会带

```
Content-Type: application/json
```






