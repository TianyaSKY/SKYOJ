<template>
  <div class="teacher-manual-container">
    <div class="markdown-body">
      <h1>教师操作手册 (内部文档)</h1>
      <p>本文档仅供教师查阅，包含 ACM、OOP、Kaggle 题目的录入指南，以及判题脚本（打分）的示例代码和推荐解答代码格式。</p>

      <h2>1. 题目录入指南</h2>

      <h3>1.1 ACM 模式题目</h3>
      <p>ACM 模式通常为标准输入输出判题，适用于算法竞赛。</p>
      <ul>
        <li><strong>基本信息</strong>:
          <ul>
            <li><strong>标题</strong>: 题目名称</li>
            <li><strong>时间限制</strong>: 通常为 1000ms</li>
            <li><strong>内存限制</strong>: 通常为 128MB or 256MB</li>
          </ul>
        </li>
        <li><strong>描述信息</strong>:
          <ul>
            <li><strong>题目描述</strong>: 详细的背景与要求。</li>
            <li><strong>输入描述</strong>: 数据的输入格式（如：第一行包含一个整数 N...）。</li>
            <li><strong>输出描述</strong>: 期望的输出格式。</li>
            <li><strong>样例</strong>: 提供至少一组公开的 Input/Output 样例。</li>
          </ul>
        </li>
        <li><strong>测试数据</strong>:
          <ul>
            <li>上传 <code>.zip</code> 压缩包。</li>
            <li>包内文件结构应为平铺（无文件夹），成对出现：<code>1.in</code>, <code>1.out</code>, <code>2.in</code>, <code>2.out</code>...</li>
          </ul>
        </li>
      </ul>

      <h3>1.2 OOP 模式题目 (面向对象设计)</h3>
      <p>OOP 模式侧重于类的设计、接口实现与代码复用。</p>
      <ul>
        <li><strong>题目设置</strong>:
          <ul>
            <li><strong>类型</strong>: 选择 "OOP"</li>
            <li><strong>模板代码</strong>: 提供基础框架代码（Skeleton Code），学生在此基础上完成填空。</li>
          </ul>
        </li>
        <li><strong>判题机制</strong>:
          <ul>
            <li><strong>单元测试</strong>: 教师需上传单元测试文件（如 Java 的 java 测试类，Python 的 <code>py</code> 文件）。</li>
            <li>系统会将学生的提交与单元测试文件编译/运行，根据通过的测试用例数量给分。</li>
          </ul>
        </li>
      </ul>

      <h3>1.3 Kaggle 模式题目 (数据科学/机器学习)</h3>
      <p>Kaggle 模式用于数据分析与模型预测任务。</p>
      <ul>
        <li><strong>题目设置</strong>:
          <ul>
            <li><strong>类型</strong>: 选择 "Kaggle"</li>
            <li><strong>数据集</strong>: 上传 <code>train.csv</code> (训练集) 和 <code>test.csv</code> (测试集，不含标签)。</li>
          </ul>
        </li>
        <li><strong>评分标准</strong>:
          <ul>
            <li><strong>评价指标</strong>: 选择 Accuracy, MSE, F1-Score, AUC 等。</li>
            <li><strong>答案文件</strong>: 上传 <code>solution.csv</code> (包含测试集 ID 和正确标签/预测值)。</li>
            <li>系统会自动比对学生提交的 CSV 与 <code>solution.csv</code> 计算得分。</li>
          </ul>
        </li>
      </ul>

      <hr>

      <h2>2. 打分示例代码 (Special Judge / Checker)</h2>
      <p>当标准对比（diff）无法满足需求时（例如题目有多个正确答案，或允许浮点误差），需要编写 Special Judge (SPJ) 脚本。</p>

      <h3>Python OOP 示例</h3>
      <p>此脚本接收用户完成的类/函数/接口，返回 0-100 的分数或状态。</p>
      <pre><code class="language-python">from solution import Student

