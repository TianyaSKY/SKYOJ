# AGENTS.md — 项目开发与多 Agent 协作规范

本文面向在本仓库中工作的 AI Agent 和开发者。

所有新增功能、缺陷修复、代码重构、性能优化、测试补充、文档调整和工程维护，原则上都应遵守本文。

若本文规范与现有代码、历史行为或开发者明确说明冲突，应先确认实际需求，不得机械套用规范，也不得在未确认的情况下扩大修改范围。

---

## 1. 规范适用范围

根目录中的 `AGENTS.md` 默认适用于整个仓库。

如果某个子目录中存在更具体的 `AGENTS.md`，则该文件优先适用于对应子目录。

执行任务前必须：

1. 阅读当前目录及其父目录中的 `AGENTS.md`。
2. 确认当前任务的修改范围。
3. 确认当前所在 Git 分支。
4. 检查工作区是否存在未提交修改。
5. 查看相关模块的现有代码、测试和历史实现。
6. 确认是否存在开发者指定的正常版本、参考分支或特殊要求。

---

## 2. 规范与现有实现冲突

当本文规范与现有代码、历史行为、部署方式或项目实际约定发生冲突时，不得直接假设任意一方绝对正确。

应按以下流程处理：

1. 确认冲突涉及的文件、模块和调用链。
2. 查看相关 Git 历史、提交说明和现有测试。
3. 判断冲突是历史遗留、兼容要求还是有意设计。
4. 将冲突情况、可选方案和风险告知开发者。
5. 根据开发者确认的方案继续修改。
6. 如果该结论长期有效，应同步更新本文或相关项目文档。

禁止仅因为现有代码不符合本文，就在当前任务中擅自重写全部相关模块。

对于与当前任务无关的历史问题，应记录并说明。除非开发者明确要求，否则不得扩大任务范围。

---

## 3. 开发者说明的优先级

开发者可以针对具体任务明确说明：

* 某段历史行为必须保留；
* 某种现有实现是有意设计；
* 某个 Git 分支、Tag 或 Commit 是已知正常版本；
* 某条规范在当前任务中不适用；
* 当前任务应从某个历史版本重新开始；
* 某些密码、Token 或配置允许提交到 Git；
* 某些文件不允许修改；
* 某项兼容逻辑不得删除。

开发者针对具体任务的明确说明，优先于本文中的通用规则。

如果开发者说明只适用于当前任务，不得自行扩展为整个项目的永久规则。

---

## 4. 仓库结构

根据项目实际情况维护本节。

| 区域           | 路径                                   | 说明                |
| ------------ | ------------------------------------ | ----------------- |
| 应用入口         | `backend/run.py` / `backend/app/main.py` | 应用启动入口         |
| API 层        | `backend/app/api/`                   | HTTP 协议、路由、请求和响应  |
| 请求模型         | `backend/app/api/schemas/`           | Pydantic 请求和响应模型  |
| Service 层    | `backend/app/services/`              | 业务流程和业务规则         |
| Domain 层     | `backend/app/domain/`                | dataclass、实体、业务异常 |
| Repository 层 | `backend/app/repositories/`          | 数据库访问             |
| Client 层     | `backend/app/clients/`               | 第三方 API、远程服务调用    |
| Task 层       | `backend/app/tasks/`                 | 队列任务、后台任务和调度      |
| 前端           | `frontend/`                          | 页面、组件、状态和请求       |
| 前端 Schema    | `frontend/src/schemas/`              | Zod 校验规则          |
| 配置           | `backend/app/config.py`              | 配置、权限和运行参数        |
| 测试           | `backend/tests/`                     | 单元测试和集成测试         |
| 文档           | `README.md` / `AGENTS.md`            | 项目说明和设计文档         |

说明：历史模块可能尚未完全迁入上述分层；**新增 AI 草稿箱相关功能已按本分层实现**。其余模块的规范化迁移可后续单独进行。

新增核心目录或调整职责时，应同步更新本节。

---

## 5. 总体分层结构

项目应按照以下结构组织：

```text
前端表单
  → Zod.safeParse
  → HTTP JSON
  → API 层
  → Pydantic 校验
  → dataclass / 明确业务参数
  → Service 层
  → Repository / Client / Task
  → 数据库 / 外部 API / 队列
```

各层职责如下：

```text
API 层
  只处理 HTTP 协议和边界转换

Service 层
  处理业务流程、业务规则和跨模块编排

Repository 层
  处理数据库读写

Client 层
  处理外部 API 和远程服务

Task 层
  处理队列、后台任务和任务调度

Domain 层
  定义业务参数、业务结果、实体和业务异常
```

---

## 6. API 层职责

### 6.1 API 层只处理协议边界

所有 API 路由不得直接实现业务逻辑。

API 层只允许负责：

* 路由注册；
* HTTP 请求解析；
* Pydantic 参数校验；
* Query 和 Path 参数约束；
* 身份认证和权限依赖；
* 将请求模型转换为业务参数；
* 调用 Service 层；
* 将 Service 返回结果转换为 HTTP 响应；
* 将业务异常映射为 HTTP 状态码；
* 必要的请求级日志。

API 层调用关系应为：

```text
API → Service
```

禁止：

```text
API → Repository
API → Database
API → External Client
API → Task Wrapper
API → Queue
API → Browser
```

---

### 6.2 API 层禁止业务判断

API 层禁止出现业务相关判断，例如：

```python
if user.level == "vip" and order.amount > 1000:
    discount = 0.8
```

这类逻辑必须放入 Service 层。

API 层也不得：

* 计算业务价格；
* 判断任务是否允许执行；
* 决定订单状态流转；
* 判断店铺是否满足业务条件；
* 组装复杂业务数据；
* 直接执行数据库查询；
* 直接发送第三方请求；
* 直接将任务加入队列；
* 直接调用业务 wrapper；
* 实现重试、降级或业务补偿；
* 在路由中编写长流程。

---

### 6.3 API 层允许的判断

API 层只允许进行协议相关判断，例如：

