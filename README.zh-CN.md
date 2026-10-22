# Codex Analysis State

面向 Codex CLI 多轮数据分析的显式状态、历史数据选择和可重放计算扩展。

[English](README.md) · [快速开始](docs/quickstart.md) ·
[方法说明](docs/method.md) · [历史实验](docs/results.md) ·
[验证记录](docs/validation.md)

当用户不断改变分析范围、指标和比较方式时，明确记录哪些定义继续沿用、
哪些修改只对本轮生效，以及应该读取哪个历史结果。扩展分别处理分析对象、
测量定义、历史比较基准和展示行数，并在发布可复用结果前重放 Python 计算。

本项目是独立研究项目，使用 [StateM](https://github.com/henryqin1997/statem)
运行时。Codex CLI 提供模型与工具，本包提供项目级 Skill、分析协议和命令入口。

## 历史案例

| 实验 | 优化前 | 优化后 | 口径 |
|---|---:|---:|---|
| Netflix task2：Native 与分析扩展对照 | 13/34（38.24%） | 27/34（79.41%） | 单任务、每组一次运行，计算预算未对齐 |
| Netflix task2：开发流程迭代 | 1/34（2.94%） | 29/34（85.29%） | 参考知情的同题开发调优 |

两组结果来自历史冻结工作流。本次独立打包版本尚未经过等价性评测；同题开发
成绩也不代表独立留出任务成绩。更广范围实验存在收益与退化，完整口径见
[历史实验与局限](docs/results.md)。

## 安装

使用 Python 3.11 及以上版本，以下命令适用于 POSIX shell。实际模型使用需要
另行安装并登录 Codex CLI。

```sh
git clone https://github.com/qiboyu301-crypto/codex-analysis-state.git
cd codex-analysis-state
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

先运行不调用模型的三轮示例，输出目录需要是新目录：

```sh
analysis-state demo /tmp/analysis-state-demo
```

示例只有六行自建销售数据。第一轮保留三个一月候选地区、展示前两名；第二轮
临时用二月收入衡量原来的三个地区，展示名单发生变化但候选集合不变；第三轮
恢复一月口径，总收入从二月的 260 恢复为 240。示例使用预先编写的计算脚本，
用于理解和验证流程，不是模型准确率实验。

输出包含逐轮的 `answer.json`、分析定义、输入与重放回执，以及可复用数据目录。

## 在自己的数据上使用

先把原始表格放在一个输入目录，然后创建独立工作区：

```sh
analysis-state init /tmp/my-analysis --data /path/to/input-tables
cd /tmp/my-analysis
codex
```

启动 Codex 时保持包的虚拟环境已激活。初始化会复制输入、记录内容哈希，并把
Skill 放到工作区的 `.agents/skills/analysis-state`。在 Codex 中输入：

```text
使用 $analysis-state 分析这些表格。先确定完整候选集合，只展示前五名。
后续我会修改指标，但仍然引用这个原始候选集合。
```

工作流为：检查 → 计算 → 保留 → 验证 → 交付。Skill 会指导 Agent 使用
`analysis-state begin`、`next`、`run` 和 `complete`。已有输入快照变化时创建
新工作区；已发布的历史表格保持不变。详细命令与文件格式见
[快速开始](docs/quickstart.md)。

## 验证范围与贡献

重放检查能核对输入身份、执行是否成功、数据事实及声明的历史读取，不能保证
业务语义正确，也不自动核对 Codex 实际最终回复。普通 Python 在用户已有权限
下运行，本包不提供文件系统隔离。

`bash scripts/validate_release.sh` 在干净环境中构建并安装 wheel、运行行为测试
和三轮示例，不调用模型。当前验证状态见 [validation.md](docs/validation.md)。

代码采用 Apache-2.0。StateM 与研究代码来源、冻结提交和适配改动见
[NOTICE](NOTICE) 和 [PROVENANCE.json](PROVENANCE.json)。欢迎提供可复现的问题
和实际使用反馈，参与方式见 [CONTRIBUTING.md](CONTRIBUTING.md)。
