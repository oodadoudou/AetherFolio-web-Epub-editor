# AetherFolio 后端测试设计报告

## 1. 测试概述

### 1.1 测试目标
- 验证所有API端点的功能正确性
- 确保服务层逻辑的可靠性
- 验证数据模型和验证规则
- 测试错误处理和边界条件
- 验证性能和并发处理能力
- 确保安全性和数据完整性

### 1.2 测试范围
- **API层测试**: 所有REST API端点
- **服务层测试**: 业务逻辑和数据处理
- **工具类测试**: 安全验证、日志记录等
- **集成测试**: 端到端功能验证
- **性能测试**: 负载和压力测试

### 1.3 测试分类
- **单元测试** (`tests/unit/`): 测试单个函数或类
- **集成测试** (`tests/integration/`): 测试组件间交互
- **API测试** (`tests/api/`): 测试HTTP接口
- **性能测试** (`tests/performance/`): 测试性能指标

## 2. 测试架构

### 2.1 目录结构
```
tests/
├── __init__.py                 # 测试包初始化
├── conftest.py                 # pytest配置和fixtures
├── TEST_DESIGN_REPORT.md       # 本文档
├── data/                       # 测试数据
│   ├── __init__.py
│   ├── generators.py           # 测试数据生成器
│   ├── sample_files/           # 示例文件
│   └── fixtures/               # 测试固件
├── unit/                       # 单元测试
│   ├── __init__.py
│   ├── test_models.py          # 数据模型测试
│   ├── test_security.py        # 安全模块测试
│   ├── test_config.py          # 配置模块测试
│   ├── test_logging.py         # 日志模块测试
│   └── services/               # 服务层测试
│       ├── test_epub_service.py
│       ├── test_session_service.py
│       ├── test_replace_service.py
│       └── test_preview_service.py
├── integration/                # 集成测试
│   ├── __init__.py
│   ├── test_file_operations.py # 文件操作集成测试
│   ├── test_batch_replace.py   # 批量替换集成测试
│   └── test_session_lifecycle.py # 会话生命周期测试
├── api/                        # API测试
│   ├── __init__.py
│   ├── test_upload_api.py      # 上传API测试
│   ├── test_files_api.py       # 文件API测试
│   ├── test_replace_api.py     # 替换API测试
│   └── test_sessions_api.py    # 会话API测试
└── performance/                # 性能测试
    ├── __init__.py
    ├── test_load.py            # 负载测试
    └── test_stress.py          # 压力测试
```

### 2.2 测试工具和框架
- **pytest**: 主要测试框架
- **pytest-asyncio**: 异步测试支持
- **httpx**: HTTP客户端测试
- **pytest-mock**: Mock和Patch支持
- **pytest-cov**: 代码覆盖率
- **pytest-benchmark**: 性能基准测试
- **factory-boy**: 测试数据工厂

## 3. 详细测试计划

### 3.1 单元测试 (Unit Tests)

#### 3.1.1 数据模型测试 (`test_models.py`)
- **测试目标**: 验证Pydantic模型的验证规则
- **测试内容**:
  - 模型字段验证
  - 数据类型转换
  - 自定义验证器
  - 序列化/反序列化
- **测试用例**:
  - 有效数据验证
  - 无效数据拒绝
  - 边界值测试
  - 默认值处理

#### 3.1.2 安全模块测试 (`test_security.py`)
- **测试目标**: 验证安全验证功能
- **测试内容**:
  - 文件路径验证
  - MIME类型检查
  - 文件大小限制
  - 文件名安全性
  - 哈希计算
- **测试用例**:
  - 路径遍历攻击防护
  - 恶意文件类型检测
  - 文件大小超限处理
  - 特殊字符文件名处理

#### 3.1.3 配置模块测试 (`test_config.py`)
- **测试目标**: 验证配置加载和验证
- **测试内容**:
  - 环境变量加载
  - 配置验证
  - 默认值设置
  - 目录创建
