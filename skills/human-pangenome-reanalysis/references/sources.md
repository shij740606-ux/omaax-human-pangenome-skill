# 方法来源、许可和验证范围

核对日期：2026-11-19。本 skill 的适配脚本为原创 MIT 实现，未复制以下仓库的管线源码，亦不附带参考基因组或第三方程序。

| 来源 | 用途与边界 |
| --- | --- |
| [Shuhua Group CPC-graph-based-NGS-pipeline](https://github.com/Shuhua-Group/CPC-graph-based-NGS-pipeline/tree/dae393faf7eb8876a1e87174ea399b9760c9e05b) | 研究流程参考；该快照未见明确 LICENSE，未作为发行代码复制 |
| [Shuhua Group CPC2](https://github.com/Shuhua-Group/CPC2/tree/f9d1044b53248a52fec510ddc6a57dfdde824f6e) | CPC.Ref2 研究背景和资源线索；该项目 MIT 不能替其他仓库授权 |
| [vg 1.78.0](https://github.com/vgteam/vg/releases/tag/v1.78.0) | 固定主程序版本；软件及所含依赖遵循其自身许可 |
| [Giraffe 官方短读长说明](https://github.com/vgteam/vg/wiki/Mapping-short-reads-with-Giraffe) | 配套索引、双端 reads、GAM、投影和后处理 |
| [Giraffe 最佳实践](https://github.com/vgteam/vg/wiki/Giraffe-best-practices) | 显式索引、距离索引写入行为、参考路径与资源限制 |
| [SAMtools fastq](https://www.htslib.org/doc/samtools-fasta.html) | 恢复 reads 的要求与限制 |
| [DeepVariant](https://github.com/google/deepvariant) | 后续小变异分析，尚未由本版自动执行验收 |
| [PanGenie](https://github.com/eblerjana/pangenie) | 已知面板分型，不能代替所有新 SV 发现 |
| [GIAB data indexes](https://github.com/genome-in-a-bottle/giab_data_indexes) | 后续独立准确性测试数据入口，当前不捆绑下载 |

## 当前证据级别

- 单元测试覆盖配对、错误路径/哈希、参考路径、平台、输出保护和失败记录。
- Linux smoke 现场生成合成数据，真正调用 vg/SAMtools 构图、比对、投影、索引和读取结果；是否通过以 Actions 记录为准。
- 尚未完成 CPC/HPRC 全人类图、GIAB 真值、临床样本、全基因组性能及应用内完整远程任务闭环验收。
- 不用合成测试报告临床性能，不给 skill 编造评分，不把“下载成功”说成“计算环境已就绪”。