def test():
    score = 0
    error_msg = None

    try:
        # 1. 构造函数是否可正常创建对象（10 分）
        s = Student("Alice", [80, 90])
        score += 10

        # 2. 初始成绩是否被正确保存（10 分）
        if hasattr(s, "grades") and s.grades == [80, 90]:
            score += 10

        # 3. get_average 方法存在并可调用（10 分）
        avg = s.get_average()
        score += 10

        # 4. 初始平均分计算是否正确（20 分）
        if abs(avg - 85) < 1e-6:
            score += 20

        # 5. add_grade 是否能正确添加成绩（20 分）
        s.add_grade(70)
        if s.grades == [80, 90, 70]:
            score += 20

        # 6. 添加成绩后平均分是否正确（30 分）
        avg = s.get_average()
        if abs(avg - 80) < 1e-6:
            score += 30

    except Exception as e:
        error_msg = str(e)
        score = 0

    finally:
        if error_msg:
            print(f"error: {error_msg}")
        print(score)

if __name__ == '__main__':
    test()
</code></pre>

      <h3>Kaggle 代码示例</h3>
      <pre><code class="language-python">import pandas as pd
import numpy as np

score = 0
error_msg = None

try:
    # 1. 文件存在性（20 分）
    truth = pd.read_csv('truth.csv')
    submit = pd.read_csv('submission.csv')
    score += 20

    # 2. 表头检查（不通过直接 0 分）
    if list(truth.columns) != ['id', 'price']:
        score = 0
        raise ValueError('truth header mismatch')

    if list(submit.columns) != ['id', 'price']:
        score = 0
        raise ValueError('submission header mismatch')

    # 3. id 对齐（20 分）
    merged = truth.merge(submit, on='id', suffixes=('_true', '_pred'))
    if len(merged) != len(truth):
        raise ValueError('id mismatch')
    score += 20

    # 4. 数值合法性（20 分）
    if not np.issubdtype(merged['price_pred'].dtype, np.number):
        raise ValueError('price not numeric')
    score += 20

    # 5. RMSE 计算（最多 40 分）
    rmse = np.sqrt(((merged['price_true'] - merged['price_pred']) ** 2).mean())
    perf_score = max(0, min(40, 40 - rmse / 2500))
    score += perf_score

except Exception as e:
    error_msg = str(e)
    score = 0

finally:
    if error_msg:
        print(f"error: {error_msg}")
    print(int(score))
</code></pre>

      <hr>

      <h2>3. 推荐代码 (Standard Solution)</h2>
      <p>建议在题目描述中或题解部分提供标准解答，供学生参考。</p>

      <h3>ACM - A+B Problem (Python)</h3>
      <pre><code class="language-python">import sys

if __name__ == "__main__":
    for line in sys.stdin:
        if not line:
            break
        parts = line.split()
        if len(parts) < 2:
            continue
        a, b = map(int, parts)
        print(a + b)</code></pre>

      <h3>OOP - 银行账户类 (Java)</h3>
      <pre><code class="language-java">public class BankAccount {
    private double balance;

    public BankAccount(double initialBalance) {
        this.balance = initialBalance;
    }

    public void deposit(double amount) {
        if (amount > 0) {
            this.balance += amount;
        }
    }

    public boolean withdraw(double amount) {
        if (amount > 0 && this.balance >= amount) {
            this.balance -= amount;
            return true;
        }
        return false;
    }

    public double getBalance() {
        return balance;
    }
}</code></pre>

      <h3>Kaggle - 简单线性回归 (Python/Scikit-Learn)</h3>
      <pre><code class="language-python">import pandas as pd
from sklearn.linear_model import LinearRegression

# 读取数据
train_df = pd.read_csv('train.csv')
test_df = pd.read_csv('test.csv')

# 特征工程
X_train = train_df[['feature1', 'feature2']]
y_train = train_df['target']
X_test = test_df[['feature1', 'feature2']]

# 模型训练
model = LinearRegression()
model.fit(X_train, y_train)

# 预测
predictions = model.predict(X_test)

# 生成提交文件
submission = pd.DataFrame({
    'id': test_df['id'],
    'target': predictions
})
submission.to_csv('submission.csv', index=False)</code></pre>
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

.markdown-body ul {
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
