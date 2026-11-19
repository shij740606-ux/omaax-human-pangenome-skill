"""Real vg/SAMtools integration on synthetic data, never human accuracy evidence."""
import importlib.util
import json
from pathlib import Path
import random
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runner", ROOT / "skills/human-pangenome-reanalysis/scripts/run.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def command(*args, output=None):
    if output:
        with output.open("xb") as handle:
            subprocess.run([str(x) for x in args], check=True, stdout=handle)
    else:
        subprocess.run([str(x) for x in args], check=True)


def main():
    work = Path(sys.argv[1]).resolve()
    work.mkdir()
    rng = random.Random(20261119)
    seq = "".join(rng.choices("ACGT", k=12000))
    fasta = work / "reference.fa"
    fasta.write_text(">chrTest\n" + seq + "\n")
    command("samtools", "faidx", fasta)
    vcf = work / "panel.vcf"
    alt = next(base for base in "ACGT" if base != seq[2999])
    vcf.write_text(f"##fileformat=VCFv4.2\n##contig=<ID=chrTest,length=12000>\n##FORMAT=<ID=GT,Number=1,Type=String,Description=\"Genotype\">\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tpanel1\nchrTest\t3000\t.\t{seq[2999]}\t{alt}\t.\tPASS\t.\tGT\t0|1\n")
    command("bgzip", "-c", vcf, output=work / "panel.vcf.gz")
    command("tabix", "-p", "vcf", work / "panel.vcf.gz")
    command("vg", "autoindex", "--workflow", "giraffe", "-r", fasta, "-v", work / "panel.vcf.gz", "-p", work / "graph", "-t", "2")
    with (work / "R1.fq").open("w") as left, (work / "R2.fq").open("w") as right:
        for i in range(1200):
            start = rng.randrange(100, 11400)
            fragment = rng.randrange(280, 380)
            r1 = seq[start:start+150]
            r2 = seq[start+fragment-150:start+fragment].translate(str.maketrans("ACGT", "TGCA"))[::-1]
            left.write(f"@read{i}/1\n{r1}\n+\n{'I'*150}\n")
            right.write(f"@read{i}/2\n{r2}\n+\n{'I'*150}\n")
    names = {"gbz": "graph.giraffe.gbz", "dist": "graph.dist", "min": "graph.shortread.withzip.min", "zipcodes": "graph.shortread.zipcodes", "fasta": "reference.fa", "fai": "reference.fa.fai"}
    files = {key: {"path": str(work / name), "sha256": runner.sha256(work / name)} for key, name in names.items()}
    reference = {"label": "synthetic-12kb-1SNP", "source": "tests/smoke.py, seed 20261119", "coordinate_system": "TEST", "vg_version": runner.VG_VERSION, "paths": ["chrTest"], "files": files}
    runner.write_json(work / "bundle.json", reference)
    config = {"sample": "synthetic01", "r1": str(work / "R1.fq"), "r2": str(work / "R2.fq"), "output": str(work / "result"), "threads": 2, "min_free_gb": 0.1, "reference_manifest": str(work / "bundle.json")}
    runner.write_json(work / "task.json", config)
    before = {p.name: runner.sha256(p) for p in work.iterdir() if p.is_file()}
    runner.run(config)
    after = {p.name: runner.sha256(p) for p in work.iterdir() if p.is_file()}
    assert before == after, "Input/reference files changed"
    acceptance = json.loads((work / "result/acceptance.json").read_text())
    assert acceptance["passed"] and acceptance["primary_reads"] == 2400 and acceptance["mapped_fraction"] > 0.95
    print(json.dumps(acceptance, indent=2))


if __name__ == "__main__":
    main()
