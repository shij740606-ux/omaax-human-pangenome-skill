# 输入恢复与接续分析

以下是执行指导，**不属于 0.1 版已实测的一键分析后端**。助手使用时需要记录实际命令、版本和验收结果，未执行的步骤保持“未执行”。

## 已有 BAM / CRAM

先查看 header 和原线性参考版本，确认是双端 WGS，保留了 SEQ、QUAL、配对、未比对 reads。硬剪切掉的序列、先前过滤掉的 reads 无法恢复；不要宣称与原始 FASTQ 等价。CRAM 需要与编码时完全一致的原参考 FASTA。

在全新转换目录，SAMtools 先按读名整理，再分开输出双端、单端残留和未分类 reads。示意命令（换成实际绝对路径；不得使用已有输出目录）：

```bash
samtools quickcheck /data/original.bam
samtools collate -@ 4 -o /new-run/name-collated.bam /data/original.bam
samtools fastq -@ 4 -n \
  -1 /new-run/R1.fastq -2 /new-run/R2.fastq \
  -s /new-run/singletons.fastq -0 /new-run/other.fastq \
  /new-run/name-collated.bam
```

CRAM 先使用 `samtools view -T /refs/original-reference.fa -b -o /new-run/decoded.bam /data/original.cram` 显式解码，再执行上面的整理。保存每步 stderr，并核对 primary read 数、双端数、单端残留和无法恢复数量。不要把 `singletons` 或 `other` 静默丢弃；本版仅把完整双端部分交给图比对，报告其范围。

## 小变异：DeepVariant

图比对后，使用与所选坐标一致的 FASTA 和经过验收的排序 BAM。先评估重复读段处理、局部重比对、测序平台与模型是否适用。脚本已启用 `vg surject --left-align`，这不能替代完整的变异准确性验证。

按 [DeepVariant 官方 quick start](https://github.com/google/deepvariant/blob/r1.9/docs/deepvariant-quick-start.md) 为本次环境固定容器版本/摘要、模型和调用参数。WGS 模型不应直接套到 WES、RNA 或长读长。在新子目录运行，保留 VCF、gVCF、日志和方法配置。没有足够环境时明确缺项，不自动下载多 GB 的镜像或模型而不告知用户。

验收至少包括：压缩 VCF 可读且可索引、样本 ID 正确、contig 与同一参考字典一致、REF 等位基因能在该 FASTA 验证、记录数及过滤类别有统计。空 VCF 可以是有效结果，不能人为补出变异；退出 0 但文件缺失不能算完成。

## 已知面板分型：PanGenie

按 [PanGenie 官方说明](https://github.com/eblerjana/pangenie) 准备配套的无重叠、单倍型已定相变异面板和参考，固定软件/面板版本。单独提交任务，不把其输出叫作“新发现全部 SV”。面板中没有的位点或低可分辨区域需要标记未覆盖/不确定。

测试样本若已在图或单倍型面板中，不能用来声称独立泛化准确率。比较时使用排除测试样本的面板，或明确仅作流程复现。

## 与旧线性结果比较

先确认同一个样本、同一可比较区域、同一坐标和兼容的变异表示。不同坐标先选经过验证的转换方案，不能简单改染色体名。保留原 VCF，在新文件中规范化；报告共有、新增、缺失、过滤差异、覆盖与无法对应位点。

变异数量增加不等于准确率提高。HG002/HG005 的 precision/recall 必须使用匹配的 GIAB 真值和高可信区域，SNP/indel 分开计分，SV 另用合适真值和匹配定义。原始数据、图面板、caller/模型变化都记录，避免把 caller 差异归因于泛基因组本身。

若用户只有 VCF，可做上述比较/注释准备；不能从 VCF 推回所有 reads 再声称完成图重比对。
