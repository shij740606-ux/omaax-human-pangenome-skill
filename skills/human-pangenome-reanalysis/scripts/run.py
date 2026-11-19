#!/usr/bin/env python3
"""Original, standard-library adapter for paired short-read graph mapping."""
import argparse
import gzip
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

VG_VERSION = "1.78.0"
REFERENCE_KEYS = {"gbz", "dist", "min", "zipcodes", "fasta", "fai"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def absolute(value):
    require(isinstance(value, str) and Path(value).is_absolute(), "配置路径必须是执行服务器的绝对路径")
    return Path(value).resolve()


def existing(value):
    path = absolute(value)
    require(path.is_file() and path.stat().st_size > 0, f"文件不存在或为空：{path}")
    return path


def records(path, mate):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="ascii") as handle:
        while True:
            header = handle.readline().rstrip("\r\n")
            if not header:
                require(not handle.read(1), f"FASTQ 内有空白行：{path}")
                return
            seq = handle.readline().rstrip("\r\n")
            plus = handle.readline().rstrip("\r\n")
            quality = handle.readline().rstrip("\r\n")
            require(header.startswith("@") and len(header) > 1 and plus.startswith("+"), f"FASTQ 四行格式错误：{path}")
            require(seq and len(seq) == len(quality) and re.fullmatch("[ACGTNacgtn]+", seq), f"FASTQ 序列/质量长度或碱基错误：{path}")
            require(all(33 <= ord(c) <= 126 for c in quality), f"FASTQ 质量编码错误：{path}")
            parts = header[1:].split()
            name = parts[0]
            if name.endswith(("/1", "/2")):
                require(name.endswith(f"/{mate}"), f"R1/R2 标记相反：{path}")
                name = name[:-2]
            if len(parts) > 1 and re.match(r"^[12]:", parts[1]):
                require(parts[1].startswith(f"{mate}:"), f"R1/R2 标记相反：{path}")
            yield name


def check_pairs(r1, r2):
    count = 0
    for left, right in itertools.zip_longest(records(r1, 1), records(r2, 2)):
        require(left is not None and right is not None and left == right, f"R1/R2 数量或读名不匹配，第 {count + 1} 对")
        count += 1
    require(count > 0, "没有双端 reads")
    return count


def capture(args):
    result = subprocess.run([str(x) for x in args], check=True, capture_output=True)
    return result.stdout.decode("utf-8", errors="replace")