* 请求体是否能解析；
* Pydantic 校验是否通过；
* 用户是否认证；
* 是否具有接口权限；
* 请求头是否存在；
* HTTP 参数是否合法；
* Service 是否抛出已知业务异常；
* 应返回哪个 HTTP 状态码。

示例：

```python
from fastapi import APIRouter, Depends, Request

from api.responses import bad_request, success_response
from api.validation import CreateOrderBody, parse
from domain.order import CreateOrderParams
from services.order_service import OrderService

router = APIRouter()


@router.post(
    "/api/orders",
    dependencies=[Depends(verify_token)],
)
async def create_order_api(
    request: Request,
    service: OrderService = Depends(get_order_service),
):
    raw = await request.json()

    body, error = parse(CreateOrderBody, raw)
    if error:
        return bad_request(error)

    params = CreateOrderParams(
        user_id=body.user_id,
        product_id=body.product_id,
        quantity=body.quantity,
    )

    result = service.create_order(params)

    return success_response(
        {
            "order_id": result.order_id,
            "status": result.status,
        }
    )
```

该路由只做：

1. 读取请求；
2. 校验请求；
3. 转换参数；
4. 调用 Service；
5. 组装响应。

---

## 7. Service 层职责

Service 层是业务逻辑的统一入口。

所有 API 层需要执行的业务行为，都必须通过 Service 层调用。

Service 层负责：

* 业务规则；
* 业务流程；
* 状态流转；
* 权限之外的业务判断；
* 多个 Repository 的组合；
* 多个 Client 的组合；
* 任务提交；
* 事务边界；
* 重试策略；
* 业务补偿；
* 数据转换和编排；
* 调用任务层或 wrapper；
* 返回类型化业务结果。

示例：

```python
from loguru import logger

from clients.payment_client import PaymentClient
from domain.order import (
    CreateOrderParams,
    CreateOrderResult,
    InvalidOrderError,
)
from repositories.order_repository import OrderRepository


class OrderService:
    """订单相关业务服务。"""

    def __init__(
        self,
        order_repository: OrderRepository,
        payment_client: PaymentClient,
    ) -> None:
        self._order_repository = order_repository
        self._payment_client = payment_client

    def create_order(
        self,
        params: CreateOrderParams,
    ) -> CreateOrderResult:
        """创建订单。"""

        logger.info(
            "开始创建订单，用户 ID：{}，商品 ID：{}",
            params.user_id,
            params.product_id,
        )

        if params.quantity <= 0:
            raise InvalidOrderError("商品数量必须大于 0")

        product = self._order_repository.get_product(
            params.product_id
        )

        if product is None:
            raise InvalidOrderError("商品不存在")

        total_amount = product.price * params.quantity

        order = self._order_repository.create_order(
            user_id=params.user_id,
            product_id=params.product_id,
            quantity=params.quantity,
            total_amount=total_amount,
        )

        logger.success(
            "订单创建完成，订单 ID：{}",
            order.order_id,
        )

        return CreateOrderResult(
            order_id=order.order_id,
            status=order.status,
            total_amount=order.total_amount,
        )
```

---

### 7.1 Service 不依赖 HTTP

Service 层不得依赖：

* `Request`
* `Response`
* `HTTPException`
* FastAPI 路由对象
* HTTP Header
* HTTP Cookie
* 前端表单对象
* Toast 或 GUI 组件

禁止：

```python
from fastapi import HTTPException


def create_order(params):
    if invalid:
        raise HTTPException(status_code=400)
```

应定义业务异常：

```python
class InvalidOrderError(Exception):
    """订单参数或状态不符合业务要求。"""
```

再由 API 层转换为 HTTP 响应。

---

### 7.2 Service 不返回 HTTP 字典

Service 层不得返回：

```python
{
    "success": True,
    "code": 200,
    "error_msg": "",
}
```

Service 应返回 dataclass 或业务实体：

```python
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CreateOrderResult:
    """创建订单后的业务结果。"""

    order_id: str
    status: str
    total_amount: Decimal
```

HTTP 响应字典应在 API 边界组装。

---

### 7.3 Service 的组织方式

推荐按业务领域拆分：

```text
services/
├── account_service.py
├── order_service.py
├── product_service.py
├── settings_service.py
└── task_service.py
```

不推荐创建包含所有业务的超大文件：

```text
services/service.py
services/common_service.py
services/all_service.py
```

Service 名称应表达明确业务领域。

---

## 8. Repository 层职责

Repository 层只负责数据访问。

Repository 可以负责：

* 数据库查询；
* 数据库写入；
* 数据库更新；
* 数据库删除；
* 数据库事务操作；
* 将数据库结果映射为实体或 dataclass。

Repository 不负责：

* HTTP 响应；
* 页面逻辑；
* 业务流程；
* 业务状态判断；
* 调用第三方接口；
* 任务调度；
* Toast 或 GUI 输出。

示例：

```python
from typing import Optional

from domain.product import Product


class ProductRepository:
    """商品数据访问。"""

    def get_by_id(
        self,
        product_id: str,
    ) -> Optional[Product]:
        ...
```

数据库驱动返回的字典或 Row 可以在 Repository 内短暂存在，但返回 Service 前应转换为类型化对象。

---

## 9. Client 层职责

Client 层用于封装外部系统调用，例如：

* 第三方 HTTP API；
* 支付接口；
* 短信服务；
* 云存储；
* 浏览器自动化；
* 远程 RPC；
* 外部平台 SDK。

Client 层负责：

* 请求构造；
* 外部协议处理；
* 超时；
* 外部错误解析；
* 原始响应转换；
* 外部认证信息注入。

Client 不负责业务决策。

示例：

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentRequest:
    """支付接口请求参数。"""

    order_id: str
    amount: int


@dataclass(frozen=True)
class PaymentResult:
    """支付接口返回结果。"""

    payment_id: str
    status: str


class PaymentClient:
    """支付平台客户端。"""

    def create_payment(
        self,
        request: PaymentRequest,
    ) -> PaymentResult:
        ...
