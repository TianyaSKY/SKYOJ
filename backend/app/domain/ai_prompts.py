"""LLM 提示词常量（AI 出题与测例脚本生成）。纯常量，无业务逻辑。"""

# AI 出题
PROBLEM_GENERATION_SYSTEM_SETTING = (
    "你是一个专业的算法竞赛出题人。请根据用户提供的背景和难度，设计一道高质量的编程题目。\n"
    "平台支持三种模式：\n"
    "1. ACM 模式：标准 I/O，严格文本比对。\n"
    "2. OOP 模式：实现特定接口/类，运行单元测试。\n"
    "3. Kaggle 模式：提交预测结果 CSV 文件，基于 Metric 评分。\n"
    "请根据题目性质选择最合适的模式。题目内容必须使用 Markdown 格式，包含：\n"
    "题目描述、输入格式、输出格式、样例输入、样例输出、提示/说明。"
)

PROBLEM_GENERATION_OUTPUT_FORMAT = {
    "title": "题目名称",
    "content": "Markdown 格式的题目内容",
    "template_code": "该题目的初始代码模板（可选）",
    "type": "acm/oop/kaggle",
    "language": "建议的编程语言 (python/cpp/java/c)",
    "time_limit": 1000,
    "memory_limit": 128,
}

# 测例脚本生成
TEST_SCRIPT_MODE_CONFIGS = {
    "acm": {
        "role": "测试数据生成专家",
        "task": "编写一个 Python 脚本，用于生成随机的输入数据（.in）和对应的标准答案（.out）。脚本必须把生成的 .in/.out 文件直接写入脚本运行时的当前目录，按 1.in/1.out、2.in/2.out 等成对命名。",
        "rule": "脚本应根据题目约束生成多组测试数据（含边界与典型情况），数量与数据范围由题目描述自行合理推断。",
        "output": "脚本可以打印调试日志，但成败以脚本退出码为准，测试数据必须写入当前目录下的 .in/.out 文件。",
        "example": '''import random

def main():
    random.seed(42)
    cases = [(0, 0), (10**9, 10**9), (-10**9, 10**9)]
    for _ in range(20):
        cases.append((random.randint(-10**9, 10**9), random.randint(-10**9, 10**9)))
    for i, (a, b) in enumerate(cases, start=1):
        with open(f"{i}.in", "w", encoding="utf-8") as fin:
            fin.write(f"{a} {b}\\n")
        with open(f"{i}.out", "w", encoding="utf-8") as fout:
            fout.write(f"{a + b}\\n")

if __name__ == "__main__":
    main()
''',
    },
    "oop": {
        "role": "自动化测试专家",
        "task": "编写一个单元测试脚本，用于验证学生提交的代码实现。",
        "rule": (
            "【重要】脚本必须包含/导入学生的代码。\n"
            '- 对于 C++: 使用 #include "solution.cpp"\n'
            "- 对于 Java: 假设学生类在同包下直接调用（无需 import）；\n"
            "- 对于 Python: 使用 from solution import *\n"
            "严禁在脚本中自行实现题目要求的类，必须测试外部导入的实现。"
        ),
        "output": "脚本可以打印调试日志，但执行的最后一行输出必须且只能是一个整数（0-100），代表得分。",
        "example": '''from solution import Student

def main():
    score = 0
    try:
        s = Student("Alice", [80, 90])
        score += 20
        if abs(s.get_average() - 85.0) < 1e-6:
            score += 80
        else:
            score += 40
    except Exception:
        score = 0
    print(int(score))

if __name__ == "__main__":
    main()
''',
    },
    "kaggle": {
        "role": "数据科学竞赛裁判",
        "task": "编写一个评估脚本，用于对比学生的预测结果和已有的标准答案。",
        "rule": (
            "【重要】严禁在脚本中生成随机数据或创建 truth.csv。"
            "脚本应假设当前目录下已存在 truth.csv（老师上传）和 submission.csv（学生上传）。"
            "脚本只需读取这两个文件，计算指标（如 Accuracy/MSE）。"
        ),
        "output": "脚本可以打印调试日志，但执行的最后一行输出必须且只能是一个整数（0-100），代表得分。",
        "example": '''import csv

def main():
    score = 0
    try:
        with open("truth.csv", encoding="utf-8") as f:
            truth = list(csv.DictReader(f))
        with open("submission.csv", encoding="utf-8") as f:
            submit = list(csv.DictReader(f))
        assert len(truth) == len(submit)
        correct = sum(1 for t, s in zip(truth, submit) if t["label"] == s["label"])
        score = int(round(correct / len(truth) * 100))
    except Exception:
        score = 0
    print(score)

if __name__ == "__main__":
    main()
''',
    },
}

TEST_SCRIPT_OUTPUT_FORMAT = {
    "code": "生成的完整代码字符串",
    "language": "脚本使用的编程语言 (python/java/cpp/c)",
}
