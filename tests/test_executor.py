import asyncio

from app.executor import CodeExecutor, ExecutionResult


async def exercise_timeout_and_recovery() -> tuple[ExecutionResult, ExecutionResult]:
    executor = CodeExecutor(timeout=1, max_workers=1)

    timed_out = await executor.execute("while True: pass")
    recovered = await executor.execute("print('recovered')")
    await executor.shutdown()

    return timed_out, recovered


def test_timeout_terminates_workers_and_recovers() -> None:
    timed_out, recovered = asyncio.run(exercise_timeout_and_recovery())

    assert timed_out["error"] == "代码执行超时 (>1秒)"
    assert recovered == {"success": True, "output": "recovered\n", "error": None}
