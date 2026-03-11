"""Tests for jcli.template.renderer."""

import pytest
from jcli.template.renderer import render_template, render_template_string


class TestRenderTemplate:
    def test_render_basic(self, template_file, vars_file):
        result = render_template(template_file, vars_file)
        assert "ge-0/0/0" in result
        assert "192.168.1.1/24" in result
        assert "Uplink to core" in result

    def test_render_produces_set_commands(self, template_file, vars_file):
        result = render_template(template_file, vars_file)
        lines = [l for l in result.strip().splitlines() if l.strip()]
        assert lines[0].startswith("set interfaces")
        assert lines[1].startswith("set interfaces")

    def test_missing_template_file(self, tmp_path, vars_file):
        fake_template = str(tmp_path / "nope.j2")
        with pytest.raises(FileNotFoundError, match="Template file not found"):
            render_template(fake_template, vars_file)

    def test_missing_vars_file(self, template_file, tmp_path):
        fake_vars = str(tmp_path / "nope.yaml")
        with pytest.raises(FileNotFoundError, match="Variables file not found"):
            render_template(template_file, fake_vars)

    def test_invalid_yaml(self, template_file, tmp_path):
        bad_yaml = tmp_path / "bad.yaml"
        bad_yaml.write_text(":\n  - :\n    : [invalid yaml: {{\n")
        with pytest.raises(ValueError, match="Error parsing YAML"):
            render_template(template_file, str(bad_yaml))

    def test_empty_vars_file(self, template_file, tmp_path):
        empty_yaml = tmp_path / "empty.yaml"
        empty_yaml.write_text("")
        with pytest.raises(ValueError, match="empty or invalid"):
            render_template(template_file, str(empty_yaml))

    def test_template_rendering_error(self, tmp_path):
        bad_template = tmp_path / "bad.j2"
        bad_template.write_text("{% for x in %}broken{% endfor %}")
        vars_f = tmp_path / "v.yaml"
        vars_f.write_text("key: value\n")
        with pytest.raises(ValueError, match="Error rendering template"):
            render_template(str(bad_template), str(vars_f))


class TestRenderTemplateString:
    def test_basic_render(self):
        template = "hostname {{ name }}"
        variables = "name: lab-router\n"
        result = render_template_string(template, variables)
        assert result == "hostname lab-router"

    def test_multiline(self):
        template = "set system host-name {{ hostname }}\nset system domain-name {{ domain }}"
        variables = "hostname: r1\ndomain: lab.local\n"
        result = render_template_string(template, variables)
        assert "r1" in result
        assert "lab.local" in result

    def test_invalid_yaml(self):
        with pytest.raises(ValueError, match="Error parsing YAML"):
            render_template_string("{{ x }}", ":\n  - :\n    : [invalid yaml: {{\n")

    def test_empty_vars(self):
        with pytest.raises(ValueError, match="empty or invalid"):
            render_template_string("{{ x }}", "")

    def test_template_syntax_error(self):
        with pytest.raises(ValueError, match="Error rendering template"):
            render_template_string("{% for x in %}broken{% endfor %}", "key: value\n")