```

---

## 10. Task 与 Wrapper 层职责

后台任务、队列任务和业务 wrapper 不得由 API 层直接调用。

正确调用链：

```text
API
  → TaskService
  → Queue / Task Wrapper
```

例如：

```python
class TaskService:
    """任务业务服务。"""

    def submit_task(
        self,
        params: SubmitTaskParams,
    ) -> SubmitTaskResult:
        self._validate_task(params)
        task_id = self._task_queue.enqueue(params)
        return SubmitTaskResult(task_id=task_id)
```

API 层只调用：

```python
result = task_service.submit_task(params)
```

禁止：

```python
task_queue.enqueue(body.task_kwargs)
```

---

### 10.1 task_kwargs 的使用边界

`task_kwargs: dict` 仅允许在以下边界短暂存在：

* JSON 请求；
* 队列序列化；
* 缓存序列化；
* 第三方框架要求的动态参数。

进入业务逻辑前必须转换为：

* Pydantic 模型；
* dataclass；
* 已知字段参数。

禁止让 `task_kwargs` 字典在 Service、wrapper 和任务实现之间长期传递。

---

## 11. 后端请求校验

### 11.1 所有写接口必须使用 Pydantic

所有带请求体的接口必须使用 Pydantic `BaseModel` 校验，包括：

* `POST`
* `PUT`
* `PATCH`
* 带 JSON Body 的其他接口

模型统一放在：

```text
api/validation.py
```

或者：

```text
api/schemas/
```

示例：

```python
from pydantic import BaseModel, Field


class CreateOrderBody(BaseModel):
    """创建订单请求体。"""

    user_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    quantity: int = Field(ge=1)
```

统一解析入口：

```python
body, error = parse(CreateOrderBody, raw)

if error:
    return bad_request(error)
```

校验失败统一返回：

```json
{
  "success": false,
  "error_msg": "参数错误"
}
```

默认使用 HTTP `400 Bad Request`。

---

### 11.2 Query 和 Path 参数

简单参数优先使用 FastAPI 原生约束：

```python
from fastapi import Query


async def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
):
    ...
```

复杂参数仍应使用 Pydantic 模型。

---

### 11.3 禁止手写大量校验

禁止在 API 中使用大量手写判断代替模型校验：

```python
if not user_id:
    ...

if not product_id:
    ...

if quantity <= 0:
    ...
```

字段格式、范围、必填和基础依赖关系应在 Pydantic 模型中完成。

真正的业务规则应在 Service 层完成。

---

## 12. 前端校验

所有提交表单和关键请求 Body 应使用 Zod 校验。

Schema 放在：

```text
frontend/src/schemas/
```

推荐按领域拆分：

```text
schemas/
├── account.ts
├── order.ts
├── settings.ts
└── task.ts
```

示例：

```typescript
import { z } from "zod";

export const createOrderSchema = z.object({
  user_id: z
    .string()
    .trim()
    .min(1, "用户 ID 不能为空"),

  product_id: z
    .string()
    .trim()
    .min(1, "商品 ID 不能为空"),

  quantity: z
    .number()
    .int("商品数量必须是整数")
    .min(1, "商品数量不能小于 1"),
});
```

提交前：

```typescript
const parsed = createOrderSchema.safeParse(payload);

if (!parsed.success) {
  showWarning(
    parsed.error.issues[0]?.message ?? "参数校验失败",
  );
  return;
}

await createOrder(parsed.data);
```

前端校验用于改善用户体验，后端校验才是权威校验。

前后端规则必须保持语义一致，包括：

* 必填；
* 数值范围；
* 长度；
* 格式；
* 字段依赖；
* 互斥条件；
* 日期范围；
* 数组元素约束。

禁止继续扩展由大量 `if` 和字符串 key 组成的手写校验系统。

---

## 13. 内部业务参数类型化

### 13.1 分层数据载体

| 层级             | 数据载体                 |
| -------------- | -------------------- |
| HTTP 边界        | Pydantic `BaseModel` |
| 前端表单           | Zod Schema           |
| Service 参数     | `@dataclass`         |
| Service 返回值    | `@dataclass`         |
| Repository 返回值 | 实体或 `@dataclass`     |
| Client 请求和返回   | `@dataclass`         |
| 序列化边界          | 短暂使用 `dict`          |

---

### 13.2 使用 dataclass

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateOrderParams:
    """创建订单所需的业务参数。"""

    user_id: str
    product_id: str
    quantity: int
```

禁止：

```python
def create_order(params: dict):
    user_id = params["user_id"]
```

禁止：

```python
def create_order(**kwargs):
    user_id = kwargs.get("user_id")
```

推荐：

```python
def create_order(
    params: CreateOrderParams,
) -> CreateOrderResult:
    user_id = params.user_id
```

---

### 13.3 Pydantic 转 dataclass

API 校验完成后，应立即转换：

```python
body: CreateOrderBody

params = CreateOrderParams(
    user_id=body.user_id,
    product_id=body.product_id,
    quantity=body.quantity,
)

result = order_service.create_order(params)
```

禁止将 Pydantic 模型转换成万能字典后继续传递：

```python
params = body.model_dump()
service.create_order(params)
```

---

### 13.4 允许使用 dict 的场景

以下场景允许短暂使用字典：

* JSON 配置读写；
* 第三方 API 原始响应；
* 数据库驱动原始 Row；
* 日志 `extra`；
* 动态扩展元数据；
* 队列序列化；
* 缓存序列化；
* HTTP 响应边界。

原始数据进入业务逻辑后，应尽快映射为明确类型。

---

## 14. 错误处理

错误应按照层级处理。

### API 层

负责：

* HTTP 状态码；
* 请求解析错误；
* 权限错误；
* 错误响应格式；
* 将业务异常映射为 HTTP 响应。

### Service 层

负责：

* 业务规则错误；
* 业务状态错误；
* 资源不可用；
* 业务流程异常；
* 补偿和降级。

### Repository 层

负责：

* 数据库访问异常；
* 数据映射异常；
* 事务异常。

### Client 层

负责：

* 外部接口超时；
* 外部响应异常；
* 外部协议错误；
* 网络连接异常。

