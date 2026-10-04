// @vitest-environment node
import { readdirSync, readFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import ts from 'typescript'
import { expect, it } from 'vitest'

const src = fileURLToPath(new URL('../../', import.meta.url))
function sources(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name === '__tests__') return []
    const path = join(directory, entry.name)
    return entry.isDirectory() ? sources(path) : /\.(ts|vue)$/.test(path) ? [path] : []
  })
}

it('生产代码只有 API 层和认证 Store 可以依赖 request 客户端', () => {
  const violations: string[] = []
  for (const path of sources(src)) {
    const local = relative(src, path).replaceAll('\\', '/')
    if (local.startsWith('api/') || local.startsWith('stores/') || local === 'utils/request.ts')
      continue
    const content = readFileSync(path, 'utf8')
    const script = path.endsWith('.vue')
      ? [...content.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)]
          .map((match) => match[1])
          .join('\n')
      : content
    const source = ts.createSourceFile(path, script, ts.ScriptTarget.Latest, true)
    const check = (node: ts.Node) => {
      let target: ts.Expression | undefined
      if (ts.isImportDeclaration(node) || ts.isExportDeclaration(node))
        target = node.moduleSpecifier
      if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword)
        target = node.arguments[0]
      if (target && ts.isStringLiteral(target)) {
        const dependency = target.text.startsWith('@/')
          ? resolve(src, target.text.slice(2))
          : resolve(dirname(path), target.text)
        if (dependency.replace(/\.ts$/, '') === resolve(src, 'utils/request'))
          violations.push(`${local}: ${target.text}`)
      }
      ts.forEachChild(node, check)
    }
    check(source)
  }
  expect(violations, '页面和组件通过 src/api 调用后端；测试可注入 request adapter 或 mock').toEqual(
    [],
  )
})
