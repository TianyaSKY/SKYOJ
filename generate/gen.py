import os
import random
import string
import math
import shutil
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Enum, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base

# =================配置区域=================

# 1. 数据库连接地址 (请根据你的实际情况修改)

DB_URI = 'mysql+pymysql://root:root@localhost:3306/oj_db'

# 2. 测试用例存储路径
BASE_TEST_CASE_PATH = './data/test_cases'

# =========================================

# 定义 SQLAlchemy 基类
Base = declarative_base()


# 重新定义 Problem 模型以匹配数据库表结构 (脱离 Flask-SQLAlchemy)
class Problem(Base):
    __tablename__ = 'problems'

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(Enum('acm', 'oop', 'kaggle'), nullable=False, default='acm')
    language = Column(Enum('python', 'java', 'c', 'cpp'), nullable=False, default='python')
    time_limit = Column(Integer, default=1000)
    memory_limit = Column(Integer, default=128)
    test_case_path = Column(String(500))
    template_code = Column(Text)
    created_at = Column(DateTime, default=datetime.now)


def ensure_dir(directory):
    if os.path.exists(directory):
        # 可选：如果你想每次运行都清空旧数据，取消下面注释
        # shutil.rmtree(directory)
        pass
    if not os.path.exists(directory):
        os.makedirs(directory)


# ==========================================
# 题目生成逻辑 (中文版 + 生成器)
# ==========================================

