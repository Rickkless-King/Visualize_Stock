# Visualize_Stock

> 一个**透视市场**的美股交易与可视化复盘工作台。  
> 用固定代码处理结构性数据，用 AI Agent 处理非结构性数据。

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

**免责声明**：本项目仅用于个人金融工程学习、数据可视化研究与交易纪律记录，不构成任何证券投资咨询或买卖建议。

---

## 项目简介

`Visualize_Stock` 是一个面向个人主观研究者的 **左画布 + 右 Copilot** 交互式市场透视工作台，致力于把分散在多个网页里的**条件/指标选股、多周期走势、关键基本面事件节点与 AI 归因复盘**收敛到同一张画布上：

- **混合选股栏**：支持市值、区间最大回撤、主题标签等横截面筛选，兼容类通达信（`MyTT`）技术指标表达式沙盒校验与信号回标。
- **事件图钉 K 线画布**：支持多周期重采样，将财报（`E`）、分红（`D`）与放量跳空异动（`!`）按交易日历自动锚定至对应 K 线。
- **双向共享画布 Agent**：点击画布事件节点即可带入上下文做多源证据归因；Agent 亦可通过工具在画布上标记关键节点或高亮走势区间。
- **可插拔与自带密钥（BYOK）**：支持用户本地配置主流大模型与多市场数据源 API Key，未配置高配源时自动降级至公开免费数据源。

---

## 代码结构

```text
Visualize_Stock/
├── src/
│   ├── core/          # 核心数据模型与市场配置契约
│   ├── providers/     # 行情、基本面数据源与大模型接入网关
│   ├── storage/       # Parquet/DuckDB 时序底座与 SQLite 状态存储
│   ├── engine/        # 重采样、事件图钉检测、条件与指标选股引擎
│   ├── agent/         # 共享画布 Agent 与工具集
│   └── app/           # FastAPI 服务与 Web 工作台静态资源
├── tests/             # pytest 自动化单元测试
├── data/sample/       # 最小脱敏演示样例数据
├── pyproject.toml     # 项目与测试配置
└── requirements.txt   # Python 依赖清单
```

---

## 快速开始

```powershell
# 1. 创建并激活虚拟环境（Python 3.12+）
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制环境变量模板（按需填入自己的 API Key）
copy .env.example .env

# 4. 运行单元测试
pytest -x
```
