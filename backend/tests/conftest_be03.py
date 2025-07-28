import pytest
import pytest_asyncio
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Generator, AsyncGenerator

from backend.services.replace_service import ReplaceService
from backend.services.session_service import SessionService
from backend.models.session import Session
from backend.core.security import SecurityValidator


# BE-03任务测试配置和固件

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def replace_service() -> AsyncGenerator[ReplaceService, None]:
    """创建ReplaceService实例用于测试"""
    service = ReplaceService()
    await service._initialize()
    yield service
    await service.cleanup()


@pytest_asyncio.fixture(scope="function")
async def session_service() -> AsyncGenerator[SessionService, None]:
    """创建SessionService实例用于测试"""
    service = SessionService()
    await service._initialize()
    yield service
    await service.cleanup()


@pytest.fixture
def security_validator() -> SecurityValidator:
    """创建SecurityValidator实例用于测试"""
    return SecurityValidator()


@pytest.fixture
def temp_rules_directory() -> Generator[str, None, None]:
    """创建临时规则文件目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_malicious_rules() -> str:
    """恶意规则样本"""
    return """# 恶意规则测试样本
# ReDoS攻击模式
(a+)+b -> replacement | Catastrophic backtracking | regex
(x+x+)+y -> replacement | Exponential backtracking | regex
([a-zA-Z]+)*$ -> replacement | Nested quantifiers | regex

# 空替换（删除操作）
delete_this ->  | Empty replacement
remove_content -> | Another deletion

# 宽泛正则表达式
.* -> global_replacement | Too broad regex | regex
.+ -> another_global | Another broad regex | regex

# 结构性变更
<div> -> <span> | HTML structure change
<script> -> <!-- script --> | Script tag modification

# Unicode安全问题
\u200B -> \u200C | Zero-width space
\u202E -> \u202D | Direction override
а -> a | Cyrillic vs Latin homograph
"""


@pytest.fixture
def sample_large_rules() -> str:
    """大规模规则样本"""
    rules = []
    
    # 添加基本规则
    for i in range(1000):
        rules.append(f"pattern_{i} -> replacement_{i} | Basic rule {i}")
    
    # 添加正则表达式规则
    for i in range(100):
        rules.append(f"\\d{{1,3}}\\.{i} -> [NUMBER_{i}] | Regex rule {i} | regex")
    
    # 添加Unicode规则
    unicode_chars = ['你好', 'こんにちは', 'مرحبا', '🚀', '😀']
    for i, char in enumerate(unicode_chars * 20):
        rules.append(f"{char}_{i} -> replacement_{i} | Unicode rule {i}")
    
    return "\n".join(rules)


@pytest.fixture
def sample_circular_rules() -> str:
    """循环引用规则样本"""
    return """# 循环引用测试
# 简单循环
a -> b | Step 1
b -> c | Step 2
c -> a | Step 3 - creates cycle

# 复杂循环
start -> middle1 | Complex cycle start
middle1 -> middle2 | Complex cycle middle 1
middle2 -> middle3 | Complex cycle middle 2
middle3 -> start | Complex cycle end - creates cycle

# 自引用
self_ref -> self_ref_modified | Self reference
exact_self -> exact_self | Exact self reference

# 独立规则（不参与循环）
independent -> result | Independent rule
other -> final | Another independent rule
"""


@pytest.fixture
def sample_unicode_rules() -> str:
    """Unicode字符规则样本"""
    return """# Unicode字符测试
# 中文字符
你好 -> 再见 | Chinese greeting
世界 -> 宇宙 | Chinese world

# 日文字符
こんにちは -> さようなら | Japanese greeting
世界 -> 宇宙 | Japanese world

# 阿拉伯文字符
مرحبا -> وداعا | Arabic greeting
عالم -> كون | Arabic world

# 表情符号
😀 -> 😢 | Happy to sad
🚀 -> ✈️ | Rocket to plane
❤️ -> 💔 | Heart to broken heart

# 特殊Unicode字符
\u200B -> \u200C | Zero-width space to zero-width non-joiner
\u202E -> \u202D | Right-to-left override to left-to-right override
\uFEFF -> \u0020 | BOM to space

# 组合字符
é -> e | Accented e to normal e
ñ -> n | Spanish n to normal n
ü -> u | Umlaut u to normal u