def get_problems_data():
    """返回题目列表配置，包含元数据和数据生成函数"""

    # 辅助：生成 Markdown 描述
    def mk_desc(desc, input_fmt, output_fmt):
        return f"""
### 题目描述
{desc}

### 输入格式
{input_fmt}

### 输出格式
{output_fmt}
"""

    # --- 1. A + B ---
    def gen_a_plus_b():
        a, b = random.randint(1, 1000), random.randint(1, 1000)
        return f"{a} {b}", f"{a + b}"

    # --- 2. 数组最大值 ---
    def gen_max():
        n = random.randint(5, 50)
        arr = [random.randint(1, 10000) for _ in range(n)]
        return f"{n}\n" + " ".join(map(str, arr)), f"{max(arr)}"

    # --- 3. 字符串反转 ---
    def gen_reverse():
        s = ''.join(random.choices(string.ascii_letters, k=random.randint(5, 20)))
        return s, s[::-1]

    # --- 4. 阶乘计算 ---
    def gen_factorial():
        n = random.randint(0, 12)
        return f"{n}", f"{math.factorial(n)}"

    # --- 5. 判定质数 ---
    def gen_prime():
        n = random.randint(1, 500)
        is_prime = True
        if n < 2: is_prime = False
        for i in range(2, int(math.sqrt(n)) + 1):
            if n % i == 0: is_prime = False
        return f"{n}", "Yes" if is_prime else "No"

    # --- 6. 斐波那契数列 ---
    def gen_fib():
        n = random.randint(0, 30)

        def fib(x):
            if x <= 1: return x
            a, b = 0, 1
            for _ in range(2, x + 1): a, b = b, a + b
            return b

        return f"{n}", f"{fib(n)}"

    # --- 7. 统计元音 ---
    def gen_vowels():
        s = ''.join(random.choices(string.ascii_lowercase, k=random.randint(10, 50)))
        cnt = sum(1 for c in s if c in 'aeiou')
        return s, f"{cnt}"

    # --- 8. 奇偶校验 ---
    def gen_odd_even():
        n = random.randint(1, 10000)
        return f"{n}", "Even" if n % 2 == 0 else "Odd"

    # --- 9. 数组排序 ---
    def gen_sort():
        n = random.randint(5, 20)
        arr = [random.randint(1, 100) for _ in range(n)]
        return f"{n}\n" + " ".join(map(str, arr)), " ".join(map(str, sorted(arr)))

    # --- 10. 寻找缺失数字 ---
    def gen_missing():
        n = random.randint(5, 20)
        full = list(range(n + 1))
        removed = full.pop(random.randint(0, n))
        random.shuffle(full)
        return f"{n}\n" + " ".join(map(str, full)), f"{removed}"

    # --- 11. 闰年判断 ---
    def gen_leap():
        y = random.randint(1900, 2100)
        leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
        return f"{y}", "Yes" if leap else "No"

    # --- 12. 字符计数 ---
    def gen_char_count():
        s = ''.join(random.choices(string.ascii_lowercase, k=random.randint(10, 30)))
        t = random.choice(string.ascii_lowercase)
        return f"{s}\n{t}", f"{s.count(t)}"

    # --- 13. 回文串判定 ---
    def gen_palindrome():
        if random.random() > 0.5:
            half = ''.join(random.choices(string.ascii_lowercase, k=5))
            s = half + half[::-1]
        else:
            s = ''.join(random.choices(string.ascii_lowercase, k=10))
        return s, "Yes" if s == s[::-1] else "No"

    # --- 14. 最大公约数 (GCD) ---
    def gen_gcd():
        a, b = random.randint(1, 1000), random.randint(1, 1000)
        return f"{a} {b}", f"{math.gcd(a, b)}"

    # --- 15. 温度转换 (C to F) ---
    def gen_temp():
        c = random.randint(-20, 100)
        return f"{c}", f"{int(c * 9 / 5 + 32)}"

    # --- 16. 判断平方数 ---
    def gen_square():
        if random.random() > 0.5:
            base = random.randint(0, 100)
            n = base * base
        else:
            n = random.randint(2, 10000)
            if int(math.sqrt(n)) ** 2 == n: n += 1
        is_sq = int(math.sqrt(n)) ** 2 == n
        return f"{n}", "True" if is_sq else "False"

    # --- 17. 数组去重计数 ---
    def gen_unique_count():
        n = random.randint(5, 20)
        arr = [random.randint(1, 10) for _ in range(n)]
        return f"{n}\n" + " ".join(map(str, arr)), f"{len(set(arr))}"

    # --- 18. 绝对值 ---
    def gen_abs():
        n = random.randint(-1000, 1000)
        return f"{n}", f"{abs(n)}"

    # --- 19. 简单的密码 (Caesar shift 1) ---
    def gen_caesar():
        s = ''.join(random.choices(string.ascii_lowercase, k=10))
        # 简单位移，z变a
        res = ''.join([chr(ord('a') + (ord(c) - ord('a') + 1) % 26) for c in s])
        return s, res

    # --- 20. 模运算 ---
    def gen_mod():
        a = random.randint(1, 1000)
        b = random.randint(1, 1000)
        return f"{a} {b}", f"{a % b}"

    # 题目列表
    problems = [
        {"title": "A + B 问题", "func": gen_a_plus_b,
         "desc": mk_desc("计算两个整数 A 和 B 的和。", "一行包含两个整数 A 和 B。", "输出 A + B 的结果。")},
        {"title": "数组最大值", "func": gen_max,
         "desc": mk_desc("找出数组中最大的元素。", "第一行输入 N，第二行输入 N 个整数。", "输出数组中的最大值。")},
        {"title": "字符串反转", "func": gen_reverse,
         "desc": mk_desc("将给定的字符串反转。", "输入一个字符串 S。", "输出反转后的字符串。")},
        {"title": "阶乘计算", "func": gen_factorial,
         "desc": mk_desc("计算 N 的阶乘 (N!)。", "输入一个整数 N (0 <= N <= 12)。", "输出 N! 的值。")},
        {"title": "质数判定", "func": gen_prime,
         "desc": mk_desc("判断一个数字是否为质数。", "输入一个整数 N。", "如果是质数输出 Yes，否则输出 No。")},
        {"title": "斐波那契数列", "func": gen_fib,
         "desc": mk_desc("求斐波那契数列的第 N 项 (从0开始，0, 1, 1, 2...)。", "输入整数 N。", "输出第 N 项的值。")},
        {"title": "统计元音", "func": gen_vowels,
         "desc": mk_desc("统计字符串中元音字母 (a, e, i, o, u) 的个数。", "输入一个字符串 S。", "输出元音的数量。")},
        {"title": "奇偶判断", "func": gen_odd_even,
         "desc": mk_desc("判断一个数是奇数还是偶数。", "输入整数 N。", "偶数输出 Even，奇数输出 Odd。")},
        {"title": "数组排序", "func": gen_sort,
         "desc": mk_desc("将数组按升序排列。", "第一行 N，第二行 N 个整数。", "输出排序后的数组，以空格分隔。")},
        {"title": "寻找缺失数字", "func": gen_missing,
         "desc": mk_desc("在 0 到 N 的序列中缺失了一个数字，请找出它。", "第一行 N，第二行 N 个不重复的整数。",
                         "输出缺失的那个数字。")},
        {"title": "闰年判断", "func": gen_leap,
         "desc": mk_desc("判断某一年是否为闰年。", "输入年份 Y。", "闰年输出 Yes，否则输出 No。")},
        {"title": "字符计数", "func": gen_char_count,
         "desc": mk_desc("统计特定字符在字符串中出现的次数。", "第一行字符串 S，第二行字符 C。",
                         "输出 C 在 S 中出现的次数。")},
        {"title": "回文串判定", "func": gen_palindrome,
         "desc": mk_desc("判断字符串是否是回文串（正读反读相同）。", "输入字符串 S。", "是回文串输出 Yes，否则输出 No。")},
        {"title": "最大公约数", "func": gen_gcd,
         "desc": mk_desc("求两个数的最大公约数。", "输入两个整数 A, B。", "输出它们的 GCD。")},
        {"title": "温度转换", "func": gen_temp,
         "desc": mk_desc("将摄氏度转换为华氏度 (整数运算)。公式 F = C * 9/5 + 32。", "输入摄氏度 C。",
                         "输出华氏度 F (取整)。")},
        {"title": "完全平方数", "func": gen_square,
         "desc": mk_desc("判断一个数是否为完全平方数。", "输入整数 N。", "是输出 True，否输出 False。")},
        {"title": "不同元素计数", "func": gen_unique_count,
         "desc": mk_desc("统计数组中有多少个不同的元素。", "第一行 N，第二行 N 个整数。", "输出不同元素的个数。")},
        {"title": "绝对值", "func": gen_abs, "desc": mk_desc("计算一个整数的绝对值。", "输入整数 N。", "输出 |N|。")},
        {"title": "简单加密", "func": gen_caesar,
         "desc": mk_desc("将字符串中每个字母向后移动一位 (a->b, z->a)。", "输入全小写字符串 S。", "输出加密后的字符串。")},
        {"title": "取模运算", "func": gen_mod,
         "desc": mk_desc("计算 A 对 B 取模的结果。", "输入两个整数 A, B。", "输出 A % B 的值。")}
    ]
    return problems


