<template>
  <div class="doc-container">
    <el-card shadow="never">
      <div class="markdown-body">
        <h1>Kaggle 模式评测指南</h1>

        <h2>1. 提交方法</h2>
        <p>在 Kaggle 模式下，你不需要提交代码，而是提交一个包含预测结果的 <strong>CSV 文件</strong>。</p>
        <ul>
          <li>下载题目提供的测试集数据（通常为 <code>test.csv</code>）。</li>
          <li>在本地运行你的模型，生成预测结果。</li>
          <li>将结果保存为 CSV 格式，第一行通常是表头（如 <code>id,label</code>）。</li>
          <li>在题目详情页上传该 CSV 文件。</li>
        </ul>

        <h2>2. 判分逻辑</h2>
        <p>系统会解析你上传的 CSV 文件，并将其与后台的标准答案进行比对。评分通常基于特定的评价指标（Metric）。</p>
        <ul>
          <li><strong>准确率 (Accuracy)</strong>: 预测正确的样本数占总样本数的比例。</li>
          <li><strong>均方误差 (MSE)</strong>: 预测值与真实值差值的平方和的平均值（用于回归问题）。</li>
          <li><strong>F1-Score</strong>: 精确率和召回率的调和平均数。</li>
        </ul>
        <p>最终得分通常是 <code>Metric * 100</code> 或直接显示 Metric 值。</p>

        <h2>3. 注意事项</h2>
        <ul>
          <li><strong>格式必须严格一致</strong>：行数必须与测试集一致，ID 顺序必须对应。</li>
          <li><strong>表头</strong>：请检查是否需要包含表头（Header），通常题目会有说明。</li>
          <li><strong>文件大小</strong>：上传文件大小通常有限制（如 100MB）。</li>
        </ul>

        <h2>4. 评分示例</h2>
        <p>假设题目要求预测二分类标签（0 或 1），评价指标为准确率。</p>

        <h3>💯 满分 (Score: 1.0 / 100)</h3>
        <p>你的 CSV 文件中所有 ID 对应的预测值都与真实标签一致。</p>

        <h3>⚠️ 部分分 (Score: 0.85 / 85)</h3>
        <p>你的预测结果中有 85% 是正确的，15% 是错误的。</p>

        <h3>⚠️ 零分 / 低分</h3>
        <ul>
          <li><strong>格式错误</strong>：CSV 缺少列，或者 ID 不匹配，导致系统无法解析（通常会提示 Format Error）。</li>
          <li><strong>全错</strong>：预测结果与真实值完全相反（在二分类中较少见，除非故意）。</li>
        </ul>
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

h1 {
  font-size: 2em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: .3em;
}

h2 {
  font-size: 1.5em;
  border-bottom: 1px solid #eaecef;
  padding-bottom: .3em;
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