def preflight(config):
    require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", config["sample"]), "样本 ID 仅允许字母、数字、点、下划线和横线，最长 80 字符")
    require(type(config["threads"]) is int and 1 <= config["threads"] <= 256, "threads 应为 1–256 的整数")
    require(type(config["min_free_gb"]) in (float, int) and 0 < config["min_free_gb"] <= 1000000, "min_free_gb 必须是正数")
    output = absolute(config["output"])
    require(not output.exists() and not Path(config["output"]).is_symlink(), "结果目录已存在，不会覆盖；请设置新的任务目录")
    require(output.parent.is_dir(), "结果目录的父目录必须预先存在")
    r1, r2 = existing(config["r1"]), existing(config["r2"])
    require(not os.path.samefile(r1, r2), "R1 与 R2 不能是同一文件")
    manifest = existing(config["reference_manifest"])
    reference = json.loads(manifest.read_text(encoding="utf-8"))
    require(reference["vg_version"] == VG_VERSION, f"参考包需与已验证 vg {VG_VERSION} 匹配")
    require(reference["coordinate_system"] in {"GRCh37", "GRCh38", "CHM13", "TEST"}, "请明确坐标体系")
    require(isinstance(reference["label"], str) and reference["label"].strip() and isinstance(reference["source"], str) and reference["source"].strip(), "参考清单缺少版本名称或来源")
    require(set(reference["files"]) == REFERENCE_KEYS, "参考清单必须列出 gbz/dist/min/zipcodes/fasta/fai")
    paths = reference["paths"]
    require(isinstance(paths, list) and paths and all(isinstance(x, str) and x and not any(c.isspace() for c in x) for x in paths), "需明确不含空白字符的参考路径名")
    require(len(paths) == len(set(paths)), "参考路径重复")
    files = {}
    for key, entry in reference["files"].items():
        source = existing(entry["path"])
        require(re.fullmatch(r"[a-f0-9]{64}", entry["sha256"]), f"缺少有效 SHA256：{key}")
        require(sha256(source) == entry["sha256"], f"参考文件校验不一致：{key}")
        files[key] = source
    require(len(set(files.values())) == len(files), "参考清单不能重复使用同一文件")
    require(files["fai"] == Path(str(files["fasta"]) + ".fai"), "FAI 必须对应指定 FASTA")
    dictionary = {}
    for line in files["fai"].read_text().splitlines():
        fields = line.split("\t")
        require(len(fields) >= 5 and fields[0] not in dictionary and int(fields[1]) > 0, "FAI 格式或重复序列名错误")
        dictionary[fields[0]] = int(fields[1])
    require(set(paths) <= dictionary.keys(), "目标路径与 FASTA 名称不匹配，不允许隐式改名")
    pairs = check_pairs(r1, r2)
    inputs = {str(p): sha256(p) for p in (r1, r2, manifest)}
    # shortcut: disk estimate is conservative only; whole-genome budgets need a measured pilot.
    required_bytes = max(config["min_free_gb"] * 1024 ** 3, (r1.stat().st_size + r2.stat().st_size) * 10 + files["dist"].stat().st_size)
    require(shutil.disk_usage(output.parent).free >= required_bytes, f"磁盘不足；本次至少预留 {required_bytes / 1024**3:.1f} GiB")
    require(sys.platform.startswith("linux"), "图比对需要 Linux 服务器；Windows 仅用于准备配置")
    require(shutil.which("vg") and shutil.which("samtools"), "服务器环境缺少 vg 或 SAMtools；请按 references/setup.md 配置")
    vg_version = capture(["vg", "version"])
    require(re.search(rf"\bv{re.escape(VG_VERSION)}\b", vg_version), f"需要 vg {VG_VERSION}；实际为 {vg_version.strip()}")
    samtools_version = capture(["samtools", "--version"]).splitlines()[0]
    graph_paths = set(capture(["vg", "paths", "-x", files["gbz"], "-L"]).splitlines())
    require(set(paths) <= graph_paths, "图中缺少指定参考路径；请使用匹配参考包，不能直接修改 contig 名称")
    return {"sample": config["sample"], "pairs": pairs, "inputs_sha256": inputs, "reference": reference,
            "vg": vg_version.strip(), "samtools": samtools_version, "required_free_bytes": required_bytes,
            "dictionary": {name: dictionary[name] for name in paths}}


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(config):
    checked = preflight(config)
    output = absolute(config["output"])
    output.mkdir()  # Exclusive creation prevents overwriting existing results, including concurrent runs.
    state = {"status": "running", "started": time.time(), "config": config, "preflight": checked, "steps": []}

    def save():
        write_json(output / "run_manifest.json", state)

    def step(name, args, stdout=None):
        entry = {"name": name, "argv": [str(x) for x in args], "status": "running", "started": time.time()}
        state["steps"].append(entry)
        save()
        with (output / f"{name}.stderr.log").open("xb") as log, (output / (stdout or f"{name}.stdout.log")).open("xb") as result:
            code = subprocess.run(entry["argv"], cwd=output, stdout=result, stderr=log).returncode
        entry.update(status="passed" if code == 0 else "failed", returncode=code, finished=time.time())
        save()
        require(code == 0, f"{name} 失败（退出码 {code}），查看 {name}.stderr.log")

    save()
    try:
        files = {key: Path(value["path"]) for key, value in checked["reference"]["files"].items()}
        dist = output / "reference.dist"
        shutil.copyfile(files["dist"], dist)
        require(sha256(dist) == checked["reference"]["files"]["dist"]["sha256"], "距离索引副本校验失败")
        dist.chmod(0o444)
        paths_file = output / "reference-paths.txt"
        paths_file.write_text("\n".join(checked["dictionary"]) + "\n")
        threads, sample = str(config["threads"]), config["sample"]
        step("giraffe", ["vg", "giraffe", "-t", threads, "-Z", files["gbz"], "-d", dist, "-m", files["min"], "-z", files["zipcodes"], "-f", config["r1"], "-f", config["r2"], "-N", sample, "-R", sample, "-b", "default"], "mapped.gam")
        step("graph-stats", ["vg", "stats", "-a", output / "mapped.gam"], "graph-stats.txt")
        step("surject", ["vg", "surject", "-t", threads, "-x", files["gbz"], "--read-length", "short", "--left-align", "--into-paths", paths_file, "-N", sample, "-R", sample, "-b", output / "mapped.gam"], "projected.unsorted.bam")
        step("sort", ["samtools", "sort", "-@", threads, "-T", output / "sort-tmp", "-o", output / "projected.bam", output / "projected.unsorted.bam"])
        bam = output / "projected.bam"
        step("quickcheck", ["samtools", "quickcheck", "-v", bam])
        step("index", ["samtools", "index", "-@", threads, "-c", bam])
        step("flagstat", ["samtools", "flagstat", bam], "flagstat.txt")
        step("idxstats", ["samtools", "idxstats", bam], "idxstats.txt")
        header = capture(["samtools", "view", "-H", bam])
        actual = {}
        samples = []
        for line in header.splitlines():
            fields = dict(x.split(":", 1) for x in line.split("\t")[1:] if ":" in x)
            if line.startswith("@SQ\t"):
                actual[fields["SN"]] = int(fields["LN"])
            if line.startswith("@RG\t"):
                samples.append(fields.get("SM"))
        require(actual == checked["dictionary"], "BAM 坐标字典与选定 FASTA 路径/长度不匹配")
        require(samples and set(samples) == {sample}, "BAM 样本标识不匹配")
        primary = int(capture(["samtools", "view", "-c", "-F", "2304", bam]))
        mapped = int(capture(["samtools", "view", "-c", "-F", "2308", bam]))
        require(primary == checked["pairs"] * 2 and mapped > 0, "primary reads 数异常或无读段映射到选定参考")
        require(Path(str(bam) + ".csi").stat().st_size > 0, "BAM 索引为空")
        acceptance = {"passed": True, "scope": "mapping-only", "coordinate_system": checked["reference"]["coordinate_system"], "primary_reads": primary, "mapped_reads": mapped, "mapped_fraction": mapped / primary, "dictionary": actual}
        write_json(output / "acceptance.json", acceptance)
        (output / "report.md").write_text(f"# 泛基因组图比对结果\n\n样本：{sample}\n\n坐标：{acceptance['coordinate_system']}\n\n输入 {checked['pairs']} 对 reads；primary {primary} 条；映射到选定参考 {mapped} 条（{mapped / primary:.2%}）。\n\n产物：mapped.gam、projected.bam / .csi、flagstat.txt、graph-stats.txt、idxstats.txt、run_manifest.json、acceptance.json。\n\n本次完成图比对与投影，没有执行变异调用或临床解释。映射率不是准确率。失败/调试日志和中间文件均保留在本目录。\n", encoding="utf-8")
        state["status"] = "passed"
    except (Exception, KeyboardInterrupt) as error:
        state.update(status="failed", error=str(error) or "interrupted")
        write_json(output / "acceptance.json", {"passed": False, "error": state["error"]})
        raise
    finally:
        state["finished"] = time.time()
        save()
    return output


def main():
    parser = argparse.ArgumentParser(description="人类双端 WGS 泛基因组图比对；只写入全新结果目录")
    parser.add_argument("--config", required=True)
    parser.add_argument("--check", action="store_true", help="完整预检查，不运行比对")
    args = parser.parse_args()
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = preflight(config) if args.check else {"output": str(run(config)), "status": "passed"}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(f"未完成：{error or 'interrupted'}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