# ==========================================
# 主程序
# ==========================================

def seed():
    print(f"Connecting to database: {DB_URI}")
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 1. 准备目录
    ensure_dir(BASE_TEST_CASE_PATH)

    problems_config = get_problems_data()

    print(f"Generating {len(problems_config)} problems...")

    for idx, config in enumerate(problems_config):
        # 2. 插入数据库
        # 注意：这里我们让数据库自动生成 ID，随后 flush 获取 ID
        new_prob = Problem(
            title=config['title'],
            content=config['desc'],
            type='acm',
            language='python',
            time_limit=1000,
            memory_limit=128,
            test_case_path='',  # 占位
            created_at=datetime.now()
        )
        session.add(new_prob)
        session.flush()  # 这一步很关键，执行 SQL 但不提交，为了拿到 new_prob.id

        # 3. 生成测试数据文件
        prob_id = new_prob.id
        prob_dir = os.path.join(BASE_TEST_CASE_PATH, str(prob_id))
        ensure_dir(prob_dir)

        # 更新数据库路径
        new_prob.test_case_path = prob_dir

        # 生成 20 个点
        for i in range(1, 21):
            input_data, output_data = config['func']()

            with open(os.path.join(prob_dir, f"{i}.in"), 'w', encoding='utf-8') as f:
                f.write(input_data)

            with open(os.path.join(prob_dir, f"{i}.out"), 'w', encoding='utf-8') as f:
                f.write(output_data)

        print(f"  [OK] Problem {prob_id}: {config['title']}")

    # 4. 提交事务
    session.commit()
    session.close()
    print("All done! Data successfully seeded.")


if __name__ == "__main__":
    seed()