- **测试用例**:
  - 完整配置加载
  - 部分配置缺失
  - 无效配置值
  - 目录权限问题

#### 3.1.4 服务层测试

##### EPUB服务测试 (`test_epub_service.py`)
- **测试目标**: 验证EPUB文件处理功能
- **测试内容**:
  - EPUB文件解压
  - 元数据提取
  - 文件树生成
  - 内容读取/保存
  - 文件导出
- **测试用例**:
  - 标准EPUB文件处理
  - 损坏EPUB文件处理
  - 大文件处理
  - 特殊字符文件名
  - 并发访问

##### 会话服务测试 (`test_session_service.py`)
- **测试目标**: 验证会话管理功能
- **测试内容**:
  - 会话创建/删除
  - 会话数据存储
  - 过期处理
  - 并发访问
- **测试用例**:
  - 正常会话生命周期
  - 会话过期清理
  - 并发会话操作
  - 内存/Redis存储切换

##### 替换服务测试 (`test_replace_service.py`)
- **测试目标**: 验证批量替换功能
- **测试内容**:
  - 规则解析
  - 文本替换
  - 进度跟踪
  - 结果报告
- **测试用例**:
  - 简单文本替换
  - 正则表达式替换
  - 大文件批量替换
  - 无效规则处理
  - 替换进度监控

##### 预览服务测试 (`test_preview_service.py`)
- **测试目标**: 验证文件预览功能
- **测试内容**:
  - HTML预览生成
  - 样式处理
  - 链接转换
  - 缓存机制
- **测试用例**:
  - 各种文件类型预览
  - 相对路径处理
  - 缓存命中/未命中
  - 预览模板渲染

##### 文件服务测试 (`test_file_service.py`)
- **测试目标**: 验证通用文件操作功能
- **测试内容**:
  - 文件读取/写入操作
  - 文件删除和移动
  - 文件信息获取
  - 路径验证和安全检查
  - 文件锁定和并发控制
- **测试用例**:
  - 各种文件类型处理（HTML, XHTML, CSS, JS, 图片）
  - 文件权限和访问控制测试
  - 路径遍历攻击防护
  - 并发文件操作和锁定机制
  - 大文件处理性能

##### 搜索替换服务测试 (`test_search_replace_service.py`)
- **测试目标**: 验证搜索替换核心功能
- **测试内容**:
  - 文本搜索算法
  - 文本替换操作
  - 正则表达式处理
  - 批量替换执行
  - 进度跟踪和报告
- **测试用例**:
  - 简单文本搜索和替换
  - 正则表达式搜索替换
  - 大小写敏感/不敏感匹配
  - 全词匹配模式
  - 批量操作性能基准
  - 替换进度实时监控

##### 报告服务测试 (`test_report_service.py`)
- **测试目标**: 验证批量替换报告功能
- **测试内容**:
  - 替换结果统计和汇总
  - HTML报告生成
  - 报告数据格式化
  - 报告模板渲染
  - 报告文件保存和访问
- **测试用例**:
  - 简单替换操作报告
  - 复杂正则替换报告
  - 大量文件批量替换统计
  - 报告HTML格式验证
  - 报告数据导出功能

### 3.2 集成测试 (Integration Tests)

#### 3.2.1 文件操作集成测试 (`test_file_operations.py`)
- **测试目标**: 验证完整的文件操作流程
- **测试场景**:
  - 上传 → 解压 → 编辑 → 保存 → 导出
  - 多文件并发操作
  - 大文件处理流程
  - 错误恢复机制

#### 3.2.2 批量替换集成测试 (`test_batch_replace.py`)
- **测试目标**: 验证端到端批量替换流程
- **测试场景**:
  - 规则上传 → 验证 → 执行 → 进度监控 → 结果报告
  - 复杂替换规则处理
  - 大量文件批量处理
  - 替换任务取消

