# 环境与参考资源

## 先检查，再配置

1. 在 OMaaX 服务器管理中选择 Linux 服务器，确认普通服务器或调度集群以及任务工作目录。Windows 内置分析环境不能直接运行此流程。
2. 检查 `python3 --version`（需要 3.10+）、`vg version`、`samtools --version`、可用 CPU、内存、工作盘空间。现有环境满足时直接复用。
3. 缺依赖时仅准备此工具的隔离环境，不改用户默认环境；Conda/Bioconda 或容器均可。安装命令必须使用实际存在的版本；本适配器固定 vg 1.78.0。SAMtools 实际版本写进运行记录。
4. 大数据任务交给现有任务管理/调度通道，不在登录节点或桌面终端长时间阻塞。用户可以查看任务状态与阶段日志。

Linux x86_64 可使用 vg 官方固定二进制；请安装到本工具专属目录，不覆盖已有 `vg`。以下仅下载约 56 MB 的软件，不下载参考基因组：

```bash
mkdir -p /absolute/new-tool-env/bin
curl --fail --location --retry 3 https://github.com/vgteam/vg/releases/download/v1.78.0/vg -o /absolute/new-tool-env/bin/vg
echo '5ddfee24c34f3656b0e71a5c2ffb65275781a7353d9147ae6b5d7323029c7799  /absolute/new-tool-env/bin/vg' | sha256sum -c -
chmod +x /absolute/new-tool-env/bin/vg
export PATH=/absolute/new-tool-env/bin:$PATH
vg version
```

上面的目录应预先确认是全新专属目录。ARM64 必须改用官方对应架构发行物并记录其 SHA256，不能混用上述 x86_64 文件。

SAMtools 使用服务器已核验的环境；若需 Conda，单独创建环境，例如 `conda create -n omaax-pangenome -c conda-forge -c bioconda python=3.11 samtools`，再记录解析出的版本和 `conda list --explicit`。这条安装命令的解析结果会随时间改变；它不是固定环境锁文件。首次使用须先跑仓库的小数据测试，不能把“安装成功”当分析成功。

## 配套参考清单

复制 `assets/reference.example.json`，填写每个文件的绝对路径与 `sha256sum` 值。

| 文件/字段 | 需要核实 |
| --- | --- |
| `gbz` | 同一个图版本、参考序列、人群/单倍型面板；明确样本是否在面板中 |
| `dist`、`min`、`zipcodes` | 与 GBZ 配套且与 vg 1.78.0 兼容，不能拼接不同发行版的索引 |
| `fasta`、`fai` | 对应目标线性参考与正确索引；普通未压缩 FASTA，FAI 位于 FASTA 同目录 |
| `paths` | 本次投影的准确参考路径名；用 `vg paths -x graph.gbz -L` 核实 |
| `coordinate_system` | 明确 GRCh37、GRCh38 或 CHM13；`TEST` 只用于合成测试 |
| `label`、`source` | 参考发行版、真实下载页/来源；研究报告可回溯 |

路径名必须同时存在于图和 FASTA/FAI 中。若图使用 `GRCh38#0#chr1` 而 FASTA 使用 `chr1`，本版会阻止执行。需由参考包维护者准备匹配的路径字典/FASTA 并单独验收；不要让助手随意做字符串替换。更不能给 CHM13 BAM 换一个 GRCh38 标签。

哈希能确认文件未变化，不能独自证明这些文件科学上配套。只采用来源明确且已核验的参考包。本版不自动下载 CPC.Ref2/HPRC 完整资源，不假定网页上任意文件都构成可运行包。

## 资源和失败处理

- 先做局部参考试跑，再按峰值内存、磁盘和耗时估算全基因组。不能用小参考的内存代表完整人类图的需求。
- `min_free_gb` 是用户本次预留磁盘要求；预检查还以输入体积和距离索引做粗估，取较大值，仍不保证运行中永不耗尽空间。
- `.dist` 会复制到任务目录，其他参考只读使用；GAM、未排序 BAM、排序 BAM 和日志都会保留，需计入磁盘。
- 进程失败/被中断时查看 `run_manifest.json` 和对应 `*.stderr.log`。缺依赖或索引错误先修原因，使用新输出目录重跑；0.1 版不自动断点续跑，避免拿部分文件冒充完整结果。
- 低映射率首先排查物种、单双端、参考版本、路径选择与读长；不能立即宣称生物学差异。
