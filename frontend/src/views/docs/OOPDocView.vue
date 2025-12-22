<template>
  <div class="doc-container">
    <el-card shadow="never">
      <div class="markdown-body">
        <h1>OOP 模式评测指南</h1>

        <h2>1. 提交方法</h2>
        <p>OOP（面向对象编程）模式主要考察代码设计能力。你需要提交<strong>实现特定接口或类</strong>的代码。</p>
        <ul>
          <li>题目通常会提供一个<strong>接口定义</strong>（如 <code>interface Shape</code>）或<strong>基类</strong>。</li>
          <li>你需要编写一个或多个类来实现这些接口或继承基类。</li>
          <li>通常不需要编写 <code>main</code> 函数，系统会提供测试驱动代码来调用你的类。</li>
        </ul>

        <h2>2. 判分逻辑</h2>
        <p>系统会编译你的代码，并与测试驱动代码链接，然后运行一系列<strong>单元测试 (Unit Tests)</strong>。</p>
        <ul>
          <li><strong>编译错误 (CE)</strong>: 你的代码不符合接口规范，或存在语法错误。</li>
          <li><strong>通过 (Pass)</strong>: 通过了所有的单元测试用例。</li>
          <li><strong>失败 (Fail)</strong>: 某些单元测试未通过（断言失败）。</li>
        </ul>
        <p>得分通常取决于通过的单元测试数量。</p>

        <h2>3. 注意事项</h2>
        <ul>
          <li><strong>类名与包名</strong>：请严格遵守题目要求的类名和包名结构。</li>
          <li><strong>访问修饰符</strong>：注意 <code>public</code>, <code>private</code>, <code>protected</code> 的使用。</li>
          <li><strong>不要包含 main 函数</strong>：除非题目明确要求，否则不要提交包含 <code>main</code> 入口的代码，以免冲突。</li>
        </ul>

        <h2>4. 评分示例</h2>
        <p>题目：实现一个 <code>Rectangle</code> 类，包含 <code>getArea()</code> 方法。</p>

        <h3>💯 满分</h3>
        <pre><code>class Rectangle {
    private int width, height;
    public Rectangle(int w, int h) {
        this.width = w;
        this.height = h;
    }
    public int getArea() {
        return width * height;
    }
}</code></pre>
        <p>系统测试：<code>new Rectangle(3, 4).getArea()</code> 返回 <code>12</code>。测试通过。</p>

        <h3>⚠️ 部分分 / 零分</h3>
        <pre><code>class Rectangle {
    // ... 构造函数 ...
    public int getArea() {
        return width + height; // 逻辑错误
    }
}</code></pre>
        <p>系统测试：期望 <code>12</code>，实际返回 <code>7</code>。测试失败。</p>
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
h1, h2, h3 {
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
  line-height: 1.25;
}
h1 { font-size: 2em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
h3 { font-size: 1.25em; }
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
