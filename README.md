# CalKit / 多尺度计算分析工具包

> CalKit — Multi-scale Computation Analysis Toolkit  
> 支持 VASP / Materials Studio / LAMMPS / ABACUS / DeePkit 等多计算软件的后处理工具包

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-0.4.0-orange)]()

---

* [English](#english)  
* [中文](#中文)

---

## English

### 1. Project Overview

**CalKit** is a Python toolkit for post-processing computational chemistry and materials science results. It supports multiple software platforms including **VASP**, **Materials Studio**, **LAMMPS**, **ABACUS**, and **DeePkit**, with a unified command-line interface and Python API for all analysis modules.

| Module | Class | Supported Software | Description |
|---|---|---|---|
| **Force Convergence** | `ForceConvergenceAnalyzer` | VASP | Parse force convergence from OUTCAR |
| **Bader Charge** | `BaderAnalyzer` | VASP | Automate Bader charge analysis, export to Excel |
| **Free Energy** | `FreeEnergyAnalyzer` | VASP | Extract free energy values from OUTCAR |
| **PDOS** | `PDOSAnalyzer` | VASP | Parse DOSCAR/PROCAR for PDOS and d-band center analysis |
| **Magnetic Moment** | `MagneticMomentAnalyzer` | VASP | Extract magnetic moments from OUTCAR, export to Excel |
| **Energy** | `EnergyExtractor` | VASP | Extract energy without entropy, energy(sigma->0), TOTEN |

> **Roadmap**: LAMMPS log parsing, Materials Studio energy analysis, ABACUS output processing, and DeePkit integration are under development.

### 2. Architecture

All analyzers inherit from `BaseAnalyzer` (defined in `base.py`), which provides:
- Common path resolution and file validation
- Shared parsing helpers (`_float_after`, `_float_at`, `_find_line`)
- Error tracking via `self.errors`

The CLI and interactive menu share a single **command registry** (`COMMANDS` dict in `cli.py`), so adding a new analyzer only requires adding one entry — no boilerplate needed.

```
CalKit/ckit/
  base.py              BaseAnalyzer ABC
  force_convergence.py ForceConvergenceAnalyzer
  bader_analysis.py    BaderAnalyzer
  free_energy.py       FreeEnergyAnalyzer
  pdos_analysis.py     PDOSAnalyzer
  magnetic_moment.py   MagneticMomentAnalyzer
  energy.py            EnergyExtractor
  cli.py               CLI (argparse + command registry)
  menu.py              Interactive TUI (auto-generated from registry)
  config.py            Configuration (~/.calkit/config.json)
```

### 3. Features

- **Command-line interface** — `calkit force`, `bader`, `free`, `pdos`, `mag`, `energy`
- **Interactive menu** — launch with `calkit` (no args) or `python -m ckit.menu`
- **Python API** — consistent `run(**kwargs)` / `print_summary()` / `to_excel()` interface
- **Excel export** — `to_excel(path)` on analyzers that produce tabular results
- **Text export** — `to_file(path)` on energy-related analyzers
- **Configuration** — `~/.calkit/config.json`, editable via `calkit config`
- **Cross-platform** — runs on Linux, macOS, and Windows
- **Extensible** — add a new analyzer by subclassing `BaseAnalyzer` and registering in `COMMANDS`

### 4. Installation

```bash
# Standard pip install
pip install .

# Or use the one-click setup script (Linux/macOS)
bash setup.sh
```

**Requirements** (auto-installed):

```
openpyxl >= 3.0.0    # Excel export
numpy >= 1.21.0       # Numerical operations
matplotlib >= 3.5.0   # Plotting
pandas >= 1.3.0       # Data manipulation
```

### 5. Usage

#### 5.1 Command-Line Interface

```bash
# Launch interactive menu
calkit

# Force convergence
calkit force --outcar OUTCAR --directory .

# Bader analysis + Excel export
calkit bader --acf ACF.dat --outcar OUTCAR --excel results.xlsx

# Free energy
calkit free --outcar OUTCAR --output energy.txt

# Magnetic moment + Excel export
calkit mag --outcar OUTCAR --excel mag.xlsx

# Energy extraction
calkit energy --outcar OUTCAR

# PDOS analysis
calkit pdos --doscar DOSCAR --procar PROCAR --excel pdos.xlsx
```

#### 5.2 Python API

```python
from ckit import ForceConvergenceAnalyzer, BaderAnalyzer, MagneticMomentAnalyzer

# Force convergence
fc = ForceConvergenceAnalyzer()
fc.run(outcar_path="OUTCAR", directory=".")
fc.print_summary()

# Bader analysis
bader = BaderAnalyzer()
bader.run(acf_path="ACF.dat", outcar_path="OUTCAR", directory=".")
bader.print_summary()
bader.to_excel("bader_results.xlsx")

# Magnetic moment
mag = MagneticMomentAnalyzer()
mag.run(outcar_path="OUTCAR", directory=".")
mag.print_summary()
mag.to_excel("mag_results.xlsx")
```

#### 5.3 Interactive Menu

```
╔══════════════════════════════════════╗
║            CalKit  v0.4.0            ║
╚══════════════════════════════════════╝

  [1] force      Force convergence analysis
  [2] bader      Bader charge analysis
  [3] free       Free energy analysis
  [4] pdos       PDOS analysis
  [5] mag        Magnetic moment analysis
  [6] energy     Energy extraction
  [0] exit       Exit

Select >
```

### 6. Configuration

```bash
calkit config
```

Settings are stored in `~/.calkit/config.json`:

| Section | Key | Description | Default |
|---|---|---|---|
| `paths` | `pseudopotential_dir` | Pseudopotential library path | `""` |
| `paths` | `bader_executable` | Bader program path | `"bader"` |
| `paths` | `vaspkit_executable` | Vaspkit program path | `"vaspkit"` |
| `paths` | `default_output_dir` | Default output directory | `""` |
| `defaults` | `temperature` | Default temperature (K) | `298.15` |
| `defaults` | `dpi` | Plot resolution | `150` |
| `defaults` | `output_format` | Output format | `"excel"` |
| `defaults` | `pdos_pattern` | PDOS glob pattern | `"PDOS*.dat"` |
| `ui` | `color_output` | ANSI color support | `true` |

### 7. Supported Software

| Software | Status | Modules |
|---|---|---|
| **VASP** | Full support | All 6 analyzers (force, bader, free, pdos, mag, energy) |
| **Materials Studio** | Planned | Energy extraction, geometry analysis |
| **LAMMPS** | Planned | Log parsing, thermodynamic analysis |
| **ABACUS** | Planned | Output processing, band structure |
| **DeePkit** | Planned | Model integration, property prediction |

### 8. Adding a New Analyzer

1. Create a new module (e.g. `my_analysis.py`) subclassing `BaseAnalyzer`
2. Implement `run(**kwargs)` and `print_summary()`
3. Add an entry to `COMMANDS` in `cli.py`
4. The interactive menu updates automatically

Example:

```python
# my_analysis.py
from .base import BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    def run(self, **kwargs):
        # parsing logic here
        self._ran = True

    def print_summary(self):
        print("My analysis results")
```

```python
# In cli.py COMMANDS dict:
"mycmd": {
    "class": MyAnalyzer,
    "help": "My custom analysis",
    "run_kwargs": lambda a: {"directory": a.directory},
    "add_args": lambda p: (
        p.add_argument("--directory", default=".", help="VASP directory"),
    ),
},
```

### 9. License

MIT License. See [LICENSE](LICENSE) for details.

---

## 中文

### 1. 项目概述

**CalKit** 是一款面向计算化学与材料科学的多尺度计算分析工具包，支持 **VASP**、**Materials Studio**、**LAMMPS**、**ABACUS** 和 **DeePkit** 等多种计算软件的后处理分析，提供统一的命令行接口和 Python API。

| 模块 | 类 | 支持软件 | 描述 |
|---|---|---|---|
| **力收敛分析** | `ForceConvergenceAnalyzer` | VASP | 从 OUTCAR 解析力收敛信息 |
| **Bader 电荷分析** | `BaderAnalyzer` | VASP | 自动化 Bader 电荷分析，导出 Excel |
| **自由能分析** | `FreeEnergyAnalyzer` | VASP | 从 OUTCAR 提取自由能数值 |
| **PDOS 分析** | `PDOSAnalyzer` | VASP | 解析 DOSCAR/PROCAR，分析 PDOS 与 d 带中心 |
| **磁矩分析** | `MagneticMomentAnalyzer` | VASP | 从 OUTCAR 提取磁矩，导出 Excel |
| **能量提取** | `EnergyExtractor` | VASP | 提取 energy without entropy、energy(sigma->0)、TOTEN |

> **路线图**: LAMMPS 日志解析、Materials Studio 能量分析、ABACUS 输出处理、DeePkit 集成正在开发中。

### 2. 架构说明

所有分析器均继承自 `base.py` 中定义的 `BaseAnalyzer`，提供：
- 通用路径解析和文件校验
- 共享解析辅助方法（`_float_after`、`_float_at`、`_find_line`）
- 通过 `self.errors` 进行错误追踪

CLI 和交互式菜单共享同一个**命令注册表**（`cli.py` 中的 `COMMANDS` 字典），新增分析器只需添加一条记录，无需编写样板代码。

```
CalKit/ckit/
  base.py              基类 BaseAnalyzer
  force_convergence.py ForceConvergenceAnalyzer
  bader_analysis.py    BaderAnalyzer
  free_energy.py       FreeEnergyAnalyzer
  pdos_analysis.py     PDOSAnalyzer
  magnetic_moment.py   MagneticMomentAnalyzer
  energy.py            EnergyExtractor
  cli.py               CLI（argparse + 命令注册表）
  menu.py              交互式 TUI（从注册表自动生成）
  config.py            配置管理（~/.calkit/config.json）
```

### 3. 功能特性

- **命令行接口** — `calkit force`/`bader`/`free`/`pdos`/`mag`/`energy`
- **交互式菜单** — 运行 `calkit`（无参数）或 `python -m ckit.menu`
- **Python API** — 统一的 `run(**kwargs)` / `print_summary()` / `to_excel()` 接口
- **Excel 导出** — 支持表格结果的分析器提供 `to_excel(path)`
- **文本导出** — 能量相关分析器提供 `to_file(path)`
- **配置管理** — `~/.calkit/config.json`，可通过 `calkit config` 编辑
- **跨平台** — 支持 Linux、macOS、Windows
- **易扩展** — 继承 `BaseAnalyzer` 并在 `COMMANDS` 中注册即可添加新分析器

### 4. 安装方法

```bash
# 标准 pip 安装
pip install .

# 或使用一键部署脚本（Linux/macOS）
bash setup.sh
```

**依赖项**（自动安装）：

```
openpyxl >= 3.0.0    # Excel 导出
numpy >= 1.21.0       # 数值计算
matplotlib >= 3.5.0   # 绘图
pandas >= 1.3.0       # 数据处理
```

### 5. 使用说明

#### 5.1 命令行接口

```bash
# 启动交互式菜单
calkit

# 力收敛分析
calkit force --outcar OUTCAR --directory .

# Bader 分析 + Excel 导出
calkit bader --acf ACF.dat --outcar OUTCAR --excel results.xlsx

# 自由能分析
calkit free --outcar OUTCAR --output energy.txt

# 磁矩分析 + Excel 导出
calkit mag --outcar OUTCAR --excel mag.xlsx

# 能量提取
calkit energy --outcar OUTCAR

# PDOS 分析
calkit pdos --doscar DOSCAR --procar PROCAR --excel pdos.xlsx
```

#### 5.2 Python API

```python
from ckit import ForceConvergenceAnalyzer, BaderAnalyzer, MagneticMomentAnalyzer

# 力收敛分析
fc = ForceConvergenceAnalyzer()
fc.run(outcar_path="OUTCAR", directory=".")
fc.print_summary()

# Bader 分析
bader = BaderAnalyzer()
bader.run(acf_path="ACF.dat", outcar_path="OUTCAR", directory=".")
bader.print_summary()
bader.to_excel("bader_results.xlsx")

# 磁矩分析
mag = MagneticMomentAnalyzer()
mag.run(outcar_path="OUTCAR", directory=".")
mag.print_summary()
mag.to_excel("mag_results.xlsx")
```

#### 5.3 交互式菜单

```
╔══════════════════════════════════════╗
║            CalKit  v0.4.0            ║
╚══════════════════════════════════════╝

  [1] force      力收敛分析
  [2] bader      Bader 电荷分析
  [3] free       自由能分析
  [4] pdos       PDOS 分析
  [5] mag        磁矩分析
  [6] energy     能量提取
  [0] exit       退出

请选择 >
```

### 6. 配置管理

```bash
calkit config
```

配置文件位于 `~/.calkit/config.json`：

| 分组 | 键名 | 说明 | 默认值 |
|---|---|---|---|
| `paths` | `pseudopotential_dir` | 赝势库路径 | `""` |
| `paths` | `bader_executable` | Bader 程序路径 | `"bader"` |
| `paths` | `vaspkit_executable` | Vaspkit 程序路径 | `"vaspkit"` |
| `paths` | `default_output_dir` | 默认输出目录 | `""` |
| `defaults` | `temperature` | 默认温度 (K) | `298.15` |
| `defaults` | `dpi` | 图片分辨率 | `150` |
| `defaults` | `output_format` | 输出格式 | `"excel"` |
| `defaults` | `pdos_pattern` | PDOS 文件匹配模式 | `"PDOS*.dat"` |
| `ui` | `color_output` | ANSI 彩色输出 | `true` |

### 7. 支持的软件

| 软件 | 状态 | 分析模块 |
|---|---|---|
| **VASP** | 完整支持 | 全部 6 个分析器（力收敛、Bader、自由能、PDOS、磁矩、能量） |
| **Materials Studio** | 计划中 | 能量提取、几何分析 |
| **LAMMPS** | 计划中 | 日志解析、热力学分析 |
| **ABACUS** | 计划中 | 输出处理、能带结构 |
| **DeePkit** | 计划中 | 模型集成、性质预测 |

### 8. 添加新分析器

1. 新建模块（如 `my_analysis.py`），继承 `BaseAnalyzer`
2. 实现 `run(**kwargs)` 和 `print_summary()`
3. 在 `cli.py` 的 `COMMANDS` 字典中添加一条记录
4. 交互式菜单会自动更新

示例：

```python
# my_analysis.py
from .base import BaseAnalyzer

class MyAnalyzer(BaseAnalyzer):
    def run(self, **kwargs):
        # 解析逻辑
        self._ran = True

    def print_summary(self):
        print("自定义分析结果")
```

```python
# 在 cli.py 的 COMMANDS 中添加：
"mycmd": {
    "class": MyAnalyzer,
    "help": "自定义分析",
    "run_kwargs": lambda a: {"directory": a.directory},
    "add_args": lambda p: (
        p.add_argument("--directory", default=".", help="计算目录"),
    ),
},
```

### 9. 许可证

MIT 许可证。详见 [LICENSE](LICENSE) 文件。
