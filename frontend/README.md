# frontend

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (
and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
    - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
    - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
    - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
    - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```

## TypeScript 开发与验收

前端源码、Vue `<script setup>`、测试和工具配置统一使用 TypeScript。共享配置启用 `strict: true`、`allowJs: false`，应用、Vitest 与 Node/Playwright 分别使用独立配置检查。

```sh
npm ci
npm run type-check          # 应用、单测、E2E 与配置的静态检查
npm run test:unit:coverage  # 单测及覆盖率基线门禁
npm run check               # 类型检查、单测、生产构建
npm run test:e2e            # 使用 Playwright 配置连接或启动前后端
```

CI 分别执行类型检查、覆盖率单测、构建和完整 E2E。覆盖率门槛来自迁移前实测：语句 74.04%、分支 59.11%、函数 43.58%、行 75.39%。真实后端 E2E 的隔离数据库准备方式见仓库 CI 工作流和 `backend/scripts/seed_e2e.py`。

API 响应类型按后端协议放在 `src/types/`；关键输入和不可信 WebSocket、用户缓存、AI 响应在 `src/schemas/` 通过 Zod 校验。Axios 响应拦截器返回解包后的 `Promise<T>`，调用方直接读取业务响应。捕获异常保持 `unknown`，显示消息前校验字段。新增 Vue 组件使用 `<script setup lang="ts">`，避免通过 `any` 或关闭类型检查绕过边界。
