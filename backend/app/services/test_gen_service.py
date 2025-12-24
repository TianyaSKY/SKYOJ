import io
import os
import shutil
import tarfile

from app.services.judge_service import client, create_tar_stream

# 使用专门的生成沙箱镜像
GEN_IMAGE_NAME = "skyoj-generator"


def run_test_generation(problem_id, code):
    """
    运行 LLM 生成的测试数据脚本，并将生成的文件保存到题目目录下。
    """
    container = None
    try:
        # 启动容器
        container = client.containers.run(
            image=GEN_IMAGE_NAME,
            command="sleep 600",
            detach=True,
            network_mode="none",
            remove=True
        )

        # 将生成脚本上传到容器
        # 假设脚本是 Python 编写的
        tar_stream = create_tar_stream('generator.py', code)
        container.put_archive('/app', tar_stream)

        # 创建输出目录 (在 Dockerfile 中已授权给 generator 用户)
        container.exec_run("mkdir -p /app/output")

        # 运行脚本，工作目录设为 /app/output
        # 脚本应该将生成的测试文件直接写在当前目录
        exec_result = container.exec_run("python3 ../generator.py", workdir="/app/output")

        if exec_result.exit_code != 0:
            return False, f"Execution Error: {exec_result.output.decode('utf-8')}"

        # 从容器中获取生成的测试文件
        bits, stat = container.get_archive('/app/output')

        # 准备宿主机存储路径
        problem_dir = os.path.join("uploads/problems", str(problem_id))
        if os.path.exists(problem_dir):
            shutil.rmtree(problem_dir)
        os.makedirs(problem_dir)

        # 将 tar 流写入内存并解压
        tar_data = io.BytesIO()
        for chunk in bits:
            tar_data.write(chunk)
        tar_data.seek(0)

        with tarfile.open(fileobj=tar_data) as tar:
            tar.extractall(path=problem_dir)

        # get_archive 会包含 'output' 这一层目录，我们需要把里面的文件移出来
        extracted_output_dir = os.path.join(problem_dir, 'output')
        if os.path.exists(extracted_output_dir):
            for filename in os.listdir(extracted_output_dir):
                shutil.move(os.path.join(extracted_output_dir, filename), os.path.join(problem_dir, filename))
            os.rmdir(extracted_output_dir)

        return True, "Test cases generated and saved successfully."

    except Exception as e:
        return False, f"System Error: {str(e)}"
    finally:
        if container:
            try:
                container.stop()
            except:
                pass
