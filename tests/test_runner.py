import contextlib
import gzip
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runner", ROOT / "skills/human-pangenome-reanalysis/scripts/run.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = {"sample": "sample1", "r1": str(self.root / "R1.fq"), "r2": str(self.root / "R2.fq"), "output": str(self.root / "result"), "threads": 2, "min_free_gb": 0.001, "reference_manifest": str(self.root / "bundle.json")}
        for i in (1, 2):
            Path(self.config[f"r{i}"]).write_text(f"@read1/{i}\nACGT\n+\nIIII\n")
        files = {}
        for key in runner.REFERENCE_KEYS:
            name = "reference.fa.fai" if key == "fai" else "reference.fa" if key == "fasta" else key
            path = self.root / name
            content = "chr1\t4\t6\t4\t5\n" if key == "fai" else ">chr1\nACGT\n" if key == "fasta" else key
            path.write_text(content)
            files[key] = {"path": str(path), "sha256": runner.sha256(path)}
        self.reference = {"label": "test", "source": "synthetic", "coordinate_system": "TEST", "vg_version": runner.VG_VERSION, "paths": ["chr1"], "files": files}
        self.save_reference()

    def save_reference(self):
        Path(self.config["reference_manifest"]).write_text(json.dumps(self.reference))

    @contextlib.contextmanager
    def environment(self):
        def capture(args):
            if args == ["vg", "version"]:
                return f"vg version v{runner.VG_VERSION}\n"
            if args == ["samtools", "--version"]:
                return "samtools 1.19\n"
            return "chr1\n"
        with patch.object(runner.sys, "platform", "linux"), patch.object(runner.shutil, "which", return_value="/bin/test"), patch.object(runner, "capture", side_effect=capture):
            yield

    def check(self):
        with self.environment():
            return runner.preflight(self.config)

    def test_preflight_leaves_inputs_and_output_untouched(self):
        before = {p.name: runner.sha256(p) for p in self.root.iterdir()}
        self.assertEqual(self.check()["pairs"], 1)
        self.assertEqual(before, {p.name: runner.sha256(p) for p in self.root.iterdir()})
        self.assertFalse(Path(self.config["output"]).exists())

    def test_gzip_pairs(self):
        for i in (1, 2):
            path = self.root / f"R{i}.fq.gz"
            with gzip.open(path, "wt") as handle:
                handle.write(Path(self.config[f"r{i}"]).read_text())
            self.config[f"r{i}"] = str(path)
        self.assertEqual(self.check()["pairs"], 1)

    def test_pair_count_name_and_quality_mismatches(self):
        for content in ("@other/2\nACGT\n+\nIIII\n", "@read1/2\nACGT\n+\nIII\n", "@read1/1\nACGT\n+\nIIII\n", "@read1/2\nACGT\n+\nIIII\n@extra/2\nACGT\n+\nIIII\n"):
            with self.subTest(content=content):
                Path(self.config["r2"]).write_text(content)
                with self.assertRaises(ValueError):
                    self.check()

    def test_existing_output_not_overwritten(self):
        out = Path(self.config["output"])
        out.mkdir()
        (out / "keep.txt").write_text("user result")
        with self.assertRaisesRegex(ValueError, "不会覆盖"):
            self.check()
        self.assertEqual((out / "keep.txt").read_text(), "user result")

    def test_same_fastq_rejected(self):
        self.config["r2"] = self.config["r1"]
        with self.assertRaisesRegex(ValueError, "同一文件"):
            self.check()

    def test_bad_hash_and_coordinate_rejected(self):
        self.reference["files"]["gbz"]["sha256"] = "0" * 64
        self.save_reference()
        with self.assertRaisesRegex(ValueError, "校验不一致"):
            self.check()
        self.reference["files"]["gbz"]["sha256"] = runner.sha256(self.root / "gbz")
        self.reference["paths"] = ["chr2"]
        self.save_reference()
        with self.assertRaisesRegex(ValueError, "FASTA"):
            self.check()

    def test_missing_graph_path_and_wrong_version_rejected(self):
        with self.environment(), patch.object(runner, "capture", side_effect=[f"vg version v{runner.VG_VERSION}", "samtools 1.19", "chr2\n"]):
            with self.assertRaisesRegex(ValueError, "图中缺少"):
                runner.preflight(self.config)
        with self.environment(), patch.object(runner, "capture", return_value="vg version v1.2.3"):
            with self.assertRaisesRegex(ValueError, "实际为"):
                runner.preflight(self.config)

    def test_platform_and_missing_tool_rejected(self):
        with self.environment(), patch.object(runner.sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError, "Linux"):
                runner.preflight(self.config)
        with self.environment(), patch.object(runner.shutil, "which", return_value=None):
            with self.assertRaisesRegex(ValueError, "缺少"):
                runner.preflight(self.config)

    def test_failure_keeps_manifest_and_inputs(self):
        before = {p.name: runner.sha256(p) for p in self.root.iterdir()}
        with self.environment(), patch.object(runner.subprocess, "run") as execute:
            execute.return_value.returncode = 9
            with self.assertRaisesRegex(ValueError, "giraffe 失败"):
                runner.run(self.config)
        out = Path(self.config["output"])
        self.assertFalse(json.loads((out / "acceptance.json").read_text(encoding="utf-8"))["passed"])
        self.assertEqual(json.loads((out / "run_manifest.json").read_text(encoding="utf-8"))["status"], "failed")
        self.assertEqual(before, {p.name: runner.sha256(p) for p in self.root.iterdir() if p.is_file()})
        # Restore permission only on this test's private copy, for Windows temp cleanup.
        (out / "reference.dist").chmod(0o600)


if __name__ == "__main__":
    unittest.main()