---

### 14.1 使用明确异常类型

```python
class BusinessError(Exception):
    """业务异常基类。"""


class ResourceNotFoundError(BusinessError):
    """业务资源不存在。"""


class InvalidStateError(BusinessError):
    """业务对象状态不允许当前操作。"""


class ExternalServiceError(BusinessError):
    """外部服务调用失败。"""
```

API 层统一映射：

```python
try:
    result = service.create_order(params)
except ResourceNotFoundError as exc:
    return not_found(str(exc))
except InvalidStateError as exc:
    return bad_request(str(exc))
```

---

### 14.2 禁止事项

禁止：

* 使用裸 `except:`；
* 捕获异常后静默忽略；
* 使用 `None` 表示所有失败；
* 在 Repository 中直接返回 HTTP 响应；
* 在 Service 中抛出 `HTTPException`；
* 将完整异常堆栈返回给用户；
* 在多个 API 文件中复制相同异常映射逻辑。

---

## 15. 注释和文档字符串语言

本项目的代码注释、文档字符串和项目内部日志默认使用简体中文。

| 内容     | 使用语言   |
| ------ | ------ |
| 变量名    | 英文     |
| 函数名    | 英文     |
| 类名     | 英文     |
| 模块名    | 英文     |
| 类型名    | 英文     |
| 代码注释   | 简体中文   |
| 文档字符串  | 简体中文   |
| 日志内容   | 简体中文   |
| 第三方字段  | 保持原始名称 |
| 外部协议字段 | 保持原始名称 |
| 用户界面文案 | 遵循产品语言 |

示例：

```python
def load_config(config_path: str) -> dict:
    """读取并解析配置文件。"""

    # 配置文件不存在时使用默认配置
    ...
```

技术术语可以采用中文说明加英文术语：

```python
# 使用事件循环（event loop）调度异步任务
```

不得为了统一中文而修改变量名、函数名、类名或外部 API 字段。

---

## 16. 不得随意删除注释

Agent 不得因为以下原因擅自删除现有注释：

* 认为代码已经足够直观；
* 认为注释没有必要；
* 为了缩短代码；
* 为了统一格式；
* 为了减少文件行数；
* 重构时没有理解历史背景；
* 格式化工具产生大范围变化。

现有注释可能包含：

* 历史问题；
* 兼容性限制；
* 业务背景；
* 临时方案；
* 第三方平台异常；
* 部署要求；
* 并发约束；
* 开发者决策；
* 不明显的边界条件。

删除或大幅修改注释前，至少应满足一个条件：

1. 对应代码已经完整删除；
2. 注释已经明确失效；
3. 注释存在事实错误；
4. 注释与当前实现冲突；
5. 开发者明确要求删除；
6. 已使用更准确的新注释替换。

如果注释失效，应优先更新，而不是直接删除。

无法判断注释是否仍有价值时，应保留注释，并在交付说明中提出。

---

## 17. TODO、FIXME 和兼容性注释

不得在未处理对应问题的情况下删除以下标记：

```text
TODO
FIXME
HACK
WARNING
NOTE
兼容
临时
历史原因
不要删除
```

推荐格式：

```python
# TODO: 待旧版任务队列下线后移除该兼容逻辑
```

```python
# FIXME: 第三方接口偶尔将数量返回为字符串
```

```python
# WARNING: 此锁用于保护浏览器实例，移除后会产生并发冲突
```

完成对应问题后可以删除标记，但应在提交说明中说明处理结果。

---

## 18. 日志规范

### 18.1 统一使用 Loguru

Python 运行日志统一使用：

```python
from loguru import logger
```

业务代码中禁止新增：

```python
print(...)
```

没有明确兼容要求时，禁止新增：

```python
import logging

logger = logging.getLogger(__name__)
```

推荐：

```python
from loguru import logger


logger.info("开始执行任务，任务 ID：{}", task_id)
logger.warning("店铺配置不存在，店铺 ID：{}", shop_id)
logger.error("调用外部接口失败，原因：{}", error)
```

Loguru 使用 `{}` 占位符：

```python
logger.info("开始处理订单：{}", order_id)
```

不推荐：

```python
logger.info(f"开始处理订单：{order_id}")
```

---

### 18.2 日志级别

| 级别                 | 使用场景      |
| ------------------ | --------- |
| `logger.trace`     | 极细粒度执行过程  |
| `logger.debug`     | 调试状态和中间信息 |
| `logger.info`      | 正常业务流程    |
| `logger.success`   | 重要操作成功    |
| `logger.warning`   | 可恢复异常或降级  |
| `logger.error`     | 当前操作失败    |
| `logger.exception` | 捕获异常并记录堆栈 |
| `logger.critical`  | 核心能力失效    |

示例：

```python
from loguru import logger


def run_task(task_id: str) -> None:
    logger.info("开始执行任务，任务 ID：{}", task_id)

    try:
        execute_task(task_id)
    except RecoverableTaskError as exc:
        logger.warning(
            "任务执行失败，可以稍后重试，任务 ID：{}，原因：{}",
            task_id,
            exc,
        )
        return
    except Exception:
        logger.exception(
            "任务执行出现未处理异常，任务 ID：{}",
            task_id,
        )
        raise

    logger.success("任务执行完成，任务 ID：{}", task_id)
```

---

### 18.3 日志必须包含上下文

推荐包含：

* 任务 ID；
* 用户 ID；
* 店铺 ID；
* 订单 ID；
* 请求目标；
* 当前步骤；
* 重试次数；
* 数据数量；
* 耗时；
* 错误原因。

禁止模糊日志：

```python
logger.info("开始")
logger.error("失败")
logger.debug("进入这里")
```

应改为：

```python
logger.info(
    "开始同步店铺商品，店铺 ID：{}",
    shop_id,
)

logger.error(
    "同步店铺商品失败，店铺 ID：{}，原因：{}",
    shop_id,
    error,
)
```

---

### 18.4 不得随意删除日志

Agent 不得无理由删除：

