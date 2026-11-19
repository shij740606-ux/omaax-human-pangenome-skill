---
name: human-pangenome-reanalysis
description: 人类双端短读长 WGS 泛基因组重分析。用于用户希望将 FASTQ 或已有线性参考 BAM/CRAM 的 reads 重新映射到 CPC/HPRC 等匹配图参考、输出指定坐标的 BAM 和质量统计、接续变异分析时。需要 Linux 服务器和独立参考包；只有 VCF 时不能完成 reads 重分析。不用于临床诊断、RNA-seq、外显子组、长读长或肿瘤体细胞流程。
---

# 人类泛基因组重分析（研究版）

## 先确定输入和执行位置

复用 OMaaX 当前项目、服务器、计算环境和任务管理。服务器计算通过已配置的 `workspace_script` / `workspace_analysis` 等管理通道；不要另开 SSH 绕过服务器管理。只询问尚缺且阻塞本次分析的信息。

1. 确认人类胚系双端短读长 WGS、样本 ID、两个 FASTQ 路径、参考清单、输出目录、线程与资源预算。
2. FASTQ 直接进入脚本。BAM/CRAM 先读 [输入与后续分析](references/inputs-and-downstream.md)，恢复 reads 并核对保留范围。VCF-only 只能比较或注释；不能声称补回漏测序列。个体组装 FASTA 属于另一种流程。
3. 计算在用户选定 Linux 服务器上运行。**桌面内置 Python 或“技能已添加”不代表 vg/SAMtools/参考索引就绪。不要用 pip 安装 vg 或 SAMtools。** 将本 skill 的脚本和配置传到本次服务器任务目录；数据保持在原服务器。
4. 读 [环境和参考包](references/setup.md)，检查实际版本、索引配套关系、FASTA 路径命名、GRCh38/CHM13 坐标及资源。缺失就报告具体项，不循环猜装环境。

## 执行

复制 `assets/config.example.json` 成本次任务的 JSON，填真实绝对路径。参考文件记录来源和 SHA256；参考坐标与路径必须匹配，不通过批量重命名假装转换。

```bash
python3 /path/to/skill/scripts/run.py --config /path/to/task.json --check
python3 /path/to/skill/scripts/run.py --config /path/to/task.json
```

`--check` 完整检查四行 FASTQ 的配对、格式、输入哈希、参考哈希、工具版本、路径和磁盘，不启动比对或创建结果目录；大文件检查本身需要时间。通过后继续用户已授权的分析，不额外要求例行确认。集群计算使用已确认的调度方式，避免在登录节点执行重计算。

脚本固定 vg 1.78.0，其他版本需先用同一小型流程验收后调整代码和参考清单。所有索引必须预先存在，脚本不会在共享参考目录自动建索引。

## 验收和交付

检查 `acceptance.json` 的 `passed` 与 `run_manifest.json` 的 `status`，不能仅看退出码。交付：

- `mapped.gam`：图比对结果；`projected.bam` 与 `.csi`：指定参考路径的坐标排序比对。
- `flagstat.txt`、`graph-stats.txt`、`idxstats.txt`：质量统计。
- `run_manifest.json`：配置、版本、输入哈希、执行命令、阶段和失败原因。
- `acceptance.json`：BAM 可读、坐标字典、样本标识、primary reads 数和映射数检查。
- `report.md`：范围、统计和输出清单。只有通过检查才报告“图比对流程完成”。

0.1 版可执行终点是 BAM/QC，**不是已完成小变异/SV 分型**。如用户要求变异结果，继续 [后续分析指南](references/inputs-and-downstream.md) 中对应分支，单独记录工具版本、VCF 验收和未验证范围；不能把指南描述当执行成功。

## 输入和结果保护

保持原始数据、图参考和现有会话不变。结果目录必须全新；失败保留日志，修正原因后用新目录重试。不要删除原结果或自动清理共享参考。参考 `.dist` 在任务内复制，避免 vg 对共享索引写入。资源不足时报告实际缺项。

模型只需要摘要、配置和产物索引，不自动上传完整 FASTQ、BAM 或基因型文件。没有真值测试前，不宣称检出率提升；没有专门验证前，不输出诊断、致病分级或用药结论。
