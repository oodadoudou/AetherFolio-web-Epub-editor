"""会话服务单元测试"""

import pytest
import pytest_asyncio
import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from backend.services.session_service import SessionService
from backend.models.session import Session
from backend.core.config import settings


class TestSessionService:
    """会话服务测试类"""
    
    @pytest_asyncio.fixture
    async def service(self):
        """创建测试用的会话服务实例"""
        service = SessionService()
        await service._initialize()
        yield service
        await service._cleanup()
    
    @pytest_asyncio.fixture
    async def service_with_redis(self):
        """创建带Redis的测试服务实例（已跳过）"""
        service = SessionService()
        await service._initialize()
        yield service, None
        await service._cleanup()
    
    @pytest.fixture
    def sample_metadata(self):
        """示例会话元数据"""
        return {
            'original_filename': 'test.epub',
            'file_size': 1024000,
            'upload_time': datetime.now().isoformat(),
            'file_type': 'epub',
            'user_agent': 'Test Agent'
        }
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """测试服务初始化"""
        assert service.service_name == "session"
        assert service.sessions == {}
        assert service.session_data == {}
        assert service._redis_client is None
        assert service._cleanup_task is not None
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_service_initialization_with_redis(self):
        """测试带Redis的服务初始化"""
        pass
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_service_initialization_redis_failure(self):
        """测试Redis连接失败的情况"""
        pass
    
    @pytest.mark.asyncio
    async def test_create_session_success(self, service, sample_metadata):
        """测试成功创建会话"""
        session_id = await service.create_session(sample_metadata)
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID长度
        assert session_id in service.sessions
        
        session = service.sessions[session_id]
        assert session.session_id == session_id
        assert session.original_filename == 'test.epub'
        assert session.metadata == sample_metadata
        assert session.upload_time <= datetime.now()
        assert session.expires_at > datetime.now()
    
    @pytest.mark.asyncio
    async def test_create_session_without_metadata(self, service):
        """测试不带元数据创建会话"""
        session_id = await service.create_session()
        
        assert session_id is not None
        assert session_id in service.sessions
        
        session = service.sessions[session_id]
        assert session.original_filename is None
        assert session.metadata == {}
    
    @pytest.mark.asyncio
    async def test_create_session_max_limit(self, service):
        """测试会话数量限制"""
        original_max = settings.max_sessions
        try:
            settings.max_sessions = 2
            
            # 创建最大数量的会话
            session_id1 = await service.create_session()
            session_id2 = await service.create_session()
            
            # 尝试创建超出限制的会话
            with pytest.raises(Exception, match="会话数量已达上限"):
                await service.create_session()
                
        finally:
            settings.max_sessions = original_max
    
    @pytest.mark.asyncio
    async def test_get_session_success(self, service, sample_metadata):
        """测试成功获取会话"""
        session_id = await service.create_session(sample_metadata)
        
        session = await service.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.original_filename == 'test.epub'
    
    @pytest.mark.asyncio
    async def test_get_session_not_found(self, service):
        """测试获取不存在的会话"""
        session = await service.get_session('a' * 32)  # 32字符的有效session ID
        assert session is None
    
    @pytest.mark.asyncio
    async def test_get_session_invalid_id(self, service):
        """测试获取无效ID的会话"""
        with pytest.raises(Exception):  # 应该抛出异常而不是返回None
            await service.get_session('')
    
    @pytest.mark.asyncio
    async def test_get_session_expired(self, service, sample_metadata):
        """测试获取过期会话"""
        session_id = await service.create_session(sample_metadata)
        
        # 手动设置会话为过期
        service.sessions[session_id].expires_at = datetime.now() - timedelta(seconds=1)
        
        session = await service.get_session(session_id)
        assert session is None
        assert session_id not in service.sessions
    
    @pytest.mark.asyncio
    async def test_update_session_success(self, service, sample_metadata):
        """测试成功更新会话"""
        session_id = await service.create_session(sample_metadata)
        
        new_metadata = {'new_key': 'new_value'}
        result = await service.update_session(session_id, new_metadata)
        
        assert result is True
        session = service.sessions[session_id]
        assert session.metadata['new_key'] == 'new_value'
        assert session.metadata['original_filename'] == 'test.epub'  # 原有数据保留
    
    @pytest.mark.asyncio
    async def test_update_session_not_found(self, service):
        """测试更新不存在的会话"""
        result = await service.update_session('a' * 32, {'key': 'value'})
        assert result is False
    
    @pytest.mark.asyncio
    async def test_extend_session_success(self, service, sample_metadata):
        """测试成功延长会话"""
        session_id = await service.create_session(sample_metadata)
        original_expires = service.sessions[session_id].expires_at
        
        result = await service.extend_session(session_id, 3600)  # 延长1小时
        
        assert result is True
        new_expires = service.sessions[session_id].expires_at
        assert new_expires > original_expires
    
    @pytest.mark.asyncio
    async def test_extend_session_default_time(self, service, sample_metadata):
        """测试使用默认时间延长会话"""
        session_id = await service.create_session(sample_metadata)
        original_expires = service.sessions[session_id].expires_at
        
        result = await service.extend_session(session_id)  # 使用默认延长时间
        
        assert result is True
        new_expires = service.sessions[session_id].expires_at
        assert new_expires > original_expires
    
    @pytest.mark.asyncio
    async def test_extend_session_not_found(self, service):
        """测试延长不存在的会话"""
        result = await service.extend_session('a' * 32)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_delete_session_success(self, service, sample_metadata):
        """测试成功删除会话"""
        session_id = await service.create_session(sample_metadata)
        await service.set_session_data(session_id, 'test_key', 'test_value')
        
        result = await service.delete_session(session_id)
        
        assert result is True
        assert session_id not in service.sessions
        assert session_id not in service.session_data
    
    @pytest.mark.asyncio
    async def test_delete_session_not_found(self, service):
        """测试删除不存在的会话"""
        result = await service.delete_session('non-existent-id')
        assert result is True  # 删除不存在的会话也返回True
    
    @pytest.mark.asyncio
    async def test_set_session_data_success(self, service, sample_metadata):
        """测试成功设置会话数据"""
        session_id = await service.create_session(sample_metadata)
        
        result = await service.set_session_data(session_id, 'test_key', 'test_value')
        
        assert result is True
        assert session_id in service.session_data
        assert service.session_data[session_id]["test_key"] == "test_value"
    
    @pytest.mark.asyncio
    async def test_set_session_data_complex_value(self, service, sample_metadata):
        """测试设置复杂数据类型"""
        session_id = await service.create_session(sample_metadata)
        complex_data = {'nested': {'key': 'value'}, 'list': [1, 2, 3]}
        
        result = await service.set_session_data(session_id, 'complex', complex_data)
        
        assert result is True
        assert service.session_data[session_id]["complex"] == complex_data
    
    @pytest.mark.asyncio
    async def test_set_session_data_session_not_found(self, service):
        """测试为不存在的会话设置数据"""
        result = await service.set_session_data('a' * 32, 'key', 'value')
        assert result is False
    
    @pytest.mark.asyncio
    async def test_get_session_data_success(self, service, sample_metadata):
        """测试成功获取会话数据"""
        session_id = await service.create_session(sample_metadata)
        await service.set_session_data(session_id, 'test_key', 'test_value')
        
        value = await service.get_session_data(session_id, 'test_key')
        
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_get_session_data_with_default(self, service, sample_metadata):
        """测试获取不存在的会话数据时返回默认值"""
        session_id = await service.create_session(sample_metadata)
        
        value = await service.get_session_data(session_id, 'non_existent_key', 'default')
        
        assert value == "default"
    
    @pytest.mark.asyncio
    async def test_get_session_data_session_not_found(self, service):
        """测试从不存在的会话获取数据"""
        value = await service.get_session_data('a' * 32, 'key', 'default')
        assert value == "default"
    
    @pytest.mark.asyncio
    async def test_delete_session_data_success(self, service, sample_metadata):
        """测试成功删除会话数据"""
        session_id = await service.create_session(sample_metadata)
        await service.set_session_data(session_id, 'test_key', 'test_value')
        
        result = await service.delete_session_data(session_id, 'test_key')
        
        assert result is True
        value = await service.get_session_data(session_id, 'test_key', 'not_found')
        assert value == "not_found"
    
    @pytest.mark.asyncio
    async def test_list_sessions_empty(self, service):
        """测试列出空会话列表"""
        sessions = await service.list_sessions()
        assert sessions == []
    
    @pytest.mark.asyncio
    async def test_list_sessions_with_active_sessions(self, service, sample_metadata):
        """测试列出活跃会话"""
        session_id1 = await service.create_session(sample_metadata)
        session_id2 = await service.create_session(sample_metadata)
        
        sessions = await service.list_sessions()
        
        assert len(sessions) == 2
        session_ids = [s.session_id for s in sessions]
        assert session_id1 in session_ids
        assert session_id2 in session_ids
    
    @pytest.mark.asyncio
    async def test_list_sessions_excludes_expired(self, service, sample_metadata):
        """测试列出会话时排除过期会话"""
        session_id1 = await service.create_session(sample_metadata)
        session_id2 = await service.create_session(sample_metadata)
        
        # 手动设置第一个会话为过期
        service.sessions[session_id1].expires_at = datetime.now() - timedelta(seconds=1)
        
        sessions = await service.list_sessions()
        
        assert len(sessions) == 1
        assert sessions[0].session_id == session_id2
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_sync(self, service, sample_metadata):
        """测试同步清理过期会话"""
        session_id1 = await service.create_session(sample_metadata)
        session_id2 = await service.create_session(sample_metadata)
        
        # 手动设置第一个会话为过期
        service.sessions[session_id1].expires_at = datetime.now() - timedelta(seconds=1)
        
        await service._cleanup_expired_sessions_sync()
        
        assert session_id1 not in service.sessions
        assert session_id2 in service.sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions_public_method(self, service, sample_metadata):
        """测试公共清理方法"""
        session_id1 = await service.create_session(sample_metadata)
        session_id2 = await service.create_session(sample_metadata)
        
        # 手动设置第一个会话为过期
        service.sessions[session_id1].expires_at = datetime.now() - timedelta(seconds=1)
        
        cleaned_count = await service.cleanup_expired_sessions()
        
        assert cleaned_count == 1
        assert session_id1 not in service.sessions
        assert session_id2 in service.sessions
    
    @pytest.mark.asyncio
    async def test_get_session_stats(self, service, sample_metadata):
        """测试获取会话统计信息"""
        # 创建一些会话
        await service.create_session(sample_metadata)
        await service.create_session(sample_metadata)
        
        stats = await service.get_session_stats()
        
        assert isinstance(stats, dict)
        assert 'active_sessions' in stats
        assert 'total_sessions' in stats
        assert 'expired_sessions' in stats
        assert 'max_sessions' in stats
        assert 'session_timeout' in stats
        assert 'cleanup_interval' in stats
        assert 'redis_enabled' in stats
        
        assert stats['active_sessions'] == 2
        assert stats['total_sessions'] == 2
        assert stats['expired_sessions'] == 0
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_redis_operations(self, service_with_redis, sample_metadata):
        """测试Redis操作"""
        pass
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_redis_load_session(self, service_with_redis):
        """测试从Redis加载会话"""
        pass
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_redis_load_session_invalid_data(self, service_with_redis):
        """测试从Redis加载无效会话数据"""
        pass
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_redis_get_session_data_from_redis(self, service_with_redis, sample_metadata):
        """测试从Redis获取会话数据"""
        pass
    
    @pytest.mark.skip(reason="Redis asyncio not available in test environment")
    async def test_redis_error_handling(self, service_with_redis, sample_metadata):
        """测试Redis错误处理"""
        pass
    
    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, service, sample_metadata):
        """测试并发会话操作"""
        async def create_and_use_session(index):
            session_id = await service.create_session(sample_metadata)
            await service.set_session_data(session_id, 'key', f'value{index}')
            value = await service.get_session_data(session_id, 'key')
            return session_id, value
        
        # 并发创建和使用多个会话
        tasks = [create_and_use_session(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # 验证所有操作都成功
        assert len(results) == 5
        for i, (session_id, value) in enumerate(results):
            assert session_id is not None
            assert value == f"value{i}"
    
    @pytest.mark.asyncio
    async def test_service_cleanup(self, service, sample_metadata):
        """测试服务清理"""
        # 创建一些会话和数据
        session_id = await service.create_session(sample_metadata)
        await service.set_session_data(session_id, 'key', 'value')
        
        # 验证数据存在
        assert len(service.sessions) > 0
        assert len(service.session_data) > 0
        
        # 手动清理过期会话
        cleaned_count = await service.cleanup_expired_sessions()
        
        # 验证清理功能正常工作（即使没有过期会话）
        assert cleaned_count >= 0
        assert len(service.sessions) > 0  # 会话未过期，应该仍然存在


class TestSessionIDUniqueness:
    """Session ID唯一性测试类 - BE-01任务Session ID测试"""
    
    @pytest_asyncio.fixture
    async def service(self):
        """创建测试用的会话服务实例"""
        service = SessionService()
        await service._initialize()
        yield service
        await service._cleanup()
    
    @pytest.mark.asyncio
    async def test_session_id_uniqueness_bulk_generation(self, service):
        """测试大量生成Session ID的唯一性"""
        session_ids = set()
        duplicate_count = 0
        total_sessions = 1000
        
        # 在极短时间内大量生成session ID
        for i in range(total_sessions):
            try:
                session_id = await service.create_session({
                    'test_index': i,
                    'timestamp': time.time()
                })
                
                if session_id in session_ids:
                    duplicate_count += 1
                else:
                    session_ids.add(session_id)
                    
            except Exception as e:
                # 如果达到会话限制，跳过
                if "会话数量已达上限" in str(e):
                    break
                raise
        
        # 验证没有重复的session ID
        assert duplicate_count == 0, f"发现 {duplicate_count} 个重复的session ID"
        
        # 验证所有生成的session ID都是有效的UUID4格式
        import uuid
        for session_id in session_ids:
            try:
                parsed_uuid = uuid.UUID(session_id, version=4)
                assert str(parsed_uuid) == session_id
            except ValueError:
                pytest.fail(f"Session ID {session_id} 不是有效的UUID4格式")
    
    @pytest.mark.asyncio
    async def test_session_id_collision_probability(self, service):
        """测试Session ID碰撞概率"""
        import uuid
        import hashlib
        
        # 生成多个session ID并分析其分布
        session_ids = []
        hash_prefixes = {}
        
        # 生成500个session ID（在测试环境中保持合理的数量）
        for i in range(500):
            try:
                session_id = await service.create_session({'index': i})
                session_ids.append(session_id)
                
                # 分析UUID的前8个字符的分布
                prefix = session_id[:8]
                hash_prefixes[prefix] = hash_prefixes.get(prefix, 0) + 1
                
            except Exception as e:
                if "会话数量已达上限" in str(e):
                    break
                raise
        
        # 验证没有重复的session ID
        unique_ids = set(session_ids)
        assert len(unique_ids) == len(session_ids), "发现重复的session ID"
        
        # 验证UUID前缀的分布相对均匀（大部分前缀应该只出现一次）
        max_prefix_count = max(hash_prefixes.values())
        assert max_prefix_count <= 3, f"UUID前缀分布不均匀，最大重复次数: {max_prefix_count}"
        
        # 验证UUID版本号都是4
        for session_id in session_ids:
            uuid_obj = uuid.UUID(session_id)
            assert uuid_obj.version == 4, f"Session ID {session_id} 不是UUID4"
    
    @pytest.mark.asyncio
    async def test_concurrent_session_id_generation(self, service):
        """测试并发生成Session ID的唯一性"""
        import asyncio
        
        async def create_session_batch(batch_index, batch_size=50):
            """创建一批会话"""
            session_ids = []
            for i in range(batch_size):
                try:
                    session_id = await service.create_session({
                        'batch': batch_index,
                        'index': i,
                        'timestamp': time.time()
                    })
                    session_ids.append(session_id)
                except Exception as e:
                    if "会话数量已达上限" in str(e):
                        break
                    raise
            return session_ids
        
        # 并发创建多批会话
        tasks = [create_session_batch(i) for i in range(10)]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 收集所有session ID
        all_session_ids = []
        for result in batch_results:
            if isinstance(result, Exception):
                pytest.fail(f"Batch creation failed: {result}")
            all_session_ids.extend(result)
        
        # 验证所有session ID都是唯一的
        unique_ids = set(all_session_ids)
        assert len(unique_ids) == len(all_session_ids), \
            f"并发生成的session ID中发现重复，总数: {len(all_session_ids)}, 唯一数: {len(unique_ids)}"
        
        # 验证每个session ID都是有效的UUID4
        import uuid
        for session_id in all_session_ids:
            uuid_obj = uuid.UUID(session_id)
            assert uuid_obj.version == 4
    
    @pytest.mark.asyncio
    async def test_session_id_entropy_analysis(self, service):
        """测试Session ID的熵值分析"""
        import uuid
        import collections
        
        session_ids = []
        
        # 生成一定数量的session ID
        for i in range(200):
            try:
                session_id = await service.create_session({'entropy_test': i})
                session_ids.append(session_id)
            except Exception as e:
                if "会话数量已达上限" in str(e):
                    break
                raise
        
        # 分析字符分布
        char_frequency = collections.Counter()
        for session_id in session_ids:
            # 移除连字符，只分析十六进制字符
            hex_chars = session_id.replace('-', '')
            char_frequency.update(hex_chars)
        
        # 验证字符分布相对均匀（每个十六进制字符都应该出现）
        expected_chars = set('0123456789abcdef')
        actual_chars = set(char_frequency.keys())
        assert expected_chars.issubset(actual_chars), \
            f"缺少十六进制字符: {expected_chars - actual_chars}"
        
        # 验证没有字符出现频率过高（简单的熵检查）
        total_chars = sum(char_frequency.values())
        for char, count in char_frequency.items():
            frequency = count / total_chars
            # 理论上每个字符应该出现约1/16的频率，允许一定偏差
            assert 0.03 <= frequency <= 0.12, \
                f"字符 '{char}' 出现频率异常: {frequency:.4f}"
    
    @pytest.mark.asyncio
    async def test_session_id_format_validation(self, service):
        """测试Session ID格式验证"""
        import re
        
        # UUID4格式的正则表达式
        uuid4_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            re.IGNORECASE
        )
        
        # 生成多个session ID并验证格式
        for i in range(100):
            try:
                session_id = await service.create_session({'format_test': i})
                
                # 验证UUID4格式
                assert uuid4_pattern.match(session_id), \
                    f"Session ID {session_id} 不符合UUID4格式"
                
                # 验证版本位（第13个字符应该是'4'）
                assert session_id[14] == '4', \
                    f"Session ID {session_id} 版本位不正确"
                
                # 验证变体位（第17个字符应该是8,9,a,b之一）
                variant_char = session_id[19].lower()
                assert variant_char in '89ab', \
                    f"Session ID {session_id} 变体位不正确: {variant_char}"
                    
            except Exception as e:
                if "会话数量已达上限" in str(e):
                    break
                raise