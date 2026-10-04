<template>
  <div class="doc-container">
    <el-card shadow="never">
      <div class="markdown-body">
        <h1>ACM 模式评测指南</h1>

        <h2>1. 提交方法</h2>
        <p>
          在 ACM 模式下，你需要提交一份完整的源代码文件（如 <code>.cpp</code>, <code>.py</code>,
          <code>.java</code>）。程序必须从<strong>标准输入 (stdin)</strong>
          读取数据，并将结果输出到<strong>标准输出 (stdout)</strong>。
        </p>
        <ul>
          <li>
            <strong>C++</strong>: 使用 <code>cin</code> / <code>cout</code> 或 <code>scanf</code> /
            <code>printf</code>。
          </li>
          <li>
            <strong>Python</strong>: 使用 <code>input()</code> 读取，<code>print()</code> 输出。
          </li>
          <li>
            <strong>Java</strong>: 使用 <code>Scanner</code> 或
            <code>BufferedReader</code> 读取，<code>System.out.println</code>
            输出。
          </li>
        </ul>

        <h2>2. 判分逻辑</h2>
        <p>系统会将你的程序输出与标准答案进行<strong>严格的文本比对</strong>。</p>
        <ul>
          <li>
            <strong>Accepted (AC)</strong>: 你的输出与标准答案完全一致（忽略行末空格和文末换行）。
          </li>
          <li><strong>Wrong Answer (WA)</strong>: 输出结果错误。</li>
          <li><strong>Time Limit Exceeded (TLE)</strong>: 程序运行时间超过了题目限制。</li>
          <li><strong>Memory Limit Exceeded (MLE)</strong>: 程序使用的内存超过了题目限制。</li>
          <li><strong>Runtime Error (RE)</strong>: 程序运行时崩溃（如数组越界、除以零）。</li>
        </ul>

        <h2>3. 注意事项</h2>
        <ul>
          <li>不要输出任何提示性文字（如 "Please input a number:"），否则会被判 WA。</li>
          <li>注意数据范围，选择合适的数据类型（如 C++ 中 <code>long long</code>）。</li>
          <li>Java 类名必须为 <code>Main</code>。</li>
        </ul>

        <h2>4. 评分示例</h2>

        <h3>💯 满分 (Accepted)</h3>
        <p>题目：计算 A + B。</p>
        <pre><code># Python
import sys

for line in sys.stdin:
    a, b = map(int, line.split())
    print(a + b)</code></pre>
        <p>输入：<code>1 2</code><br />输出：<code>3</code> (与答案一致)</p>

        <h3>⚠️ 零分 (Wrong Answer)</h3>
        <pre><code># Python
a, b = map(int, input().split())
print(a * b) # 逻辑错误</code></pre>
        <p>输入：<code>1 2</code><br />输出：<code>2</code> (答案应为 3)</p>

        <h3>⚠️ 零分 (Time Limit Exceeded)</h3>
        <pre><code># Python
while True: pass # 死循环</code></pre>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.doc-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px;
}

.markdown-body {
  line-height: 1.6;
}

h1,
h2,
h3 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}

h1 {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

h2 {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: 0.3em;
}

h3 {
  font-size: 1.25em;
}

pre {
  background-color: #f6f8fa;
  padding: 16px;
  border-radius: 6px;
  overflow: auto;
}

code {
  font-family: monospace;
}
</style>