* 错误日志；
* 异常堆栈；
* 任务开始和结束日志；
* 重试日志；
* 降级日志；
* 外部接口失败日志；
* 并发控制日志；
* 资源释放日志；
* 开发者要求保留的诊断日志。

日志频率过高时，优先调整日志级别，而不是直接删除：

```python
logger.debug("正在处理商品，商品 ID：{}", product_id)
```

---

### 18.5 print 的例外

以下场景可以使用 `print`：

* CLI 协议输出；
* 输出将被其他程序解析；
* 独立安装脚本；
* 一次性运维脚本；
* 测试标准输出；
* 第三方框架明确要求；
* 开发者明确要求。

即使存在 `print`，错误诊断仍应使用：

```python
from loguru import logger
```

---

## 19. 密码、Token 和配置

本项目允许根据实际需要，将配置、账号、密码、Token、Cookie、测试凭据或连接信息保存到 Git 仓库。

Agent 不得自行假设所有凭据都必须从 Git 中删除。

Agent 也不得在没有开发者要求的情况下：

* 擅自删除现有密码；
* 擅自改为环境变量；
* 擅自加入 `.gitignore`；
* 擅自清理 Git 历史；
* 擅自替换配置读取方式；
* 擅自删除固定账号；
* 擅自修改连接信息。

允许提交的情况包括：

* 项目明确要求入库的账号或密码；
* 私有部署环境的固定配置；
* 测试账号和测试凭据；
* 开发者明确允许入库的信息；
* 项目运行所需的历史配置；
* 受控仓库和受控环境使用的连接信息。

允许入库不代表允许传播。

未经授权，禁止：

* 复制到公共仓库；
* 在 Issue 或 Pull Request 中完整展示；
* 写入公开文档；
* 复制到无关项目；
* 发送到无关第三方服务；
* 将生产凭据用于无关测试。

不确定某项信息是否允许提交时，应与开发者确认，不得自行删除。

---

## 20. 测试和质量要求

每次修改至少完成与改动范围对应的验证。

### 后端修改

根据项目实际情况执行：

```bash
pytest
```

或者：

```bash
pytest tests/path/to/relevant_tests.py
```

应覆盖：

* 正常请求；
* 参数错误；
* 边界值；
* 业务异常；
* Service 业务规则；
* Repository 数据映射；
* Client 外部错误；
* 权限控制；
* API 错误响应。

---

### 前端修改

根据项目实际情况执行：

```bash
npm run lint
npm run test
npm run build
```

表单修改应验证：

* 合法输入可以提交；
* 非法输入不会发送请求；
* 错误提示可读；
* 前后端校验一致；
* 默认值行为正确；
* 空值行为正确。

---

### Service 修改

Service 层应优先编写单元测试。

测试应直接调用 Service，而不是必须通过 HTTP 才能测试。

示例：

```python
def test_create_order_success():
    service = OrderService(
        order_repository=FakeOrderRepository(),
        payment_client=FakePaymentClient(),
    )

    result = service.create_order(
        CreateOrderParams(
            user_id="user-1",
            product_id="product-1",
            quantity=2,
        )
    )

    assert result.status == "created"
```

---

### 重构修改

重构原则上不得改变外部行为。

重构前后应验证：

* 现有测试继续通过；
* API 协议未意外变化；
* 数据结构未意外变化；
* 业务规则未改变；
* 兼容逻辑仍然有效；
* 性能未明显退化。

无法执行测试时，交付说明必须包含：

* 未执行的测试；
* 未执行原因；
* 已完成的替代验证；
* 可能存在的风险。

---

## 21. Git 默认分支

仓库默认分支通常为：

```text
main
```

或者：

```text
master
```

本文使用 `<default-branch>` 表示实际默认分支。

确认默认分支：

```bash
git remote show origin
```

或者：

```bash
git branch -a
```

默认分支必须保持：

* 可以检出；
* 可以构建；
* 可以运行；
* 测试通过；
* 不包含未完成代码；
* 不包含临时实验；
* 不包含 Agent 中间提交；
* 不作为多 Agent 直接工作分支。

禁止直接在 `main` 或 `master` 上开发。

禁止向默认分支强制推送：

```bash
git push --force
git push --force-with-lease
```

---

## 22. 开始任务前同步默认分支

```bash
git switch <default-branch>
git fetch origin
git pull --ff-only origin <default-branch>
```

使用 `--ff-only` 避免意外产生无意义的 Merge Commit。

如果本地默认分支存在未推送提交或与远程分叉，应先确认原因，不得直接强制覆盖。

---

## 23. 分支命名

所有新增、修复、重构和维护任务都必须创建独立分支。

| 类型    | 格式                    | 示例                             |
| ----- | --------------------- | ------------------------------ |
| 新功能   | `feat/<topic>`        | `feat/order-export`            |
| 缺陷修复  | `fix/<topic>`         | `fix/login-timeout`            |
| 紧急修复  | `hotfix/<topic>`      | `hotfix/payment-failure`       |
| 重构    | `refactor/<topic>`    | `refactor/task-service`        |
| 性能优化  | `perf/<topic>`        | `perf/query-cache`             |
| 测试    | `test/<topic>`        | `test/order-service`           |
| 文档    | `docs/<topic>`        | `docs/deployment-guide`        |
| 工程维护  | `chore/<topic>`       | `chore/update-dependencies`    |
| 构建调整  | `build/<topic>`       | `build/package-config`         |
| CI 调整 | `ci/<topic>`          | `ci/windows-build`             |
| 调查比对  | `investigate/<topic>` | `investigate/login-regression` |

分支名应：

* 使用小写字母；
* 使用短横线分隔；
* 表达实际任务；
* 避免无意义名称。

禁止：

```text
branch-1
test2
new-code
my-branch
agent1
```

---

## 24. 单人或单 Agent 工作流

只有一个开发者或 Agent 时，直接从默认分支创建任务分支：

```bash
git switch <default-branch>
git fetch origin
git pull --ff-only origin <default-branch>

git switch -c feat/order-export
```

完成修改后：

```bash
git status
git diff

git add <本次任务相关文件>
git diff --cached

git commit -m "feat(order): add export support"
```