# 同形异义字符（安全测试）
а -> a | Cyrillic a to Latin a
о -> o | Cyrillic o to Latin o
р -> p | Cyrillic p to Latin p
"""


@pytest.fixture
def sample_performance_rules() -> str:
    """性能测试规则样本"""
    rules = []
    
    # 复杂正则表达式
    complex_patterns = [
        r"\d{4}-\d{2}-\d{2}",  # 日期
        r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # 邮箱
        r"https?://[\w\.-]+\.[a-zA-Z]{2,}[\w\.-]*/?[\w\.-]*\??[\w=&\.-]*",  # URL
        r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",  # IP地址
        r"\b[A-Z]{2,}\b",  # 缩写词
        r"\$\d+\.\d{2}",  # 货币
        r"\b\d{3}-\d{3}-\d{4}\b",  # 电话号码
        r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b",  # 姓名
    ]
    
    # 为每个复杂模式创建多个规则
    for i, pattern in enumerate(complex_patterns):
        for j in range(50):  # 每个模式50个变体
            rules.append(f"{pattern}_{j} -> [PATTERN_{i}_{j}] | Complex pattern {i}-{j} | regex")
    
    # 添加长文本规则
    for i in range(100):
        long_pattern = "word" * 50 + f"_{i}"
        long_replacement = "replacement" * 20 + f"_{i}"
        rules.append(f"{long_pattern} -> {long_replacement} | Long text rule {i}")
    
    return "\n".join(rules)


@pytest.fixture
def sample_edge_case_rules() -> str:
    """边界条件规则样本"""
    return """# 边界条件测试
# 空搜索文本（应该无效）
 -> replacement | Empty search

# 空替换文本
delete_me ->  | Empty replacement

# 只有空格的搜索文本
   -> replacement | Whitespace only search

# 只有空格的替换文本
test ->    | Whitespace only replacement

# 特殊字符
\t -> [TAB] | Tab character
\n -> [NEWLINE] | Newline character
\r -> [CARRIAGE_RETURN] | Carriage return

# 控制字符
\x00 -> [NULL] | Null character
\x1f -> [UNIT_SEPARATOR] | Unit separator
\x7f -> [DELETE] | Delete character

# 极长的规则
""" + "x" * 1000 + " -> " + "y" * 1000 + " | Very long rule\n" + """

# 包含箭头的文本
text->with->arrows -> replacement | Text with arrows
real -> arrow -> here -> final | Multiple arrows

# 包含管道符的文本
text|with|pipes -> replacement | Text with pipes
real | pipe | here -> final | Spaced pipes

# 正则表达式特殊字符
.*+?^${}[]()| -> [REGEX_CHARS] | Regex special characters

# 引号和转义
"quoted text" -> 'single quoted' | Quote handling
\"escaped quotes\" -> normal_text | Escaped quotes
"""


# 测试标记定义
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.be03,  # BE-03任务标记
]


# 测试配置
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line(
        "markers", "be03: BE-03任务（规则文件验证）相关测试"
    )
    config.addinivalue_line(
        "markers", "security: 安全性测试"
    )
    config.addinivalue_line(
        "markers", "performance: 性能测试"
    )
    config.addinivalue_line(
        "markers", "integration: 集成测试"
    )
    config.addinivalue_line(
        "markers", "unicode: Unicode字符处理测试"
    )
    config.addinivalue_line(
        "markers", "regex: 正则表达式相关测试"
    )


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 为BE-03相关测试添加标记
    be03_keywords = [
        "validation", "security", "regex", "unicode", 
        "circular", "redos", "malicious", "performance"
    ]
    
    for item in items:
        # 检查测试名称是否包含BE-03相关关键词
        if any(keyword in item.name.lower() for keyword in be03_keywords):
            item.add_marker(pytest.mark.be03)
        
        # 为安全测试添加标记
        if any(keyword in item.name.lower() for keyword in ["security", "malicious", "redos"]):
            item.add_marker(pytest.mark.security)
        
        # 为性能测试添加标记
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        
        # 为集成测试添加标记
        if "integration" in item.name.lower():
            item.add_marker(pytest.mark.integration)
        
        # 为Unicode测试添加标记
        if "unicode" in item.name.lower():
            item.add_marker(pytest.mark.unicode)
        
        # 为正则表达式测试添加标记
        if any(keyword in item.name.lower() for keyword in ["regex", "redos"]):
            item.add_marker(pytest.mark.regex)