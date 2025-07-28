# Search Replace Service
# Handles search and replace operations

import re
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from backend.services.base import BaseService


class SearchReplaceService(BaseService):
    """Service for handling search and replace operations"""
    
    def __init__(self):
        super().__init__("search_replace")
    
    async def _initialize(self):
        """初始化搜索替换服务"""
        await super()._initialize()
        self.log_info("Search replace service initialized")
    
    async def search_in_file(self, file_path: str, query: str, options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for text in a single file"""
        async with self.performance_context("search_in_file"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                results = []
                
                # Read file content
                try:
                    with open(file_path_obj, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                except UnicodeDecodeError:
                    # Try other encodings
                    encodings = ['gbk', 'gb2312', 'latin1']
                    for encoding in encodings:
                        try:
                            with open(file_path_obj, 'r', encoding=encoding) as f:
                                lines = f.readlines()
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise ValueError(f"Cannot decode file: {file_path}")
                
                # Prepare search pattern
                if options.get('use_regex', False):
                    flags = 0 if options.get('case_sensitive', True) else re.IGNORECASE
                    pattern = re.compile(query, flags)
                else:
                    if options.get('whole_word', False):
                        query_pattern = r'\b' + re.escape(query) + r'\b'
                    else:
                        query_pattern = re.escape(query)
                    
                    flags = 0 if options.get('case_sensitive', True) else re.IGNORECASE
                    pattern = re.compile(query_pattern, flags)
                
                # Search in each line
                for line_num, line in enumerate(lines, 1):
                    line_content = line.rstrip('\n\r')
                    matches = pattern.finditer(line_content)
                    
                    for match in matches:
                        results.append({
                            "line_number": line_num,
                            "content": line_content,
                            "match_start": match.start(),
                            "match_end": match.end(),
                            "matched_text": match.group()
                        })
                
                self.log_info(f"Search completed in file: {file_path}", 
                            matches_found=len(results))
                return results
                
            except Exception as e:
                self.log_error(f"Failed to search in file: {file_path}", e)
                raise
    
    async def search_in_files(self, dir_path: str, query: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Search for text in multiple files"""
        async with self.performance_context("search_in_files"):
            try:
                dir_path_obj = Path(dir_path)
                if not dir_path_obj.exists():
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                
                # Get file extensions to search
                extensions = self._get_file_extensions(options)
                
                # Find all files to search
                files_to_search = []
                for ext in extensions:
                    files_to_search.extend(dir_path_obj.rglob(f"*{ext}"))
                
                # Remove duplicates and sort
                files_to_search = sorted(set(files_to_search))
                
                results = {
                    "total_matches": 0,
                    "files_with_matches": 0,
                    "results": {},
                    "searched_files": len(files_to_search)
                }
                
                # Search in each file
                for file_path in files_to_search:
                    try:
                        file_results = await self.search_in_file(str(file_path), query, options)
                        if file_results:
                            results["results"][str(file_path)] = file_results
                            results["total_matches"] += len(file_results)
                            results["files_with_matches"] += 1
                    except Exception as e:
                        self.log_error(f"Error searching in file: {file_path}", e)
                        continue
                
                self.log_info(f"Search completed in directory: {dir_path}", 
                            total_matches=results["total_matches"],
                            files_with_matches=results["files_with_matches"])
                return results
                
            except Exception as e:
                self.log_error(f"Failed to search in files: {dir_path}", e)
                raise
    
    async def replace_in_file(self, file_path: str, search: str, replace: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Replace text in a single file"""
        async with self.performance_context("replace_in_file"):
            try:
                file_path_obj = Path(file_path)
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"File not found: {file_path}")
                
                # Read original content
                encoding = 'utf-8'
                try:
                    with open(file_path_obj, 'r', encoding=encoding) as f:
                        original_content = f.read()
                except UnicodeDecodeError:
                    # Try other encodings
                    encodings = ['gbk', 'gb2312', 'latin1']
                    for enc in encodings:
                        try:
                            with open(file_path_obj, 'r', encoding=enc) as f:
                                original_content = f.read()
                            encoding = enc
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        raise ValueError(f"Cannot decode file: {file_path}")
                
                # Prepare replacement pattern
                if options.get('use_regex', False):
                    flags = 0 if options.get('case_sensitive', True) else re.IGNORECASE
                    pattern = re.compile(search, flags)
                    new_content = pattern.sub(replace, original_content)
                    replacements_count = len(pattern.findall(original_content))
                else:
                    if options.get('whole_word', False):
                        search_pattern = r'\b' + re.escape(search) + r'\b'
                    else:
                        search_pattern = re.escape(search)
                    
                    flags = 0 if options.get('case_sensitive', True) else re.IGNORECASE
                    pattern = re.compile(search_pattern, flags)
                    new_content = pattern.sub(replace, original_content)
                    replacements_count = len(pattern.findall(original_content))
                
                # Write back to file if there were changes
                if new_content != original_content:
                    with open(file_path_obj, 'w', encoding=encoding) as f:
                        f.write(new_content)
                
                result = {
                    "file_path": str(file_path),
                    "replacements_count": replacements_count,
                    "original_size": len(original_content),
                    "new_size": len(new_content),
                    "encoding": encoding
                }
                
                self.log_info(f"Replace completed in file: {file_path}", 
                            replacements_count=replacements_count)
                return result
                
            except Exception as e:
                self.log_error(f"Failed to replace in file: {file_path}", e)
                raise
    
    async def replace_in_files(self, dir_path: str, search: str, replace: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """Replace text in multiple files"""
        async with self.performance_context("replace_in_files"):
            try:
                dir_path_obj = Path(dir_path)
                if not dir_path_obj.exists():
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                
                # Get file extensions to process
                extensions = self._get_file_extensions(options)
                
                # Find all files to process
                files_to_process = []
                for ext in extensions:
                    files_to_process.extend(dir_path_obj.rglob(f"*{ext}"))
                
                # Remove duplicates and sort
                files_to_process = sorted(set(files_to_process))
                
                results = {
                    "total_replacements": 0,
                    "files_modified": 0,
                    "results": {},
                    "processed_files": len(files_to_process)
                }
                
                # Process each file
                for file_path in files_to_process:
                    try:
                        file_result = await self.replace_in_file(str(file_path), search, replace, options)
                        if file_result["replacements_count"] > 0:
                            results["results"][str(file_path)] = file_result
                            results["total_replacements"] += file_result["replacements_count"]
                            results["files_modified"] += 1
                    except Exception as e:
                        self.log_error(f"Error replacing in file: {file_path}", e)
                        continue
                
                self.log_info(f"Replace completed in directory: {dir_path}", 
                            total_replacements=results["total_replacements"],
                            files_modified=results["files_modified"])
                return results
                
            except Exception as e:
                self.log_error(f"Failed to replace in files: {dir_path}", e)
                raise
    
    async def batch_replace(self, dir_path: str, rules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Perform batch replace operations"""
        async with self.performance_context("batch_replace"):
            try:
                results = {
                    "total_replacements": 0,
                    "files_modified": 0,
                    "rules_applied": 0,
                    "results_by_rule": []
                }
                
                for i, rule in enumerate(rules):
                    try:
                        search = rule.get('search', '')
                        replace = rule.get('replace', '')
                        options = {
                            'case_sensitive': rule.get('case_sensitive', True),
                            'use_regex': rule.get('use_regex', False),
                            'whole_word': rule.get('whole_word', False),
                            'file_extensions': rule.get('file_extensions', ['.txt', '.html', '.md'])
                        }
                        
                        rule_result = await self.replace_in_files(dir_path, search, replace, options)
                        
                        results["results_by_rule"].append({
                            "rule_index": i,
                            "search": search,
                            "replace": replace,
                            "result": rule_result
                        })
                        
                        results["total_replacements"] += rule_result["total_replacements"]
                        results["files_modified"] = max(results["files_modified"], rule_result["files_modified"])
                        results["rules_applied"] += 1
                        
                    except Exception as e:
                        self.log_error(f"Error applying rule {i}: {rule}", e)
                        continue
                
                self.log_info(f"Batch replace completed in directory: {dir_path}", 
                            rules_applied=results["rules_applied"],
                            total_replacements=results["total_replacements"])
                return results
                
            except Exception as e:
                self.log_error(f"Failed to perform batch replace: {dir_path}", e)
                raise
    
    def _compile_regex(self, pattern: str, flags: int = 0) -> re.Pattern:
        """Compile regex pattern"""
        try:
            return re.compile(pattern, flags)
        except re.error as e:
            self.log_error(f"Invalid regex pattern: {pattern}", e)
            raise ValueError(f"Invalid regex pattern: {pattern}")
    
    def _get_file_extensions(self, options: Dict[str, Any]) -> List[str]:
        """Get file extensions to search"""
        extensions = options.get('file_extensions', ['.txt', '.html', '.md', '.py', '.js', '.css'])
        if not isinstance(extensions, list):
            extensions = ['.txt', '.html', '.md']
        return extensions
    
    def validate_search_options(self, options: Dict[str, Any]) -> bool:
        """验证搜索选项"""
        try:
            # 检查必要的选项类型
            if 'case_sensitive' in options and not isinstance(options['case_sensitive'], bool):
                return False
            if 'use_regex' in options and not isinstance(options['use_regex'], bool):
                return False
            if 'whole_word' in options and not isinstance(options['whole_word'], bool):
                return False
            
            # 检查未知选项
            valid_options = {'case_sensitive', 'use_regex', 'whole_word', 'file_extensions'}
            for key in options.keys():
                if key not in valid_options:
                    return False
            
            return True
        except Exception as e:
            self.log_error("Error validating search options", e)
            return False
    
    def optimize_search_for_large_file(self, file_size: int) -> bool:
        """判断是否需要对大文件进行搜索优化"""
        # 文件大小超过 1MB 时启用优化
        large_file_threshold = 1024 * 1024  # 1MB
        return file_size > large_file_threshold
    
    def get_search_cache(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        """获取搜索缓存"""
        # 简单的内存缓存实现
        if not hasattr(self, '_search_cache'):
            self._search_cache = {}
        
        cache_entry = self._search_cache.get(cache_key)
        if cache_entry:
            # 检查缓存是否过期（5分钟）
            import time
            if time.time() - cache_entry['timestamp'] < 300:
                return cache_entry['data']
            else:
                # 清除过期缓存
                del self._search_cache[cache_key]
        
        return None
    
    def set_search_cache(self, cache_key: str, data: List[Dict[str, Any]]):
        """设置搜索缓存"""
        if not hasattr(self, '_search_cache'):
            self._search_cache = {}
        
        import time
        self._search_cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
    
    async def _cleanup(self):
        """清理服务资源"""
        # SearchReplaceService 没有需要特别清理的资源
        await super()._cleanup()


# 创建全局服务实例
search_replace_service = SearchReplaceService()


# 导出
__all__ = ["SearchReplaceService", "search_replace_service"]