推送远程：

```bash
git push -u origin feat/order-export
```

单 Agent 任务没有必要额外创建 Agent 子分支或集成分支。

---

## 25. 多 Agent 分支模型

多 Agent 并行任务推荐使用三级结构：

```text
默认分支
└── 任务分支
    ├── Agent 子分支 1
    ├── Agent 子分支 2
    └── Agent 子分支 3
```

示例：

```text
main
└── refactor/task-system
    ├── agent/task-system/api
    ├── agent/task-system/service
    ├── agent/task-system/frontend
    └── agent/task-system/tests
```

其中：

* `main` 或 `master` 是稳定分支；
* `refactor/task-system` 是本次任务集成分支；
* 每个 Agent 使用独立子分支；
* 每个 Agent 使用独立工作目录；
* Agent 分支完成后合并回任务分支；
* 任务分支验证后再合并到默认分支。

---

### 25.1 是否需要任务分支

以下情况建议使用任务分支：

* 多个 Agent 并行；
* 修改涉及多个模块；
* 前端、API、Service 和测试分别开发；
* 需要多轮集成；
* 不希望未完成代码接近默认分支。

以下情况通常不需要额外集成层：

* 只有一个 Agent；
* 修改范围很小；
* 没有并行需求；
* 一个分支可以独立完成。

---

## 26. 创建多 Agent 任务分支

基于最新默认分支创建任务分支：

```bash
git switch <default-branch>
git fetch origin
git pull --ff-only origin <default-branch>

git switch -c refactor/task-system
git push -u origin refactor/task-system
```

任务分支主要用于：

* 接收 Agent 子分支；
* 处理跨模块冲突；
* 运行集成测试；
* 保存完整任务结果。

多个 Agent 不得同时直接修改任务分支。

任务分支应由主 Agent、集成 Agent 或开发者维护。

---

## 27. 使用 Git Worktree

每个 Agent 必须拥有：

* 独立分支；
* 独立工作目录；
* 明确任务范围。

推荐使用 `git worktree`，不需要每个 Agent 重复 clone 仓库。

示例：

```bash
git worktree add \
  -b agent/task-system/api \
  ../project-agent-api \
  refactor/task-system

git worktree add \
  -b agent/task-system/service \
  ../project-agent-service \
  refactor/task-system

git worktree add \
  -b agent/task-system/frontend \
  ../project-agent-frontend \
  refactor/task-system

git worktree add \
  -b agent/task-system/tests \
  ../project-agent-tests \
  refactor/task-system
```

目录结构：

```text
workspace/
├── project/
├── project-agent-api/
├── project-agent-service/
├── project-agent-frontend/
└── project-agent-tests/
```

禁止：

* 多个 Agent 共用同一个目录；
* 多个 Agent 使用同一个分支；
* Agent 在工作期间切换到其他 Agent 分支；
* 多个 Agent 同时提交到任务分支；
* Agent 直接向默认分支提交。

---

## 28. 多 Agent 任务拆分

任务拆分应尽量减少文件重叠。

适合并行：

* API 层与 Service 层分别修改；
* 前端与后端分别修改；
* 不同业务模块分别修改；
* 功能实现和测试分别处理；
* 文档和代码分别处理。

不适合直接并行：

* 多个 Agent 同时重构同一核心文件；
* 多个 Agent 同时修改同一个模型；
* 一个 Agent 修改接口，另一个 Agent 未同步接口就修改调用方；
* 多个 Agent 同时修改数据库迁移；
* 多个 Agent 同时修改锁文件；
* 后续任务依赖前置设计尚未确定。

存在依赖时，应顺序执行：

```text
Agent A：定义 Domain 和 Service 接口
    ↓
合并到任务分支
    ↓
Agent B：实现 API 调用
Agent C：实现前端调用
Agent D：补充测试
```

不得为了并行而强行拆分存在明确依赖关系的工作。

---

## 29. Agent 工作要求

每个 Agent 开始前必须执行：

```bash
git branch --show-current
git status
```

工作过程中：

1. 只修改分配范围内的代码；
2. 不擅自扩大任务范围；
3. 不覆盖无法理解的修改；
4. 不随意删除注释；
5. 不随意删除日志；
6. 不修改默认分支；
7. 不提交缓存和构建产物；
8. 不执行破坏性 Git 操作；
9. 修改公共接口时同步更新调用方；
10. 完成后运行相关测试。

完成后提交：

```bash
git status
git diff

git add <相关文件>
git diff --cached

git commit -m "refactor(service): extract task business logic"
```

每个 Agent 应提供：

* 修改摘要；
* 修改文件；
* 测试结果；
* 未完成事项；
* 已知风险；
* 合并注意事项。

---

## 30. 提交信息规范

推荐使用 Conventional Commits：

```text
<type>(<scope>): <description>
```

示例：

```text
feat(order): add export endpoint
fix(auth): handle expired token
refactor(service): extract task logic
test(order): add validation tests
docs(api): update request examples
chore(deps): update dependencies
```

提交要求：

* 一个提交处理一个明确问题；
* 不混入无关格式化；
* 不提交调试日志；
* 不提交无意义大范围变动；
* 不使用模糊描述；
* 不擅自修改已共享提交历史。

---

## 31. 分支同步策略

### Agent 私有分支

Agent 私有分支可以在合并前 Rebase 到任务分支：

```bash
git fetch origin
git switch agent/task-system/service
git rebase refactor/task-system
```

解决冲突后：

```bash
git add <resolved-files>
git rebase --continue
```

无法确认冲突时：

```bash
git rebase --abort
```

然后交由集成 Agent 或开发者处理。

---

### 共享任务分支

任务分支一旦被多个 Agent 使用，应视为共享分支。

共享任务分支不建议执行改写历史的 Rebase。

同步默认分支时使用：

```bash
git fetch origin
git switch refactor/task-system
git merge origin/<default-branch>
```

不建议直接执行：

```bash
git pull
```

应明确使用：

```bash
git pull --ff-only
```

或者：

```bash
git fetch origin
git merge origin/<branch>
```

