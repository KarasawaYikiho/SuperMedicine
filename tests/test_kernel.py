import pytest
import yaml
from core.kernel import Kernel

class TestKernel:
    def _create_kernel(self, tmp_path):
        (tmp_path / "config.yaml").write_text(yaml.dump({"project": "test"}))
        (tmp_path / "plugins").mkdir()
        (tmp_path / "policies").mkdir()
        return Kernel(config_path=tmp_path / "config.yaml", plugins_dir=tmp_path / "plugins", policies_dir=tmp_path / "policies")
    def test_init(self, tmp_path):
        assert self._create_kernel(tmp_path) is not None
    def test_config(self, tmp_path):
        assert self._create_kernel(tmp_path).config.get("project") == "test"
    def test_plugin_registry(self, tmp_path):
        assert self._create_kernel(tmp_path).plugin_registry is not None
    def test_event_bus(self, tmp_path):
        assert self._create_kernel(tmp_path).event_bus is not None
