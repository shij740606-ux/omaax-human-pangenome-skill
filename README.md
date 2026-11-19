# OMaaX 人类泛基因组重分析 skill

按需下载的研究工具：让 OMaaX 在用户已配置的 Linux 服务器上核对双端短读长 WGS 数据和参考包，运行 **vg Giraffe → 指定参考路径投影 → 排序 BAM / 索引 / QC**。

它不是把旧 VCF 改几个坐标，也不把完整参考基因组塞进桌面安装包。安装 skill 不等于安装计算环境。

## 下载与使用

- OMaaX 工具市场搜索「人类泛基因组重分析」，添加后在项目对话中使用。目录接入需要含此条目的 OMaaX 版本；已有旧版本不会凭 GitHub 发布自动出现新条目。
- 通用 skill 客户端：安装本仓库 `skills/human-pangenome-reanalysis` 目录。
- 手动运行：读 [使用说明](skills/human-pangenome-reanalysis/SKILL.md)，准备 [环境和参考包](skills/human-pangenome-reanalysis/references/setup.md)，复制并填写 [任务配置](skills/human-pangenome-reanalysis/assets/config.example.json)，然后：

```bash
python3 skills/human-pangenome-reanalysis/scripts/run.py --config /absolute/task.json --check
python3 skills/human-pangenome-reanalysis/scripts/run.py --config /absolute/task.json
```

对话示例：

> 使用人类泛基因组重分析。数据在已连接服务器的 /data/sample/R1.fastq.gz 和 R2.fastq.gz，参考清单在 /refs/bundle.json。先检查环境和坐标，再运行到新任务目录，保留原文件。报告比对质量和产物路径，不做临床结论。

## 0.1 版范围

| 能力 | 状态 |
| --- | --- |
| 双端 FASTQ / gzip FASTQ 检查、图比对、指定路径投影、BAM / CSI / QC | 可执行脚本 |
| 已有 BAM/CRAM 恢复 reads | 使用说明；需确认原文件保留的 reads 和解码参考 |
| DeepVariant 小变异分析、PanGenie 已知面板分型、旧结果比较 | 接续指南；未作为已验证的一键后端 |
| 全人类基因组准确率、HG002/HG005 真值对照、临床解释 | 尚未验证，不作准确率或诊断承诺 |

脚本拒绝覆盖现有目录；输入只读；距离索引复制到本次任务目录再使用。失败保留日志，重新运行使用新目录。不会自动下载大数据、改变已有环境或把测序数据上传到模型服务。

## 验证

```bash
python3 -m unittest discover -s tests -v
python3 tests/smoke.py /absolute/new-smoke-work
```

第二条要求 Linux、vg 1.78.0、SAMtools、bgzip 和 tabix。测试现场生成约 12 kb 的合成参考及双端 reads，真正执行图构建、比对、投影与 QC。它只验证工具链可运行，不是人类数据准确性验证。实际通过情况以仓库 Actions 记录为准。

## 来源与授权

这是独立实现的适配代码，采用 MIT 许可证。研究方向参考 Shuhua Group 的 CPC 工作；没有复制其未明确授权的管线代码。vg、SAMtools、DeepVariant、PanGenie 和参考数据各自的许可继续适用。详见 [来源与边界](skills/human-pangenome-reanalysis/references/sources.md)。