---

## 32. 已知正常版本和回归比对

当开发者确认某个 Git 版本正常时，可以基于该版本创建独立分支和工作目录，用于：

* 对比当前版本；
* 定位回归；
* 验证历史行为；
* 尝试修复；
* 从正常版本重新实现。

正常版本可以是：

* Commit SHA；
* Tag；
* 本地分支；
* 远程分支。

记录准确版本：

```bash
git rev-parse <known-good-ref>
```

查看版本：

```bash
git show --stat --oneline <known-good-ref>
```

---

### 32.1 创建正常版本工作目录

```bash
git worktree add \
  -b investigate/<topic>-known-good \
  ../project-known-good \
  <known-good-ref>
```

示例：

```bash
git worktree add \
  -b investigate/login-known-good \
  ../project-login-known-good \
  a1b2c3d4
```

该操作不得影响：

* `main`；
* `master`；
* 当前任务分支；
* 其他 Agent 工作目录。

---

### 32.2 仅用于比对

默认情况下，正常版本只作为参考。

```text
当前开发：
main
└── fix/login
    ├── agent/login/service
    └── agent/login/tests

历史比对：
a1b2c3d4
└── investigate/login-known-good
```

正常版本工作目录可以用于：

* 运行旧代码；
* 查看旧实现；
* 对比行为；
* 查找回归提交；
* 制作最小实验。

不得自动让所有 Agent 改为基于历史版本开发。

---

### 32.3 从正常版本重新开始

只有开发者明确决定从正常版本重新开发时，才创建新的任务分支：

```bash
git worktree add \
  -b fix/<topic>-from-known-good \
  ../project-<topic>-rebuild \
  <known-good-ref>
```

后续 Agent 基于该新任务分支：

```bash
git worktree add \
  -b agent/<topic>/service \
  ../project-<topic>-service \
  fix/<topic>-from-known-good

git worktree add \
  -b agent/<topic>/tests \
  ../project-<topic>-tests \
  fix/<topic>-from-known-good
```

是否从正常版本重新开始，必须由开发者明确决定。

---

### 32.4 比对命令

```bash
git diff <known-good-ref>..<task-branch>
```

```bash
git diff --stat <known-good-ref>..<task-branch>
```

```bash
git diff <known-good-ref>..<task-branch> -- path/to/module
```

```bash
git log --oneline <known-good-ref>..<task-branch>
```

```bash
git log -p -- path/to/file.py
```

```bash
git blame path/to/file.py
```

查看历史文件：

```bash
git show <known-good-ref>:path/to/file.py
```

恢复指定文件前先检查差异：

```bash
git diff <known-good-ref> -- path/to/file.py
```

恢复文件：

```bash
git restore \
  --source=<known-good-ref> \
  -- path/to/file.py
```

禁止未经检查就整体合并历史调查分支。

---

## 33. Agent 分支合并

由主 Agent、集成 Agent 或开发者统一合并。

进入任务分支：

```bash
git switch refactor/task-system
git status
```

逐个合并：

```bash
git merge --no-ff agent/task-system/service
```

测试通过后继续：

```bash
git merge --no-ff agent/task-system/api
```

然后：

```bash
git merge --no-ff agent/task-system/frontend
git merge --no-ff agent/task-system/tests
```

每合并一个分支后必须：

1. 检查 Diff；
2. 检查职责边界；
3. 检查是否出现重复实现；
4. 检查 API 是否包含业务逻辑；
5. 运行相关测试；
6. 确认没有覆盖其他 Agent 修改。

禁止一次性无检查地合并全部分支。

---

## 34. 冲突处理

出现冲突时，必须理解双方业务意图后处理。

禁止：

* 无条件选择 `ours`；
* 无条件选择 `theirs`；
* 删除看不懂的代码；
* 恢复整个文件覆盖其他修改；
* 跳过测试；
* 提交冲突标记。

处理后执行：

```bash
git diff --check
git status
```

确认不存在：

```text
<<<<<<<
=======
>>>>>>>
```

涉及公共接口、数据结构或业务规则的冲突，应由集成 Agent 或开发者决定。

---

## 35. 任务分支合并到默认分支

完成 Agent 集成后，在任务分支运行完整验证。

同步默认分支：

```bash
git fetch origin
git switch refactor/task-system
git merge origin/<default-branch>
```

执行验证：

```bash
pytest
npm run lint
npm run test
npm run build
```

查看最终改动：

```bash
git diff origin/<default-branch>...HEAD
git log --oneline origin/<default-branch>..HEAD
```

推送任务分支：

```bash
git push origin refactor/task-system
```

推荐流程：

```text
Agent 子分支
  → 任务分支
  → 集成测试
  → Pull Request
  → main / master
```

默认分支不得作为多 Agent 的直接集成场所。

---

## 36. 清理 Worktree 和临时分支

只有满足以下条件后才能清理：

* 修改已经提交；
* Agent 分支已经合并；
* 测试通过；
* 不再需要对应目录；
* 没有未跟踪的重要文件。

检查：

```bash
git worktree list
```

删除工作目录：

```bash
git worktree remove ../project-agent-api
git worktree remove ../project-agent-service
git worktree remove ../project-agent-frontend
git worktree remove ../project-agent-tests
```

删除已合并分支：

```bash
git branch -d agent/task-system/api
git branch -d agent/task-system/service
git branch -d agent/task-system/frontend
git branch -d agent/task-system/tests
```

清理记录：

```bash
git worktree prune
```

任务分支合并后：

```bash
git branch -d refactor/task-system
```

远程分支不再需要时：

```bash
git push origin --delete refactor/task-system
```

---

## 37. 禁止的 Git 操作

未经开发者明确授权，Agent 禁止执行：

```bash
git reset --hard
git clean -fd
git clean -fdx
git checkout -- .
git restore .
git push --force
git push --force-with-lease
git branch -D
git worktree remove --force
```

也禁止：

* 删除不属于当前任务的文件；
* 覆盖未知修改；
* 修改默认分支历史；
* 擅自删除远程分支；
* 擅自 Squash 他人提交；
* 在存在未提交修改时切换分支；
* 使用 `git add .` 提交未检查文件；
* 为查看历史版本而重置当前分支。

