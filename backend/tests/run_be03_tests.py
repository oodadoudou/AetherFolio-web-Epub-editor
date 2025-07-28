#!/usr/bin/env python3
"""
BE-03任务测试运行脚本

此脚本用于运行所有与BE-03任务（规则文件验证）相关的测试用例，
包括安全性测试、性能测试、集成测试等。

使用方法:
    python run_be03_tests.py [options]
    
选项:
    --security      只运行安全性测试
    --performance   只运行性能测试
    --integration   只运行集成测试
    --unicode       只运行Unicode相关测试
    --regex         只运行正则表达式相关测试
    --all           运行所有BE-03测试（默认）
    --verbose       详细输出
    --coverage      生成覆盖率报告
    --html          生成HTML测试报告
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Optional


class BE03TestRunner:
    """BE-03任务测试运行器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = Path(__file__).parent
        
    def run_tests(self, 
                  test_type: Optional[str] = None,
                  verbose: bool = False,
                  coverage: bool = False,
                  html_report: bool = False) -> int:
        """运行测试
        
        Args:
            test_type: 测试类型（security, performance, integration, unicode, regex, all）
            verbose: 是否详细输出
            coverage: 是否生成覆盖率报告
            html_report: 是否生成HTML报告
            
        Returns:
            int: 退出码
        """
        # 构建pytest命令
        cmd = ["python", "-m", "pytest"]
        
        # 添加测试目录
        test_files = self._get_test_files(test_type)
        cmd.extend(test_files)
        
        # 添加标记过滤
        if test_type and test_type != "all":
            cmd.extend(["-m", test_type])
        elif test_type == "all" or test_type is None:
            cmd.extend(["-m", "be03"])
        
        # 添加详细输出
        if verbose:
            cmd.append("-v")
        else:
            cmd.append("-q")
        
        # 添加覆盖率
        if coverage:
            cmd.extend([
                "--cov=backend.services.replace_service",
                "--cov=backend.api.replace",
                "--cov=backend.core.security",
                "--cov-report=term-missing"
            ])
            
            if html_report:
                cmd.append("--cov-report=html:htmlcov")
        
        # 添加HTML报告
        if html_report:
            cmd.extend(["--html=reports/be03_test_report.html", "--self-contained-html"])
        
        # 添加其他有用的选项
        cmd.extend([
            "--tb=short",  # 简短的traceback
            "--strict-markers",  # 严格标记模式
            "--disable-warnings",  # 禁用警告
        ])
        
        print(f"运行命令: {' '.join(cmd)}")
        print("=" * 80)
        
        # 确保报告目录存在
        if html_report:
            reports_dir = self.project_root / "reports"
            reports_dir.mkdir(exist_ok=True)
        
        # 运行测试
        try:
            result = subprocess.run(cmd, cwd=self.project_root, check=False)
            return result.returncode
        except KeyboardInterrupt:
            print("\n测试被用户中断")
            return 130
        except Exception as e:
            print(f"运行测试时出错: {e}")
            return 1
    
    def _get_test_files(self, test_type: Optional[str]) -> List[str]:
        """获取测试文件列表
        
        Args:
            test_type: 测试类型
            
        Returns:
            List[str]: 测试文件路径列表
        """
        test_files = []
        
        if test_type == "security" or test_type == "all" or test_type is None:
            # 安全性测试
            test_files.extend([
                "tests/unit/test_replace_service_security.py",
                "tests/api/test_replace_validation_security.py",
            ])
        
        if test_type == "performance" or test_type == "all" or test_type is None:
            # 性能测试
            test_files.append("tests/performance/test_replace_validation_performance.py")
        
        if test_type == "integration" or test_type == "all" or test_type is None:
            # 集成测试
            test_files.append("tests/integration/test_replace_validation_integration.py")
        
        if test_type == "unicode" or test_type == "all" or test_type is None:
            # Unicode测试（包含在其他测试文件中）
            test_files.extend([
                "tests/unit/test_replace_service_security.py::TestReplaceServiceSecurity::test_validate_rules_unicode_characters",
                "tests/unit/test_replace_service_security.py::TestReplaceServiceSecurity::test_validate_rules_unicode_normalization",
                "tests/unit/test_replace_service_security.py::TestReplaceServiceSecurity::test_validate_rules_unicode_security_issues",
                "tests/api/test_replace_validation_security.py::TestReplaceValidationAPISecurity::test_validate_rules_api_unicode_handling",
                "tests/api/test_replace_validation_security.py::TestReplaceValidationAPISecurity::test_validate_rules_api_bom_handling",
            ])
        
        if test_type == "regex" or test_type == "all" or test_type is None:
            # 正则表达式测试
            test_files.extend([
                "tests/unit/test_replace_service_security.py::TestReplaceServiceSecurity::test_validate_rules_malicious_regex_catastrophic_backtracking",
                "tests/unit/test_replace_service_security.py::TestReplaceServiceSecurity::test_validate_rules_malicious_regex_redos_patterns",
                "tests/unit/test_replace_service_security.py::TestReplaceServiceSecurity::test_validate_rules_regex_timeout_protection",
                "tests/api/test_replace_validation_security.py::TestReplaceValidationAPISecurity::test_validate_rules_api_redos_protection",
                "tests/performance/test_replace_validation_performance.py::TestReplaceValidationPerformance::test_validation_regex_performance",
            ])
        
        # 如果没有指定类型或指定了all，添加现有的测试文件
        if test_type == "all" or test_type is None:
            test_files.extend([
                "tests/test_rule_validation.py",
                "tests/unit/test_replace_service.py",
            ])
        
        return test_files
    
    def generate_summary_report(self) -> None:
        """生成测试总结报告"""
        print("\n" + "=" * 80)
        print("BE-03任务测试总结")
        print("=" * 80)
        
        test_categories = {
            "安全性测试": [
                "恶意正则表达式防护",
                "Unicode安全问题检测",
                "注入攻击防护",
                "文件上传安全验证",
            ],
            "性能测试": [
                "大规模规则验证性能",
                "内存使用优化",
                "并发处理能力",
                "正则表达式性能",
            ],
            "集成测试": [
                "服务间集成",
                "文件系统集成",
                "错误恢复机制",
                "资源管理",
            ],
            "边界条件测试": [
                "超长规则文件处理",
                "循环引用检测",
                "编码错误处理",
                "特殊字符处理",
            ],
        }
        
        for category, tests in test_categories.items():
            print(f"\n{category}:")
            for test in tests:
                print(f"  ✓ {test}")
        
        print("\n测试覆盖的主要功能:")
        print("  • 规则文件验证API安全性")
        print("  • 恶意正则表达式检测与防护")
        print("  • Unicode字符安全处理")
        print("  • 循环引用和递归替换检测")
        print("  • 大文件和高并发处理")
        print("  • 内存泄漏和性能监控")
        print("  • 错误处理和异常恢复")
        
        print("\n" + "=" * 80)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="BE-03任务测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_be03_tests.py --all --verbose --coverage
  python run_be03_tests.py --security --html
  python run_be03_tests.py --performance
  python run_be03_tests.py --unicode --verbose
        """
    )
    
    # 测试类型选项
    test_group = parser.add_mutually_exclusive_group()
    test_group.add_argument("--security", action="store_const", const="security", dest="test_type",
                           help="只运行安全性测试")
    test_group.add_argument("--performance", action="store_const", const="performance", dest="test_type",
                           help="只运行性能测试")
    test_group.add_argument("--integration", action="store_const", const="integration", dest="test_type",
                           help="只运行集成测试")
    test_group.add_argument("--unicode", action="store_const", const="unicode", dest="test_type",
                           help="只运行Unicode相关测试")
    test_group.add_argument("--regex", action="store_const", const="regex", dest="test_type",
                           help="只运行正则表达式相关测试")
    test_group.add_argument("--all", action="store_const", const="all", dest="test_type",
                           help="运行所有BE-03测试（默认）")
    
    # 输出选项
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="详细输出")
    parser.add_argument("--coverage", action="store_true",
                       help="生成覆盖率报告")
    parser.add_argument("--html", action="store_true",
                       help="生成HTML测试报告")
    parser.add_argument("--summary", action="store_true",
                       help="显示测试总结")
    
    args = parser.parse_args()
    
    # 创建测试运行器
    runner = BE03TestRunner()
    
    # 显示测试总结
    if args.summary:
        runner.generate_summary_report()
        return 0
    
    # 运行测试
    exit_code = runner.run_tests(
        test_type=args.test_type,
        verbose=args.verbose,
        coverage=args.coverage,
        html_report=args.html
    )
    
    # 显示结果
    if exit_code == 0:
        print("\n✅ 所有测试通过！")
        if args.coverage:
            print("📊 覆盖率报告已生成")
        if args.html:
            print("📄 HTML报告已生成: reports/be03_test_report.html")
    else:
        print(f"\n❌ 测试失败，退出码: {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())