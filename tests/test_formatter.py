"""Tests for jcli.output.formatter functions."""

import json
import pytest
from jcli.output.formatter import (
    format_device_list,
    format_facts,
    format_command_result,
    format_batch_results,
    format_multi_results,
)


class TestFormatDeviceList:
    def test_text_mode(self):
        routers = ["r1", "r2", "r3"]
        result = format_device_list(routers, json_mode=False)
        assert result == "r1\nr2\nr3"

    def test_json_mode(self):
        routers = ["r1", "r2"]
        result = format_device_list(routers, json_mode=True)
        parsed = json.loads(result)
        assert parsed == {"routers": ["r1", "r2"]}

    def test_empty_list_text(self):
        result = format_device_list([], json_mode=False)
        assert result == ""

    def test_empty_list_json(self):
        result = format_device_list([], json_mode=True)
        parsed = json.loads(result)
        assert parsed == {"routers": []}

    def test_single_device(self):
        result = format_device_list(["only_one"], json_mode=False)
        assert result == "only_one"


class TestFormatFacts:
    def test_text_mode(self):
        facts = {"hostname": "router1", "model": "vSRX", "version": "22.1R1.10"}
        result = format_facts("r1", facts, json_mode=False)
        assert "hostname: router1" in result
        assert "model: vSRX" in result
        assert "version: 22.1R1.10" in result

    def test_json_mode(self):
        facts = {"hostname": "router1", "model": "vSRX"}
        result = format_facts("r1", facts, json_mode=True)
        parsed = json.loads(result)
        assert parsed["router"] == "r1"
        assert parsed["facts"]["hostname"] == "router1"
        assert parsed["facts"]["model"] == "vSRX"

    def test_empty_facts(self):
        result = format_facts("r1", {}, json_mode=False)
        assert result == ""

    def test_empty_facts_json(self):
        result = format_facts("r1", {}, json_mode=True)
        parsed = json.loads(result)
        assert parsed["router"] == "r1"
        assert parsed["facts"] == {}


class TestFormatCommandResult:
    def test_text_mode_returns_output_only(self):
        result = format_command_result("r1", "show version", "Junos: 22.1", json_mode=False)
        assert result == "Junos: 22.1"

    def test_json_mode(self):
        result = format_command_result("r1", "show version", "Junos: 22.1", json_mode=True)
        parsed = json.loads(result)
        assert parsed["router"] == "r1"
        assert parsed["command"] == "show version"
        assert parsed["output"] == "Junos: 22.1"

    def test_json_mode_with_duration(self):
        result = format_command_result(
            "r1", "show bgp", "bgp output", duration=1.234, json_mode=True
        )
        parsed = json.loads(result)
        assert parsed["duration"] == 1.234

    def test_json_mode_without_duration(self):
        result = format_command_result("r1", "show bgp", "bgp output", json_mode=True)
        parsed = json.loads(result)
        assert "duration" not in parsed

    def test_text_mode_ignores_duration(self):
        result = format_command_result(
            "r1", "show version", "output", duration=0.5, json_mode=False
        )
        assert result == "output"


class TestFormatMultiResults:
    def test_text_mode(self):
        results = [
            {"command": "show version", "output": "Junos: 22.1",
             "status": "success", "duration": 0.5},
            {"command": "show bgp summary", "output": "bgp output",
             "status": "success", "duration": 0.3},
        ]
        result = format_multi_results("r1", results, json_mode=False)
        assert "=== show version ===" in result
        assert "Junos: 22.1" in result
        assert "=== show bgp summary ===" in result
        assert "bgp output" in result

    def test_json_mode(self):
        results = [
            {"command": "show version", "output": "v1", "status": "success", "duration": 0.5},
            {"command": "show bgp", "output": "err", "status": "failed", "duration": 1.0},
        ]
        result = format_multi_results("r1", results, json_mode=True)
        parsed = json.loads(result)
        assert parsed["router"] == "r1"
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["command"] == "show version"
        assert parsed["results"][1]["status"] == "failed"


class TestFormatBatchResults:
    def test_text_mode(self):
        results = [
            {"router": "r1", "output": "version1"},
            {"router": "r2", "output": "version2"},
        ]
        result = format_batch_results(results, json_mode=False)
        assert "=== r1 ===" in result
        assert "version1" in result
        assert "=== r2 ===" in result
        assert "version2" in result

    def test_json_mode(self):
        results = [
            {"router": "r1", "status": "success", "output": "v1", "duration": 0.5},
            {"router": "r2", "status": "failed", "output": "timeout", "duration": 30.0},
        ]
        result = format_batch_results(results, json_mode=True)
        parsed = json.loads(result)
        assert len(parsed["results"]) == 2
        assert parsed["results"][0]["router"] == "r1"
        assert parsed["results"][1]["status"] == "failed"

    def test_empty_results_text(self):
        result = format_batch_results([], json_mode=False)
        assert result == ""

    def test_empty_results_json(self):
        result = format_batch_results([], json_mode=True)
        parsed = json.loads(result)
        assert parsed["results"] == []
