import os
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Enum, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base

# =================配置区域=================
DB_URI = 'mysql+pymysql://root:root@localhost:3306/oj_db'
BASE_PROBLEM_PATH = '../backend/uploads/problems'

Base = declarative_base()

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
    if not os.path.exists(directory):
        os.makedirs(directory)

def get_kaggle_problems():
    problems = []
    
    # 1. 房价预测 (Regression - RMSE)
    problems.append({
        "title": "房价预测挑战赛",
        "desc": "根据房屋的各项特征（面积、房间数等）预测房价。请提交包含 'id' 和 'price' 的 CSV 文件。评分标准为 RMSE。",
        "gen_data": lambda: (
            pd.DataFrame({'id': range(100), 'price': np.random.rand(100) * 500000 + 100000}),
            """
import pandas as pd
import numpy as np
try:
    truth = pd.read_csv('truth.csv')
    submit = pd.read_csv('submission.csv')
    merged = truth.merge(submit, on='id', suffixes=('_true', '_pred'))
    rmse = np.sqrt(((merged['price_true'] - merged['price_pred']) ** 2).mean())
    # 将 RMSE 映射到 0-100 分，假设 RMSE=0 是 100分，RMSE=100000 是 0分
    score = max(0, 100 - (rmse / 1000))
    print(score)
except Exception as e:
    print(0)
"""
        )
    })

    # 2. 泰坦尼克号生存预测 (Classification - Accuracy)
    problems.append({
        "title": "泰坦尼克号生存预测",
        "desc": "预测乘客是否在泰坦尼克号沉没中幸存。请提交包含 'PassengerId' 和 'Survived' (0 或 1) 的 CSV 文件。评分标准为准确率。",
        "gen_data": lambda: (
            pd.DataFrame({'PassengerId': range(1, 101), 'Survived': np.random.randint(0, 2, 100)}),
            """
import pandas as pd
try:
    truth = pd.read_csv('truth.csv')
    submit = pd.read_csv('submission.csv')
    merged = truth.merge(submit, on='PassengerId')
    acc = (merged['Survived_x'] == merged['Survived_y']).mean()
    print(acc * 100)
except:
    print(0)
"""
        )
    })

    
    return problems

def seed_kaggle():
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    problems_data = get_kaggle_problems()
    for data in problems_data:
        new_prob = Problem(
            title=data['title'],
            content=data['desc'],
            type='kaggle',
            language='python', # Kaggle 评分脚本通常用 Python
            time_limit=30,
            memory_limit=512
        )
        session.add(new_prob)
        session.flush()

        prob_dir = os.path.join(BASE_PROBLEM_PATH, str(new_prob.id))
        ensure_dir(prob_dir)
        new_prob.test_case_path = prob_dir

        # 生成真值数据和评分脚本
        df_truth, score_script = data['gen_data']()
        df_truth.to_csv(os.path.join(prob_dir, "truth.csv"), index=False)
        
        with open(os.path.join(prob_dir, "score.py"), "w", encoding="utf-8") as f:
            f.write(score_script)

    session.commit()
    session.close()
    print("Kaggle problems seeded successfully.")

if __name__ == "__main__":
    seed_kaggle()
