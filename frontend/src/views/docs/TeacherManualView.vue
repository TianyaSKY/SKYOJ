<template>
  <div class="teacher-manual-container">
    <div class="markdown-body">
      <h1>教师操作手册 (内部文档)</h1>
      <p>本文档仅供教师查阅，包含 ACM、OOP、Kaggle 题目的录入指南，以及判题脚本（打分）的示例代码和推荐解答代码格式。</p>

      <h2>1. 题目录入指南</h2>

      <h3>1.1 基础配置</h3>
      <ul>
        <li><strong>标题</strong>: 题目名称。</li>
        <li><strong>类型</strong>:
          <ul>
            <li><strong>ACM</strong>: 标准 I/O，严格文本比对。</li>
            <li><strong>OOP</strong>: 实现特定接口/类，运行单元测试。</li>
            <li><strong>Kaggle</strong>: 提交预测结果 CSV 文件，基于 Metric 评分。</li>
          </ul>
        </li>
        <li><strong>允许语言</strong>: 教师可以指定该题目允许学生使用的编程语言（如仅限 Python，或 Python + C++）。</li>
        <li><strong>时间/内存限制</strong>: 判题时的资源限制。</li>
        <li><strong>默认模板代码</strong>: 提供给学生的初始代码框架。</li>
      </ul>

      <h3>1.2 ACM 模式题目</h3>
      <p>ACM 模式通常为标准输入输出判题，适用于算法竞赛。</p>
      <ul>
        <li><strong>描述信息</strong>: 包含题目描述、输入描述、输出描述、样例等。</li>
        <li><strong>测试数据</strong>:
          <ul>
            <li>上传 <code>.zip</code> 压缩包。</li>
            <li>包内文件结构应为平铺（无文件夹），成对出现：<code>1.in</code>, <code>1.out</code>, <code>2.in</code>, <code>2.out</code>...</li>
          </ul>
        </li>
      </ul>

      <h3>1.3 OOP 模式题目 (面向对象设计)</h3>
      <p>OOP 模式侧重于类的设计、接口实现与代码复用。</p>
      <ul>
        <li><strong>判题机制</strong>: 教师需上传单元测试文件（如 Java 的 JUnit 测试类，Python 的 <code>unittest</code> 文件）。</li>
        <li><strong>AICase 工具</strong>: 推荐使用管理后台的 "AICase" 功能。它可以根据题目描述自动生成测试脚本，并自动完成测试点的部署。</li>
      </ul>

      <h3>1.4 Kaggle 模式题目 (数据科学/机器学习)</h3>
      <p>Kaggle 模式用于数据分析与模型预测任务。</p>
      <ul>
        <li><strong>数据集</strong>: 教师需在题目描述中提供 <code>train.csv</code> 和 <code>test.csv</code> 的下载链接。</li>
        <li><strong>评分标准</strong>: 教师需上传 <code>truth.csv</code> (包含测试集 ID 和正确标签)。</li>
        <li><strong>判题脚本</strong>: 使用 "AICase" 生成或手动编写 Python 脚本，读取 <code>truth.csv</code> 和学生提交的 <code>submission.csv</code> 计算得分。</li>
      </ul>

      <hr>

      <h2>2. AICase 自动化工具</h2>
      <p>在题目管理页面，点击题目右侧的 <strong>"AICase"</strong> 按钮，可以进入 AI 辅助测试数据生成流程：</p>
      <ol>
        <li><strong>配置方向</strong>: 输入对测试数据的具体要求（如：数据规模、边界条件）。</li>
        <li><strong>生成脚本</strong>: AI 会根据题目类型和要求，自动编写 Python/Java 测试脚本。</li>
        <li><strong>执行生成</strong>: 点击执行，系统会自动运行脚本生成测试点（ACM）或部署评估环境（OOP/Kaggle）。</li>
      </ol>

      <hr>

      <h2>3. 打分示例代码 (Special Judge / Checker)</h2>
      <p>当标准对比（diff）无法满足需求时，需要编写评估脚本。脚本最后一行必须输出 0-100 的整数分数。</p>

      <h3>Python OOP 示例</h3>
      <pre><code class="language-python">from solution import Student

def test():
    score = 0
    try:
        s = Student("Alice", [80, 90])
        score += 20
        if abs(s.get_average() - 85) < 1e-6:
            score += 80
    except:
        score = 0
    finally:
        print(int(score))

if __name__ == '__main__':
    test()
</code></pre>

      <h3>Kaggle 评估示例</h3>
      <pre><code class="language-python">import pandas as pd
import numpy as np

try:
    truth = pd.read_csv('truth.csv')
    submit = pd.read_csv('submission.csv')
    # 计算准确率
    correct = (truth['label'] == submit['label']).sum()
    score = (correct / len(truth)) * 100
except:
    score = 0
finally:
    print(int(score))
</code></pre>
    </div>
  </div>
</template>

<style scoped>
.teacher-manual-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  font-size: 16px;
  line-height: 1.5;
  word-wrap: break-word;
}

.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

.markdown-body h1 {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body h2 {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

.markdown-body h3 {
  font-size: 1.25em;
}

.markdown-body ul, .markdown-body ol {
  padding-left: 2em;
}

.markdown-body code {
  padding: 0.2em 0.4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(27, 31, 35, 0.05);
  border-radius: 3px;
  font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
}

.markdown-body pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: #f6f8fa;
  border-radius: 3px;
}

.markdown-body pre code {
  display: inline;
  padding: 0;
  margin: 0;
  overflow: visible;
  line-height: inherit;
  word-wrap: normal;
  background-color: transparent;
  border: 0;
}

.markdown-body hr {
  height: 0.25em;
  padding: 0;
  margin: 24px 0;
  background-color: #e1e4e8;
  border: 0;
}
</style>
