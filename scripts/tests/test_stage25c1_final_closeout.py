#!/usr/bin/env python3
"""ASIP Stage 2.5C-1F2 — Real path confinement and negative test closure"""

import json, os, sys, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
REPO = os.path.dirname(SCRIPTS)

from ai.prompt_registry import (
    _validate_package, get_prompt_package,
    resolve_confined_path, PromptRegistryError,
    REPO_ROOT as REG_REPO, SCHEMAS_OUTPUT_DIR,
)
from ai.prompt_renderer import render_prompt, PromptRenderError
from ai.output_contracts import get_output_schema, OutputContractError

def _write(p, c):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(c)


class TestF7_RealAbsPath(unittest.TestCase):
    """F7: Construct package with absolute system_template, validate fails."""

    def test_abs_system_template_rejected(self):
        tmp = tempfile.mkdtemp(prefix="f7_")
        try:
            # create a real file at an absolute path
            abs_path = os.path.join(tmp, "real_system.md")
            _write(abs_path, "fake content")
            # Package with absolute path
            bad_pkg = _make_package(system_template=abs_path)
            _write(os.path.join(tmp, "u.md"), "{{ x }}")
            _write(os.path.join(tmp, "x.json"), "{}")
            _write(os.path.join(tmp, "package.json"),
                   json.dumps(bad_pkg, ensure_ascii=False, indent=2))
            errs = _validate_package(bad_pkg, "test", tmp, strict_schema=False)
            self.assertTrue(any("system_template" in e for e in errs),
                            "F7: should reject absolute system_template: %s" % errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestF8_RealDotdot(unittest.TestCase):
    """F8: Construct package with ../ user_template, validate fails."""

    def test_dotdot_user_template_rejected(self):
        tmp = tempfile.mkdtemp(prefix="f8_")
        try:
            bad_pkg = _make_package(user_template="../outside.md")
            _write(os.path.join(tmp, "s.md"), "{{ x }}")
            _write(os.path.join(tmp, "x.json"), "{}")
            _write(os.path.join(tmp, "package.json"),
                   json.dumps(bad_pkg, ensure_ascii=False, indent=2))
            errs = _validate_package(bad_pkg, "test", tmp, strict_schema=False)
            self.assertTrue(any("user_template" in e for e in errs),
                            "F8: should reject ../ user_template: %s" % errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestF9_RealOutputSchemaAbs(unittest.TestCase):
    """F9: Construct package with absolute output_schema, validate fails."""

    def test_abs_output_schema_rejected(self):
        tmp = tempfile.mkdtemp(prefix="f9_")
        try:
            real_json = os.path.join(tmp, "outside.json")
            _write(real_json, "{}")
            bad_pkg = _make_package(output_schema=real_json)
            _write(os.path.join(tmp, "s.md"), "{{ x }}")
            _write(os.path.join(tmp, "u.md"), "{{ x }}")
            _write(os.path.join(tmp, "package.json"),
                   json.dumps(bad_pkg, ensure_ascii=False, indent=2))
            errs = _validate_package(bad_pkg, "test", tmp, strict_schema=False)
            self.assertTrue(any("output_schema" in e for e in errs),
                            "F9: should reject absolute output_schema: %s" % errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestF10_SymlinkEscape(unittest.TestCase):
    """F10: Symlink/simulated escape from version_dir rejected."""

    def _setup_inside_outside(self):
        inside = tempfile.mkdtemp(prefix="f10_in_")
        outside = tempfile.mkdtemp(prefix="f10_out_")
        real_file = os.path.join(outside, "target.md")
        _write(real_file, "outside content")
        return inside, outside, real_file

    def test_symlink_escape_rejected_by_resolve(self):
        """F10: Real symlink or mock Path.resolve returning outside path rejected."""
        inside = tempfile.mkdtemp(prefix="f10_test_")
        try:
            # Create a real file inside
            _write(os.path.join(inside, "link.md"), "real content")

            # Mock Path.resolve to return an outside path (simulating symlink)
            from unittest.mock import patch, MagicMock
            from pathlib import Path as _Path
            outside_path = _Path("/outside/target.md")

            with patch('ai.prompt_registry.Path') as MockPath:
                mock_instance = MagicMock()
                mock_instance.resolve.return_value = outside_path
                mock_instance.parts = ('link.md',)
                mock_instance.__str__.return_value = os.path.join(
                    inside, "link.md")
                MockPath.return_value = mock_instance

                with self.assertRaises(PromptRegistryError):
                    resolve_confined_path(inside, "link.md", inside,
                                          must_exist=True)
        finally:
            shutil.rmtree(inside, ignore_errors=True)


class TestF14_VersionMismatch(unittest.TestCase):
    """F14: prompt 1.0.0 + schema 1.1 rejected with assertRaises."""

    def test_mismatch_raises(self):
        with self.assertRaises(OutputContractError):
            get_output_schema("article_analysis",
                              prompt_version="1.0.0",
                              output_schema_version="1.1")


class TestF18_ResourceLimit(unittest.TestCase):
    """F18: Six untrusted variables oversized => PromptRenderError."""

    def test_source_text_oversize(self):
        big = "x" * 200000
        with self.assertRaises(PromptRenderError):
            render_prompt("article_analysis", {
                "source_text": big, "country_iso3": "NER", "source_language": "en"
            })

    def test_source_a_oversize(self):
        big = "x" * 200000
        with self.assertRaises(PromptRenderError):
            render_prompt("source_comparison", {
                "source_a": big, "source_b": "ok", "country_iso3": "NER"
            })

    def test_articles_oversize(self):
        big = "x" * 200000
        with self.assertRaises(PromptRenderError):
            render_prompt("event_synthesis", {
                "articles": big, "country_iso3": "NER"
            })

    def test_events_oversize(self):
        big = "x" * 200000
        with self.assertRaises(PromptRenderError):
            render_prompt("daily_security_brief", {
                "report_date": "2026-08-01", "events": big,
                "geographic_scope": "x"
            })

    def test_historical_events_oversize(self):
        big = "x" * 200000
        with self.assertRaises(PromptRenderError):
            render_prompt("trend_forecast", {
                "historical_events": big, "geographic_scope": "x"
            })

    def test_disease_reports_oversize(self):
        big = "x" * 200000
        with self.assertRaises(PromptRenderError):
            render_prompt("disease_risk_analysis", {
                "disease_reports": big, "country_iso3": "NER"
            })


class TestF21_OutOfVersionDir(unittest.TestCase):
    """F21: Template symlinked out of version_dir (but inside repo) rejected."""

    def test_out_of_version_dir_rejected(self):
        """F21: Mock symlink escaping version_dir but inside repo."""
        tmp = tempfile.mkdtemp(prefix="f21_test_")
        try:
            other_dir = os.path.join(tmp, "other_version")
            os.makedirs(other_dir)
            outside_file = os.path.join(other_dir, "real.md")
            _write(outside_file, "template outside")

            # Create link.md inside version_dir
            _write(os.path.join(tmp, "link.md"), "placeholder")

            # Mock Path.resolve to return outside path (inside repo but outside version_dir)
            from unittest.mock import patch, MagicMock
            from pathlib import Path as _Path
            outside_path = _Path(outside_file)

            with patch('ai.prompt_registry.Path') as MockPath:
                mock_instance = MagicMock()
                mock_instance.resolve.return_value = outside_path
                mock_instance.parts = ('link.md',)
                mock_instance.__str__.return_value = os.path.join(
                    tmp, "link.md")
                MockPath.return_value = mock_instance

                with self.assertRaises(PromptRegistryError):
                    resolve_confined_path(tmp, "link.md", tmp, must_exist=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestF22_SchemaOutOfDir(unittest.TestCase):
    """F22: output_schema pointing outside schemas/ai_outputs/ rejected."""

    def test_schema_outside_ai_outputs_rejected(self):
        tmp = tempfile.mkdtemp(prefix="f22_")
        try:
            other = os.path.join(tmp, "schemas", "other")
            os.makedirs(other, exist_ok=True)
            _write(os.path.join(other, "s.json"), "{}")
            bad_pkg = _make_package(
                output_schema=os.path.join("schemas", "other", "s.json")
            )
            _write(os.path.join(tmp, "s.md"), "{{ x }}")
            _write(os.path.join(tmp, "u.md"), "{{ x }}")
            _write(os.path.join(tmp, "package.json"),
                   json.dumps(bad_pkg, ensure_ascii=False, indent=2))
            # Not strictly under schemas/ai_outputs/ - need custom allowed_root
            # This test verifies the concept: schema outside ai_outputs
            errs = _validate_package(bad_pkg, "test", tmp, strict_schema=False,
                                     _output_schema_root=os.path.join(tmp, "schemas", "ai_outputs"))
            self.assertTrue(any("output_schema" in e for e in errs),
                            "F22: schema outside ai_outputs should fail: %s" % errs)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def _make_package(**kw):
    pkg = {
        "prompt_id": "test", "task_type": "test", "version": "1.0.0",
        "status": "active", "system_template": kw.get("system_template", "s.md"),
        "user_template": kw.get("user_template", "u.md"),
        "required_variables": ["x"], "optional_variables": [],
        "untrusted_variables": ["x"],
        "output_schema": kw.get("output_schema", "x.json"),
        "output_schema_version": "1.0", "output_language": "zh-CN",
        "description": "test",
        "checksum": "sha256:" + "a" * 64,
    }
    return pkg


if __name__ == "__main__":
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])
    result = runner.run(suite)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    failed = len(result.failures) + len(result.errors)
    print(f"\nRESULT: PASS={passed} FAIL={failed}")
    sys.exit(0 if failed == 0 else 1)
