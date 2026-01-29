"""
CommandSafetyChecker 单元测试
测试安全检查规则
"""

import pytest


class TestCommandSafetyChecker:
    """CommandSafetyChecker 测试类"""

    def test_is_dangerous_rm_rf(self):
        """测试 rm -rf 命令检测"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险的 rm 命令
        assert checker.is_dangerous_command("rm -rf /") is True
        assert checker.is_dangerous_command("rm -rf /*") is True
        assert checker.is_dangerous_command("rm -rf /home/user") is True
        assert checker.is_dangerous_command("sudo rm -rf /") is True
        
        # 相对安全的 rm 命令（仍然可能被检测）
        assert checker.is_dangerous_command("rm temp.txt") is False

    def test_is_dangerous_dd_command(self):
        """测试 dd 命令检测"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险的 dd 命令
        assert checker.is_dangerous_command("dd if=/dev/zero of=/dev/sda") is True
        assert checker.is_dangerous_command("dd if=/dev/random of=/dev/sdb1") is True

    def test_is_dangerous_chmod(self):
        """测试 chmod 命令检测"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险的 chmod 命令
        assert checker.is_dangerous_command("chmod 777 /etc/passwd") is True
        
        # 相对安全的 chmod 命令
        assert checker.is_dangerous_command("chmod 755 script.sh") is False

    def test_is_dangerous_system_commands(self):
        """测试系统命令检测"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险的系统命令
        assert checker.is_dangerous_command("shutdown -h now") is True
        assert checker.is_dangerous_command("reboot") is True
        assert checker.is_dangerous_command("halt") is True

    def test_is_dangerous_safe_commands(self, sample_safe_commands):
        """测试安全命令"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        for cmd in sample_safe_commands:
            assert checker.is_dangerous_command(cmd) is False, f"{cmd} should be safe"

    def test_is_dangerous_empty_command(self):
        """测试空命令"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        assert checker.is_dangerous_command("") is False
        assert checker.is_dangerous_command(None) is False
        assert checker.is_dangerous_command("   ") is False

    def test_get_danger_level_critical(self):
        """测试关键危险等级"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 关键危险命令
        assert checker.get_danger_level("rm -rf /") == "critical"
        assert checker.get_danger_level("dd if=/dev/zero of=/dev/sda") == "critical"
        assert checker.get_danger_level("shutdown -h now") == "critical"
        assert checker.get_danger_level("reboot") == "critical"

    def test_get_danger_level_dangerous(self):
        """测试高危等级"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 高危命令
        assert checker.get_danger_level("chmod 777 /tmp/test") == "dangerous"
        assert checker.get_danger_level("killall process") == "dangerous"

    def test_get_danger_level_safe(self):
        """测试安全等级"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 安全命令
        assert checker.get_danger_level("ls -la") == "safe"
        assert checker.get_danger_level("pwd") == "safe"
        assert checker.get_danger_level("echo hello") == "safe"

    def test_get_safety_warnings(self):
        """测试安全警告信息"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险命令应该有警告
        warnings = checker.get_safety_warnings("rm -rf /")
        assert len(warnings) > 0
        assert any("CRITICAL" in w or "WARNING" in w for w in warnings)
        
        # 安全命令不应该有警告
        warnings = checker.get_safety_warnings("ls -la")
        assert len(warnings) == 0

    def test_should_force_confirmation(self):
        """测试强制确认判断"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险命令应该强制确认
        assert checker.should_force_confirmation("rm -rf /") is True
        assert checker.should_force_confirmation("sudo rm -rf /home") is True
        
        # 安全命令不需要强制确认
        assert checker.should_force_confirmation("ls -la") is False

    def test_should_disable_auto_copy(self):
        """测试禁用自动复制判断"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险命令应该禁用自动复制
        assert checker.should_disable_auto_copy("rm -rf /") is True
        
        # 安全命令可以自动复制
        assert checker.should_disable_auto_copy("ls -la") is False

    def test_get_safety_info(self):
        """测试获取完整安全信息"""
        from aicmd.safety_checker import CommandSafetyChecker
        
        checker = CommandSafetyChecker()
        
        # 危险命令
        info = checker.get_safety_info("rm -rf /")
        
        assert info["is_dangerous"] is True
        assert info["danger_level"] in ["critical", "dangerous", "warning"]
        assert len(info["warnings"]) > 0
        assert info["force_confirmation"] is True
        assert info["disable_auto_copy"] is True
        
        # 安全命令
        info = checker.get_safety_info("ls -la")
        
        assert info["is_dangerous"] is False
        assert info["danger_level"] == "safe"
        assert len(info["warnings"]) == 0


class TestCustomDangerousPatterns:
    """自定义危险模式测试"""

    def test_custom_patterns_from_config(self):
        """测试从配置加载自定义模式"""
        from aicmd.safety_checker import CommandSafetyChecker
        from aicmd.config_manager import ConfigManager
        from unittest.mock import MagicMock
        
        # 创建带自定义模式的配置
        mock_config = MagicMock(spec=ConfigManager)
        mock_config.get.return_value = [r"\bmycustomcmd\b"]
        
        checker = CommandSafetyChecker(config_manager=mock_config)
        
        # 自定义模式应该被检测
        assert checker.is_dangerous_command("mycustomcmd --force") is True
