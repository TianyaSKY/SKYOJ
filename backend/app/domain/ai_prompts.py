"""LLM 提示词常量（AI 出题与测例脚本生成）。纯常量，无业务逻辑。"""

# AI 出题
PROBLEM_GENERATION_SYSTEM_SETTING = (
    "你是一个专业的算法竞赛出题人。请根据用户提供的背景 and 难度，设计一道高质量的编程题目。\n"
    "平台支持三种模式：\n"
    "1. ACM 模式：标准 I/O，严格文本比对。\n"
    "2. OOP 模式：实现特定接口/类，运行单元测试。\n"
    "3. Kaggle 模式：提交预测结果 CSV 文件，基于 Metric 评分。\n"
    "请根据题目性质选择最合适的模式。题目内容必须使用 Markdown 格式，包含："
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
        "task": "编写一个 Python 脚本，用于生成随机的输入数据（.in）和对应的标准答案（.out）。并直接放置在原始文件夹下",
        "rule": "脚本应根据题目约束生成多组测试数据（含边界与典型情况），数量与数据范围由题目描述自行合理推断。",
    },
    "oop": {
        "role": "自动化测试专家",
        "task": "编写一个单元测试脚本，用于验证学生提交的代码实现。",
        "rule": (
            "【重要】脚本必须包含/导入学生的代码。\n"
            '- 对于 C++: 使用 #include "solution.cpp"\n'
            "- 对于 Java: 假设学生类在同包下直接调用，或使用 import Solution;\n"
            "- 对于 Python: 使用 from solution import *\n"
            "严禁在脚本中自行实现题目要求的类，必须测试外部导入的实现。最后一行必须只打印一个 0-100 的整数分数。"
        ),
    },
    "kaggle": {
        "role": "数据科学竞赛裁判",
        "task": "编写一个评估脚本，用于对比学生的预测结果 and 已有的标准答案。",
        "rule": (
            "【重要】严禁在脚本中生成随机数据 or 创建 truth.csv。"
            "脚本应假设当前目录下已存在 truth.csv（老师上传）和 submission.csv（学生上传）。"
            "脚本只需读取这两个文件，计算指标（如 Accuracy/MSE），最后一行只打印一个 0-100 的整数分数。"
        ),
    },
}

TEST_SCRIPT_OUTPUT_FORMAT = {
    "code": "生成的完整代码字符串",
    "language": "脚本使用的编程语言 (python/java/cpp/c)",
}