#### 3.2.3 会话生命周期测试 (`test_session_lifecycle.py`)
- **测试目标**: 验证完整的会话管理流程
- **测试场景**:
  - 会话创建 → 使用 → 延期 → 清理
  - 多用户并发会话
  - 会话数据一致性
  - 异常情况恢复

### 3.3 API测试 (API Tests)

#### 3.3.1 上传API测试 (`test_upload_api.py`)
- **测试端点**:
  - `POST /api/v1/upload/epub`
  - `GET /api/v1/upload/rules-template`
  - `POST /api/v1/upload/validate-rules`
- **测试场景**:
  - 正常文件上传
  - 文件类型验证
  - 文件大小限制
  - 并发上传
  - 错误响应格式
  - 速率限制测试
  - 大文件上传处理

#### 3.3.2 文件API测试 (`test_files_api.py`)
- **测试端点**:
  - `GET /api/v1/files/content`
  - `POST /api/v1/files/save`
  - `GET /api/v1/files/tree`
  - `POST /api/v1/files/export`
  - `GET /api/v1/files/preview/{session_id}/{file_path}`
  - `DELETE /api/v1/files/cache/{session_id}`
- **测试场景**:
  - 文件内容读取
  - 文件保存
  - 文件树获取
  - 文件导出
  - 预览生成
  - 缓存清理
  - 速率限制测试
  - 文件路径安全验证
  - 大文件处理
  - 并发文件操作

#### 3.3.3 替换API测试 (`test_replace_api.py`)
- **测试端点**:
  - `POST /api/v1/batch-replace/execute`
  - `GET /api/v1/batch-replace/progress/{session_id}`
  - `GET /api/v1/batch-replace/report/{session_id}`
  - `POST /api/v1/batch-replace/`
  - `DELETE /api/v1/batch-replace/{session_id}`
- **测试场景**:
  - 批量替换执行
  - 进度监控(SSE)
  - 结果报告
  - 任务取消

#### 3.3.4 会话API测试 (`test_sessions_api.py`)
- **测试端点**:
  - `GET /api/v1/sessions/{session_id}`
  - `PUT /api/v1/sessions/{session_id}/extend`
  - `DELETE /api/v1/sessions/{session_id}`
  - `GET /api/v1/sessions/`
  - `POST /api/v1/sessions/cleanup`
  - `GET /api/v1/sessions/{session_id}/stats`
  - `GET /api/v1/sessions/health`
- **测试场景**:
  - 会话信息获取
  - 会话延期
  - 会话删除
  - 会话列表
  - 批量清理
  - 统计信息
  - 健康检查
  - 速率限制测试
  - 会话过期处理
  - 并发会话管理

#### 3.3.5 搜索替换API测试 (`test_search_replace_api.py`)
- **测试端点**:
  - `POST /api/v1/search-replace/{session_id}/search`
  - `POST /api/v1/search-replace/{session_id}/replace`
- **测试场景**:
  - 文本搜索功能
  - 正则表达式搜索
  - 大小写敏感搜索
  - 全词匹配搜索
  - 文本替换功能
  - 批量替换操作
  - 搜索结果分页
  - 错误处理

### 3.4 性能测试 (Performance Tests)

#### 3.4.1 负载测试 (`test_load.py`)
- **测试目标**: 验证系统在正常负载下的性能表现
- **测试指标**:
  - API响应时间 < 200ms (95%)
  - 文件上传速度 < 5s (100MB文件)
  - 批量替换速度 < 30s (1000个文件)
  - 并发处理能力 100个并发请求
  - 内存使用率 < 80%
  - CPU使用率 < 70%
- **测试场景**:
  - 并发EPUB文件上传和处理
  - 并发批量替换操作
  - 高频API调用压力测试
  - 多用户同时编辑不同文件
  - 长时间会话保持测试

#### 3.4.2 压力测试 (`test_stress.py`)
- **测试目标**: 验证系统在极限条件下的稳定性和恢复能力
- **测试场景**:
  - 超大EPUB文件处理（>500MB）
  - 极高并发访问（>200并发用户）
  - 内存泄漏检测和长时间运行
  - 磁盘空间不足情况处理
  - 网络中断恢复测试
  - 系统资源耗尽恢复测试

