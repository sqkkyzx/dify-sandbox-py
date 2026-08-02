# DIFY-SANDBOX-PY

[English](README.md) | [中文](README_CN.md)

这是一个供 Dify 使用的代码执行器，兼容官方 Sandbox 的 API 调用与依赖安装方式。

- 支持 Python 3.14
- 支持 Node.js 20
- 包含 Dify 1.16.1 API 契约测试

## 目的

官方 Sandbox 通过严格的权限和 syscall 控制提供更强的隔离。本项目面向代码节点均由自己编写的可信环境，以便使用更宽松的权限以及 NumPy、Matplotlib、scikit-learn 等依赖。

## 用法

构建 Python 3.14 镜像：

```shell
docker build -t dify-sandbox-py:python3.14 .
```

在 Dify 的 `docker-compose.yaml` 中替换 Sandbox 镜像：

```yaml
sandbox:
  # image: langgenius/dify-sandbox:0.2.15
  image: dify-sandbox-py:python3.14
```

## 截图

Python 支持
![](/images/Xnip2024-11-25_11-30-12.jpg)

Node.js 支持
![](/images/Xnip2024-11-25_11-31-01.jpg)

Docker 容器日志
![](/images/Xnip2025-04-28_16-48-48.jpg)

## 说明

- 已移除网络访问限制，默认允许访问网络。
- 容器启动时，UV 会安装 `/dependencies/python-requirements.txt` 中的依赖。
- 镜像只内置 API 运行依赖；业务库请写入 `python-requirements.txt` 并固定版本。
- 可通过 `PIP_MIRROR_URL` 配置 Python 包索引。
- Python 代码超过 `WORKER_TIMEOUT` 后会终止并重建对应的进程池。
- 本执行器优先兼容性而非隔离性，只能运行可信代码。