如确需破坏性操作，必须先说明：

* 原因；
* 影响范围；
* 可能丢失的数据；
* 恢复方案。

并获得开发者明确授权。

---

## 38. 依赖和锁文件

以下文件容易产生冲突：

* `package-lock.json`
* `pnpm-lock.yaml`
* `yarn.lock`
* `poetry.lock`
* `requirements.txt`
* 数据库迁移文件
* 全局配置文件
* CI 配置
* 构建脚本
* 路由注册文件
* 公共类型文件

原则上由一个 Agent 负责依赖调整。

如果多个 Agent 都需要新依赖，应记录需求，由集成 Agent 统一安装和更新锁文件。

每个 Worktree 可以拥有独立的：

* Python 虚拟环境；
* `node_modules`；
* 本地缓存；
* 构建产物；
* 测试临时文件。

这些内容通常不得提交到 Git，除非项目已有明确约定。

---

## 39. 最终交付要求

每次任务完成后，应提供以下信息。

### 修改摘要

说明完成了什么以及为什么修改。

### 主要文件

列出主要修改文件和职责。

### 分层说明

说明：

* API 层做了什么；
* Service 层做了什么；
* Repository 或 Client 做了什么；
* 是否新增 dataclass；
* 是否调整 Pydantic 或 Zod。

### 验证结果

列出实际执行的命令：

```text
pytest tests/test_example.py
npm run lint
npm run build
```

### 未执行验证

说明：

* 未执行的测试；
* 未执行原因；
* 已完成的替代验证；
* 可能风险。

### 风险和后续事项

说明：

* 已知限制；
* 兼容性风险；
* 未迁移历史代码；
* 需要人工确认的行为；
* 可能存在的合并冲突。

---

## 40. 提交前检查清单

* [ ] 当前不在 `main` 或 `master`
* [ ] 当前分支与任务匹配
* [ ] 已阅读适用的 `AGENTS.md`
* [ ] 工作区没有无关修改
* [ ] 规范冲突已经与开发者确认
* [ ] 没有擅自扩大任务范围
* [ ] API 层没有新增业务逻辑
* [ ] API 只调用 Service
* [ ] API 没有直接调用 Repository
* [ ] API 没有直接调用 Client
* [ ] API 没有直接提交队列任务
* [ ] Service 不依赖 FastAPI Request 或 Response
* [ ] Service 不返回 HTTP 响应字典
* [ ] 外部输入已经完成 Pydantic 校验
* [ ] 前端表单已经完成 Zod 校验
* [ ] 内部业务参数使用 dataclass
* [ ] 没有新增业务字典漫游
* [ ] 没有新增裸 `except`
* [ ] 新增注释使用简体中文
* [ ] 文档字符串使用简体中文
* [ ] 日志内容使用简体中文
* [ ] 没有无理由删除现有注释
* [ ] 没有误删 TODO 或兼容性说明
* [ ] Python 日志使用 `from loguru import logger`
* [ ] 业务代码没有新增 `print`
* [ ] 没有无理由删除关键日志
* [ ] 密码和配置处理符合项目约定
* [ ] 没有将仓库凭据传播到外部
* [ ] 没有提交无关缓存和构建产物
* [ ] 已检查 `git diff`
* [ ] 已检查 `git diff --cached`
* [ ] 已运行相关测试
* [ ] 已记录未执行的验证
* [ ] 提交信息清晰准确

---

## 41. 多 Agent 集成检查清单

* [ ] 每个 Agent 使用独立分支
* [ ] 每个 Agent 使用独立工作目录
* [ ] 每个 Agent 有明确职责
* [ ] 多个 Agent 没有同时修改任务分支
* [ ] 所有 Agent 修改均已提交
* [ ] Agent 分支已逐个检查
* [ ] Agent 分支已逐个合并
* [ ] 冲突已按业务意图处理
* [ ] 没有冲突标记残留
* [ ] API 层没有混入业务逻辑
* [ ] Service 层承担业务编排
* [ ] 前后端校验规则一致
* [ ] 公共接口保持一致
* [ ] 相关测试全部通过
* [ ] 前端构建成功
* [ ] 默认分支最新修改已同步
* [ ] 最终 Diff 已检查
* [ ] 临时 Worktree 未提前删除
* [ ] 任务分支可以安全提交 Pull Request

---

## 42. 已知正常版本检查清单

* [ ] 开发者已经确认正常版本
* [ ] 已记录准确 Commit SHA
* [ ] 正常版本使用独立 Worktree
* [ ] 没有移动 `main` 或 `master`
* [ ] 没有重置当前任务分支
* [ ] 已明确正常版本仅用于比对还是作为新基线
* [ ] 未经确认没有让所有 Agent 改用历史基线
* [ ] 恢复历史文件前已检查差异
* [ ] 没有直接整体合并历史调查分支
* [ ] 已记录不应回退的后续功能
* [ ] 已执行必要回归测试

---

## 43. 推荐开发流程

### 单 Agent

```text
main / master
  → feat|fix|refactor/<task>
  → 测试
  → Pull Request
  → main / master
```

### 多 Agent

```text
main / master
  → feat|fix|refactor/<task>
      → agent/<task>/domain
      → agent/<task>/service
      → agent/<task>/api
      → agent/<task>/frontend
      → agent/<task>/tests
  → 集成测试
  → Pull Request
  → main / master
```

### 出现回归，需要正常版本比对

```text
当前任务：
main / master
  → fix/<task>
      → agent/<task>/service
      → agent/<task>/tests

历史比对：
<known-good-commit>
  → investigate/<task>-known-good
```

### 开发者决定从正常版本重新开始

```text
<known-good-commit>
  → fix/<task>-from-known-good
      → agent/<task>/domain
      → agent/<task>/service
      → agent/<task>/api
      → agent/<task>/tests
  → 完整验证
  → Pull Request
  → main / master
```

是否从正常版本重新开始，必须由开发者明确决定。
