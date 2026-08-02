import asyncio
import io
import subprocess
import tempfile
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import TypedDict


class ExecutionResult(TypedDict):
    success: bool
    output: str
    error: str | None


def _run_python_code_in_process(code: str) -> ExecutionResult:
    """在独立进程中执行 Python 代码。"""
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
            exec(code, {"__name__": "__main__"})  # noqa: S102

        return {
            "success": True,
            "output": stdout_buffer.getvalue(),
            "error": stderr_buffer.getvalue() or None,
        }
    except Exception as e:  # noqa: BLE001
        return {
            "success": False,
            "output": stdout_buffer.getvalue(),
            "error": str(e),
        }
    finally:
        stdout_buffer.close()
        stderr_buffer.close()


def _run_nodejs_code_in_process(code: str) -> ExecutionResult:
    """在独立进程中执行 Node.js 代码。"""
    temp_file_path: Path | None = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False
        ) as temp_file:
            temp_file.write(code)
            temp_file_path = Path(temp_file.name)

        process = subprocess.Popen(  # noqa: S603
            ["node", str(temp_file_path)],  # noqa: S607
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate()

        if process.returncode == 0:
            return {"success": True, "output": stdout, "error": None}
        return {"success": False, "output": stdout, "error": stderr}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "output": "", "error": str(e)}
    finally:
        if temp_file_path is not None:
            temp_file_path.unlink(missing_ok=True)


def check_nodejs_available() -> bool:
    """检查 Node.js 是否可用。"""
    try:
        subprocess.run(
            ["node", "--version"],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.SubprocessError, FileNotFoundError:
        return False


class CodeExecutor:
    def __init__(self, timeout: int = 30, max_workers: int = 10) -> None:
        self.timeout = timeout
        self.max_workers = max_workers
        self.process_pool = self._create_process_pool()
        self.nodejs_available = check_nodejs_available()
        self._process_pool_lock = asyncio.Lock()

    def _create_process_pool(self) -> ProcessPoolExecutor:
        return ProcessPoolExecutor(max_workers=self.max_workers)

    async def shutdown(self) -> None:
        """关闭进程池。"""
        async with self._process_pool_lock:
            self.process_pool.shutdown(wait=True, cancel_futures=True)

    async def _terminate_and_replace_process_pool(
        self, timed_out_pool: ProcessPoolExecutor
    ) -> None:
        async with self._process_pool_lock:
            if self.process_pool is not timed_out_pool:
                return

            timed_out_pool.terminate_workers()
            self.process_pool = self._create_process_pool()

    async def execute(self, code: str, language: str = "python3") -> ExecutionResult:
        process_pool = self.process_pool

        try:
            if language == "python3":
                executor_func = _run_python_code_in_process
            elif language == "nodejs":
                if not self.nodejs_available:
                    return {
                        "success": False,
                        "output": "",
                        "error": "Node.js未安装或不可用",
                    }
                executor_func = _run_nodejs_code_in_process
            else:
                return {
                    "success": False,
                    "output": "",
                    "error": f"不支持的语言: {language}",
                }

            future = asyncio.get_running_loop().run_in_executor(
                process_pool,
                executor_func,
                code,
            )
            return await asyncio.wait_for(future, timeout=self.timeout)
        except TimeoutError:
            await self._terminate_and_replace_process_pool(process_pool)
            return {
                "success": False,
                "output": "",
                "error": f"代码执行超时 (>{self.timeout}秒)",
            }
        except Exception as e:  # noqa: BLE001
            return {"success": False, "output": "", "error": str(e)}
