import os

from app.models.problem import Problem
from app.services.judge_service import client, IMAGE_NAME, create_tar_stream


def run_acm_judge(submission_id, user_code, problem_id, language='python'):
    # 多语言配置
    configs = {
        'c': {'src': 'main.c', 'compile': 'gcc main.c -o main', 'run': './main'},
        'cpp': {'src': 'main.cpp', 'compile': 'g++ main.cpp -o main', 'run': './main'},
        'java': {'src': 'Main.java', 'compile': 'javac -encoding UTF-8 Main.java', 'run': 'java Main'},
        'python': {'src': 'solution.py', 'compile': None, 'run': 'python3 solution.py'}
    }

    lang_config = configs.get(language.lower())
    if not lang_config:
        return "System Error", 0, f"Unsupported language: {language}"

    # 1. 获取题目信息和测试点路径
    problem = Problem.query.get(problem_id)
    # 假设路径为 /uploads/problems/1
    test_case_dir = f"uploads/problems/{problem_id}"

    if not os.path.exists(test_case_dir):
        return "Runtime Error", 0, "System Error: Test cases missing"

    # 获取所有输入文件
    in_files = [f for f in os.listdir(test_case_dir) if f.endswith('.in')]
    total_cases = len(in_files)
    if total_cases == 0:
        return "Runtime Error", 0, "System Error: No .in files found"

    passed_count = 0
    logs = []

    container = None
    try:
        # 启动容器 (挂起模式，等待指令)
        container = client.containers.run(
            image=IMAGE_NAME,
            command="sleep 600",  # 保持容器运行
            detach=True,
            network_mode="none",
            mem_limit=f"{problem.memory_limit}m",
            # 确保使用本地构建的镜像
            nano_cpus=1000000000,  # 限制为 1 CPU
            remove=True,
            pids_limit=50  # 防止创建过多进程
        )

        # 2. 上传用户代码
        tar_stream = create_tar_stream(lang_config['src'], user_code)
        container.put_archive('/app', tar_stream)

        # 3. 编译代码 (如果需要)
        if lang_config['compile']:
            exec_result = container.exec_run(lang_config['compile'])
            if exec_result.exit_code != 0:
                return "Compile Error", 0, exec_result.output.decode('utf-8')

        # 4. 循环测试每个点
        for in_file in sorted(in_files):
            case_name = in_file.replace('.in', '')

            # 读取宿主机(Backend容器)中的测试用例
            with open(os.path.join(test_case_dir, in_file), 'r') as f:
                input_data = f.read()
            with open(os.path.join(test_case_dir, f"{case_name}.out"), 'r') as f:
                expected_output = f.read().strip()

            # 将 input 写入容器的 input.txt
            input_tar = create_tar_stream('input.txt', input_data)
            container.put_archive('/app', input_tar)

            # 运行命令: ./main < input.txt
            # 增加超时保护
            time_limit = getattr(problem, 'time_limit', 1)
            run_cmd = f"sh -c 'timeout {time_limit}s {lang_config['run']} < input.txt'"

            # 执行
            result = container.exec_run(run_cmd)
            actual_output = result.output.decode('utf-8').strip()

            if result.exit_code != 0:
                logs.append(f"Test Case {case_name}: Runtime Error\n{actual_output}")
            elif actual_output == expected_output:
                passed_count += 1
                logs.append(f"Test Case {case_name}: Passed")
            else:
                logs.append(f"Test Case {case_name}: Wrong Answer")

    except Exception as e:
        return "Runtime Error", 0, str(e)
    finally:
        if container:
            try:
                container.stop()
            except:
                pass

    # 3. 按比例计算分数
    final_score = (passed_count / total_cases) * 100
    final_status = "Accepted" if passed_count == total_cases else "Wrong Answer"

    return final_status, final_score, "\n".join(logs)