#### 3.4.3 基准测试 (`test_benchmark.py`)
- **测试目标**: 建立性能基准和回归检测
- **测试内容**:
  - 核心算法性能基准
  - 数据库操作性能
  - 文件I/O操作性能
  - 内存使用模式分析
- **测试用例**:
  - 文本搜索算法基准
  - 正则表达式处理基准
  - 文件解压缩性能
  - 并发锁定机制性能

## 4. 测试数据管理

### 4.1 测试数据生成
- **EPUB文件**: 使用`EPUBGenerator`生成各种复杂度的测试文件
- **规则文件**: 使用`RulesGenerator`生成各种类型的替换规则
- **会话数据**: 使用`SessionDataGenerator`生成测试会话
- **文件内容**: 使用`FileContentGenerator`生成各种格式的文件内容

### 4.2 测试环境隔离
- 每个测试使用独立的临时目录
- 测试数据自动清理
- 数据库/缓存隔离
- 配置环境隔离

## 5. 测试执行策略

### 5.1 测试分组
- **快速测试**: 单元测试和简单集成测试
- **完整测试**: 包含所有测试类型
- **性能测试**: 单独执行的性能基准测试
- **回归测试**: 针对特定功能的回归验证

### 5.2 持续集成
- 代码提交时自动运行快速测试
- 每日运行完整测试套件
- 定期运行性能测试
- 测试结果报告和通知

### 5.3 测试命令
```bash
# 快速测试（单元测试，用于开发时快速验证）
pytest tests/unit/ -v --tb=short

# API测试（验证所有API端点）
pytest tests/api/ -v --tb=short

# 集成测试（验证组件间交互）
pytest tests/integration/ -v --tb=short

# 性能测试（标记为slow，单独执行）
pytest tests/performance/ -m slow -v --tb=short

# 完整测试套件（包含覆盖率报告）
pytest --cov=backend --cov-report=html --cov-report=term-missing --cov-fail-under=90

# 并行测试执行（提高测试速度）
pytest -n auto tests/ --dist=loadfile

# 特定标记的测试
pytest -m "not slow"  # 排除慢测试
pytest -m integration  # 只运行集成测试
pytest -m api         # 只运行API测试
pytest -m unit        # 只运行单元测试

# 测试特定服务
pytest tests/unit/test_epub_service.py -v
pytest tests/api/test_upload_api.py -v

# 生成详细的测试报告
pytest --html=reports/test_report.html --self-contained-html

# 测试覆盖率分析
pytest --cov=backend --cov-report=html:htmlcov --cov-report=xml:coverage.xml

# 性能基准测试
pytest tests/performance/test_benchmark.py --benchmark-only --benchmark-sort=mean
```

## 6. 质量指标

### 6.1 代码覆盖率目标
- **总体覆盖率**: ≥ 90%
- **API层覆盖率**: ≥ 95%
- **服务层覆盖率**: ≥ 90%
- **工具类覆盖率**: ≥ 85%

### 6.2 性能指标
- **API响应时间**: < 200ms (95%)
- **文件上传**: < 5s (100MB文件)
- **批量替换**: < 30s (1000个文件)
- **并发处理**: 支持100个并发请求

### 6.3 可靠性指标
- **测试通过率**: ≥ 99%
- **错误处理覆盖**: 100%
- **边界条件测试**: 100%
- **安全测试覆盖**: 100%

## 7. 风险和缓解策略

### 7.1 测试风险
- **测试数据污染**: 使用隔离的测试环境
- **测试依赖性**: 确保测试独立性
- **性能测试影响**: 在专用环境运行
- **测试维护成本**: 自动化测试数据生成

### 7.2 缓解策略
- 完善的测试隔离机制
- 自动化测试数据管理
- 持续的测试代码重构
- 定期的测试策略评估

