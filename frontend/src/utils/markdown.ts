import MarkdownIt from 'markdown-it'
import mk from 'markdown-it-katex'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import 'katex/dist/katex.min.css'

const md: MarkdownIt = new MarkdownIt({
    html: false, // 关闭内联 HTML，防 XSS；题面渲染与编辑器预览共用此实例
    linkify: true,
    breaks: true,
    typographer: true,
    highlight: (str, lang): string => {
        if (lang && hljs.getLanguage(lang)) {
            try {
                return `<pre class="hljs"><code>${
                    hljs.highlight(str, {language: lang, ignoreIllegals: true}).value
                }</code></pre>`
            } catch (_) {
            }
        }
        return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
    },
})

// KaTeX 必须在 highlight 之后注册，否则公式中的下划线 / 星号会被 inline 规则提前吞掉
md.use(mk)

/**
 * 渲染 Markdown 为安全 HTML。
 * - 题面/草稿预览统一走此函数，避免各处独立初始化导致行为漂移（LaTeX、换行、XSS 配置不一致）。
 * - 出错时返回降级 HTML，调用方无需再 try/catch。
 */
export const renderMarkdown = (text: string | null | undefined): string => {
    if (!text || !String(text).trim()) return ''
    try {
        return md.render(text)
    } catch (err) {
        console.error('[markdown] render failed:', err)
        return `<p class="md-empty">Markdown 渲染失败</p>`
    }
}

export default md
