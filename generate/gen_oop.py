import os
import shutil
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

def get_oop_problems():
    problems = [
        {
            "title": "设计一个简单的计数器类",
            "desc": "实现一个 Counter 类，包含 increment() 方法增加计数，decrement() 方法减少计数，以及 get_value() 方法获取当前值。初始值为 0。",
            "template": "class Counter:\n    def __init__(self):\n        pass\n\n    def increment(self):\n        pass\n\n    def decrement(self):\n        pass\n\n    def get_value(self):\n        pass",
            "test_runner": """
from solution import Counter
import sys

def test():
    score = 0
    try:
        c = Counter()
        if c.get_value() == 0: score += 20
        c.increment()
        if c.get_value() == 1: score += 40
        c.decrement()
        c.decrement()
        if c.get_value() == -1: score += 40
        print(score)
    except Exception as e:
        print(0)

if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个矩形类",
            "desc": "实现一个 Rectangle 类，构造函数接受 width 和 height。包含 get_area() 返回面积，get_perimeter() 返回周长。",
            "template": "class Rectangle:\n    def __init__(self, width, height):\n        pass\n\n    def get_area(self):\n        pass\n\n    def get_perimeter(self):\n        pass",
            "test_runner": """
from solution import Rectangle
import sys

def test():
    score = 0
    try:
        r = Rectangle(10, 5)
        if r.get_area() == 50: score += 50
        if r.get_perimeter() == 30: score += 50
        print(score)
    except Exception as e:
        print(0)

if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个银行账户类",
            "desc": "实现一个 BankAccount 类，构造函数接受初始余额 balance。包含 deposit(amount) 存款，withdraw(amount) 取款（余额不足时不操作），get_balance() 获取余额。",
            "template": "class BankAccount:\n    def __init__(self, balance):\n        pass\n\n    def deposit(self, amount):\n        pass\n\n    def withdraw(self, amount):\n        pass\n\n    def get_balance(self):\n        pass",
            "test_runner": """
from solution import BankAccount
def test():
    score = 0
    try:
        b = BankAccount(100)
        if b.get_balance() == 100: score += 20
        b.deposit(50)
        if b.get_balance() == 150: score += 30
        b.withdraw(70)
        if b.get_balance() == 80: score += 30
        b.withdraw(200)
        if b.get_balance() == 80: score += 20
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个学生类",
            "desc": "实现一个 Student 类，构造函数接受 name 和 grades（列表）。包含 get_average() 返回平均分，add_grade(grade) 添加分数。",
            "template": "class Student:\n    def __init__(self, name, grades):\n        pass\n\n    def get_average(self):\n        pass\n\n    def add_grade(self, grade):\n        pass",
            "test_runner": """
from solution import Student
def test():
    score = 0
    try:
        s = Student("Alice", [80, 90])
        if abs(s.get_average() - 85) < 1e-6: score += 50
        s.add_grade(70)
        if abs(s.get_average() - 80) < 1e-6: score += 50
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个栈类",
            "desc": "实现一个 Stack 类，包含 push(item) 入栈，pop() 出栈（空栈返回 None），is_empty() 判断是否为空。",
            "template": "class Stack:\n    def __init__(self):\n        pass\n\n    def push(self, item):\n        pass\n\n    def pop(self):\n        pass\n\n    def is_empty(self):\n        pass",
            "test_runner": """
from solution import Stack
def test():
    score = 0
    try:
        s = Stack()
        if s.is_empty(): score += 20
        s.push(1)
        s.push(2)
        if not s.is_empty(): score += 20
        if s.pop() == 2: score += 30
        if s.pop() == 1: score += 30
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个圆类",
            "desc": "实现一个 Circle 类，构造函数接受 radius。包含 get_area() 返回面积，get_circumference() 返回周长（使用 3.14159）。",
            "template": "class Circle:\n    def __init__(self, radius):\n        pass\n\n    def get_area(self):\n        pass\n\n    def get_circumference(self):\n        pass",
            "test_runner": """
from solution import Circle
import math
def test():
    score = 0
    try:
        c = Circle(10)
        if abs(c.get_area() - 314.159) < 1e-2: score += 50
        if abs(c.get_circumference() - 62.8318) < 1e-2: score += 50
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的购物车",
            "desc": "实现 ShoppingCart 类。add_item(name, price)，remove_item(name)，get_total() 返回总价。",
            "template": "class ShoppingCart:\n    def __init__(self):\n        pass\n\n    def add_item(self, name, price):\n        pass\n\n    def remove_item(self, name):\n        pass\n\n    def get_total(self):\n        pass",
            "test_runner": """
from solution import ShoppingCart
def test():
    score = 0
    try:
        cart = ShoppingCart()
        cart.add_item("apple", 5)
        cart.add_item("banana", 3)
        if cart.get_total() == 8: score += 40
        cart.remove_item("apple")
        if cart.get_total() == 3: score += 60
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个温度转换器类",
            "desc": "实现 TemperatureConverter 类。celsius_to_fahrenheit(c)，fahrenheit_to_celsius(f)。",
            "template": "class TemperatureConverter:\n    @staticmethod\n    def celsius_to_fahrenheit(c):\n        pass\n\n    @staticmethod\n    def fahrenheit_to_celsius(f):\n        pass",
            "test_runner": """
from solution import TemperatureConverter
def test():
    score = 0
    try:
        if abs(TemperatureConverter.celsius_to_fahrenheit(0) - 32) < 1e-6: score += 50
        if abs(TemperatureConverter.fahrenheit_to_celsius(32) - 0) < 1e-6: score += 50
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的时钟类",
            "desc": "实现 Clock 类，构造函数接受 hour, minute, second。tick() 方法增加一秒，display() 返回 'HH:MM:SS' 格式字符串。",
            "template": "class Clock:\n    def __init__(self, h, m, s):\n        pass\n\n    def tick(self):\n        pass\n\n    def display(self):\n        pass",
            "test_runner": """
from solution import Clock
def test():
    score = 0
    try:
        c = Clock(23, 59, 59)
        if c.display() == "23:59:59": score += 30
        c.tick()
        if c.display() == "00:00:00": score += 70
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个向量类",
            "desc": "实现 Vector2D 类，构造函数接受 x, y。实现 add(other) 返回新向量，dot(other) 返回点积。",
            "template": "class Vector2D:\n    def __init__(self, x, y):\n        pass\n\n    def add(self, other):\n        pass\n\n    def dot(self, other):\n        pass",
            "test_runner": """
from solution import Vector2D
def test():
    score = 0
    try:
        v1 = Vector2D(1, 2)
        v2 = Vector2D(3, 4)
        v3 = v1.add(v2)
        if v3.x == 4 and v3.y == 6: score += 50
        if v1.dot(v2) == 11: score += 50
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的计算器类",
            "desc": "实现 Calculator 类。add(a, b), subtract(a, b), multiply(a, b), divide(a, b)（除以0返回 None）。",
            "template": "class Calculator:\n    def add(self, a, b): pass\n    def subtract(self, a, b): pass\n    def multiply(self, a, b): pass\n    def divide(self, a, b): pass",
            "test_runner": """
from solution import Calculator
def test():
    score = 0
    try:
        c = Calculator()
        if c.add(1, 2) == 3: score += 25
        if c.subtract(5, 2) == 3: score += 25
        if c.multiply(3, 4) == 12: score += 25
        if c.divide(10, 2) == 5: score += 25
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个图书类",
            "desc": "实现 Book 类，包含 title, author, is_borrowed。borrow_book() 和 return_book() 修改状态并返回是否成功。",
            "template": "class Book:\n    def __init__(self, title, author):\n        pass\n    def borrow_book(self):\n        pass\n    def return_book(self):\n        pass",
            "test_runner": """
from solution import Book
def test():
    score = 0
    try:
        b = Book("Python", "Guido")
        if b.borrow_book() == True: score += 40
        if b.borrow_book() == False: score += 30
        if b.return_book() == True: score += 30
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的队列类",
            "desc": "实现 Queue 类。enqueue(item), dequeue()（空则 None）, size()。",
            "template": "class Queue:\n    def __init__(self): pass\n    def enqueue(self, item): pass\n    def dequeue(self): pass\n    def size(self): pass",
            "test_runner": """
from solution import Queue
def test():
    score = 0
    try:
        q = Queue()
        q.enqueue(1)
        q.enqueue(2)
        if q.size() == 2: score += 30
        if q.dequeue() == 1: score += 40
        if q.dequeue() == 2: score += 30
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个点类",
            "desc": "实现 Point 类，构造函数接受 x, y。distance_to(other) 返回两点间距离。",
            "template": "class Point:\n    def __init__(self, x, y): pass\n    def distance_to(self, other): pass",
            "test_runner": """
from solution import Point
import math
def test():
    score = 0
    try:
        p1 = Point(0, 0)
        p2 = Point(3, 4)
        if abs(p1.distance_to(p2) - 5.0) < 1e-6: score += 100
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的日志记录器",
            "desc": "实现 Logger 类。log(message) 添加日志，get_logs() 返回所有日志列表，clear() 清空。",
            "template": "class Logger:\n    def __init__(self): pass\n    def log(self, msg): pass\n    def get_logs(self): pass\n    def clear(self): pass",
            "test_runner": """
from solution import Logger
def test():
    score = 0
    try:
        l = Logger()
        l.log("msg1")
        l.log("msg2")
        if len(l.get_logs()) == 2: score += 50
        l.clear()
        if len(l.get_logs()) == 0: score += 50
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个形状基类和子类",
            "desc": "实现 Shape 基类（area() 返回 0）和 Square 子类（构造函数接受 side，重写 area()）。",
            "template": "class Shape:\n    def area(self): return 0\nclass Square(Shape):\n    def __init__(self, side): pass\n    def area(self): pass",
            "test_runner": """
from solution import Square, Shape
def test():
    score = 0
    try:
        s = Square(4)
        if isinstance(s, Shape): score += 40
        if s.area() == 16: score += 60
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的密码管理器",
            "desc": "实现 PasswordManager 类。set_password(pwd), check_password(pwd) 返回布尔值。",
            "template": "class PasswordManager:\n    def set_password(self, pwd): pass\n    def check_password(self, pwd): pass",
            "test_runner": """
from solution import PasswordManager
def test():
    score = 0
    try:
        pm = PasswordManager()
        pm.set_password("secret")
        if pm.check_password("secret") == True: score += 50
        if pm.check_password("wrong") == False: score += 50
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的计时器",
            "desc": "实现 Timer 类。start(), stop() 返回经过的秒数（整数，假设调用 stop 时已经过了一些时间，测试会模拟）。",
            "template": "class Timer:\n    def start(self): pass\n    def stop(self): pass",
            "test_runner": """
from solution import Timer
import time
def test():
    score = 0
    try:
        t = Timer()
        t.start()
        time.sleep(1)
        elapsed = t.stop()
        if elapsed >= 1: score += 100
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的颜色类",
            "desc": "实现 Color 类，构造函数接受 r, g, b。to_hex() 返回 '#RRGGBB' 格式字符串。",
            "template": "class Color:\n    def __init__(self, r, g, b): pass\n    def to_hex(self): pass",
            "test_runner": """
from solution import Color
def test():
    score = 0
    try:
        c = Color(255, 0, 255)
        if c.to_hex().upper() == "#FF00FF": score += 100
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        },
        {
            "title": "设计一个简单的员工类",
            "desc": "实现 Employee 类，包含 name, salary。give_raise(percent) 增加薪水。",
            "template": "class Employee:\n    def __init__(self, name, salary): pass\n    def give_raise(self, percent): pass",
            "test_runner": """
from solution import Employee
def test():
    score = 0
    try:
        e = Employee("Bob", 5000)
        e.give_raise(10)
        if e.salary == 5500: score += 100
        print(score)
    except:
        print(0)
if __name__ == '__main__':
    test()
"""
        }
    ]
    return problems

def seed_oop():
    engine = create_engine(DB_URI)
    Session = sessionmaker(bind=engine)
    session = Session()

    problems_data = get_oop_problems()
    for data in problems_data:
        new_prob = Problem(
            title=data['title'],
            content=data['desc'],
            type='oop',
            language='python',
            template_code=data['template'],
            time_limit=5,
            memory_limit=128
        )
        session.add(new_prob)
        session.flush()

        prob_dir = os.path.join(BASE_PROBLEM_PATH, str(new_prob.id))
        ensure_dir(prob_dir)
        new_prob.test_case_path = prob_dir

        with open(os.path.join(prob_dir, "test_runner.py"), "w", encoding="utf-8") as f:
            f.write(data['test_runner'])

    session.commit()
    session.close()
    print("OOP problems seeded successfully.")

if __name__ == "__main__":
    seed_oop()
