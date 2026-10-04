import { afterEach, describe, expect, it, vi } from 'vitest'
import hljs from 'highlight.js'
import md, { renderMarkdown } from '../markdown'

afterEach(() => vi.restoreAllMocks())
describe('题面 Markdown 的类型迁移兼容性', () => {
  it.each([null, undefined, '', ' \n '])('空内容 %j 渲染为空', (content) => {
    expect(renderMarkdown(content)).toBe('')
  })
  it('保留标题、公式和代码高亮', () => {
    const html = renderMarkdown('# 解法\n\n$x_1$\n\n```python\nprint(1)\n```')
    expect(html).toContain('<h1>解法</h1>')
    expect(html).toContain('katex')
    expect(html).toContain('hljs')
    expect(html).toContain('hljs-built_in')
  })
  it('未知代码语言仍转义代码，原始 HTML 不能作为脚本执行', () => {
    const html = renderMarkdown(
      '```unknown-lang\n<script>alert(1)</script>\n```\n\n<script>alert(2)</script>',
    )
    expect(html).not.toContain('<script>')
    expect(html).toContain('&lt;script&gt;')
  })
  it('高亮失败时保留已转义的代码', () => {
    vi.spyOn(hljs, 'highlight').mockImplementation(() => {
      throw new Error('高亮失败')
    })
    expect(renderMarkdown('```python\n<script>\n```')).toContain('&lt;script&gt;')
  })
  it('渲染失败时返回降级内容并保留诊断日志', () => {
    vi.spyOn(md, 'render').mockImplementation(() => {
      throw new Error('渲染失败')
    })
    const diagnostic = vi.spyOn(console, 'error').mockImplementation(() => {})
    expect(renderMarkdown('题面')).toBe('<p class="md-empty">Markdown 渲染失败</p>')
    expect(diagnostic).toHaveBeenCalledWith('[markdown] render failed:', expect.any(Error))
  })
})