## 8. 测试报告

### 8.1 测试结果报告
- 测试执行摘要
- 覆盖率报告
- 性能基准报告
- 失败测试详情

### 8.2 质量报告
- 代码质量指标
- 安全漏洞扫描
- 依赖项安全检查
- 最佳实践合规性

## 9. 实施计划和时间安排

### 9.1 第一阶段：基础测试完善（1-2周）
**目标**: 补充缺失的单元测试和API测试
**任务清单**:
1. **单元测试补充**:
   - 实现 `test_epub_service.py`（EPUB处理核心功能）
   - 实现 `test_file_service.py`（文件操作功能）
   - 实现 `test_preview_service.py`（预览生成功能）
   - 实现 `test_report_service.py`（报告生成功能）
   - 实现 `test_search_replace_service.py`（搜索替换功能）

2. **API测试增强**:
   - 完善 `test_files_api.py`（添加大文件和并发测试）
   - 完善 `test_replace_api.py`（添加SSE和错误处理测试）
   - 完善 `test_sessions_api.py`（添加会话管理测试）
   - 新增 `test_endpoints_*.py`（覆盖endpoints目录下的API）

3. **测试基础设施**:
   - 扩展测试数据生成器
   - 完善测试环境隔离
   - 配置测试标记和分类

### 9.2 第二阶段：集成测试和性能测试（2-3周）
**目标**: 建立完整的集成测试和性能测试框架
**任务清单**:
1. **集成测试实现**:
   - 实现 `test_full_workflow.py`（端到端工作流程）
   - 实现 `test_file_operations.py`（文件操作集成）
   - 实现 `test_batch_replace.py`（批量替换集成）
   - 实现 `test_session_lifecycle.py`（会话生命周期）

2. **性能测试框架**:
   - 实现 `test_load.py`（负载测试）
   - 实现 `test_stress.py`（压力测试）
   - 实现 `test_benchmark.py`（基准测试）
   - 配置性能监控和报告

3. **持续集成配置**:
   - 配置GitHub Actions工作流
   - 设置测试覆盖率报告
   - 配置性能回归检测

### 9.3 第三阶段：优化和维护（1周）
**目标**: 优化测试执行效率和建立维护机制
**任务清单**:
1. **测试优化**:
   - 并行测试执行配置
   - 测试缓存和增量执行
   - 测试数据管理优化
   - 测试报告美化

2. **质量保证**:
   - 测试代码质量检查
   - 测试覆盖率分析和改进
   - 测试文档完善
   - 测试最佳实践文档

3. **维护机制**:
   - 测试失败自动通知
   - 定期测试健康检查
   - 测试数据定期清理
   - 测试环境监控

### 9.4 长期维护计划
**持续改进目标**:
1. **自动化程度提升**:
   - 测试用例自动生成
   - 智能测试选择
   - 自动化回归测试
   - 测试结果智能分析

2. **测试效率优化**:
   - 测试执行时间优化
   - 资源使用优化
   - 测试环境标准化
   - 测试工具链升级

3. **质量监控增强**:
   - 实时质量仪表板
   - 趋势分析和预警
   - 性能基准跟踪
   - 安全测试集成

### 9.5 成功指标
**阶段性目标**:
- **第一阶段结束**: 单元测试覆盖率达到85%，API测试覆盖率达到90%
- **第二阶段结束**: 总体测试覆盖率达到90%，性能测试框架完整
- **第三阶段结束**: 测试执行时间优化50%，CI/CD流水线稳定运行

**最终目标**:
- 总体代码覆盖率 ≥ 90%
- API测试覆盖率 ≥ 95%
- 测试执行时间 < 10分钟（完整套件）
- 测试通过率 ≥ 99%
- 性能回归检测准确率 ≥ 95%

---

**文档版本**: 1.0  
**创建日期**: 2024年1月  
**最后更新**: 2024年1月  
**维护者**: AetherFolio开发团队