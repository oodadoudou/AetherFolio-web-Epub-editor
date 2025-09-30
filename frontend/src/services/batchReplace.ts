// 批量替换服务

import { ApiService } from './api';
import { 
  BatchReplaceRequest, 
  ReplaceProgress,
  BatchReplaceResponse
} from './types/upload';
import { ApiResponse, ReplaceRule } from '../types/api';

class BatchReplaceService {
  constructor(private apiService: ApiService) {}

  // 批量替换
  async batchReplace(sessionId: string, rules: ReplaceRule[], options?: {
    create_backup?: boolean;
    validate_rules?: boolean;
    dry_run?: boolean;
  }): Promise<BatchReplaceResponse> {
    const request: BatchReplaceRequest = {
      rules,
      options: {
        create_backup: options?.create_backup || true,
        validate_rules: options?.validate_rules || true,
        dry_run: options?.dry_run || false
      }
    };

    const response = await this.apiService.post<ApiResponse<BatchReplaceResponse>>(
      `/sessions/${sessionId}/batch-replace`,
      request
    );
    return response.data as unknown as BatchReplaceResponse;
  }

  // 获取批量替换进度
  async getBatchReplaceProgress(sessionId: string, taskId: string): Promise<ReplaceProgress> {
    const response = await this.apiService.get<ApiResponse<ReplaceProgress>>(
      `/sessions/${sessionId}/batch-replace/${taskId}/progress`
    );
    return response.data as unknown as ReplaceProgress;
  }

  // 取消批量替换
  async cancelBatchReplace(sessionId: string, taskId: string): Promise<{ success: boolean }> {
    const response = await this.apiService.delete<ApiResponse<{ success: boolean }>>(
      `/sessions/${sessionId}/batch-replace/${taskId}`
    );
    return response.data as unknown as { success: boolean };
  }

  // 验证替换规则
  async validateReplaceRules(rules: ReplaceRule[]): Promise<{
    valid: boolean;
    errors: { rule_index: number; error: string }[];
    warnings: { rule_index: number; warning: string }[];
  }> {
    const response = await this.apiService.post<ApiResponse<{
      valid: boolean;
      errors: { rule_index: number; error: string }[];
      warnings: { rule_index: number; warning: string }[];
    }>>('/validate/replace-rules', { rules });
    return response.data as unknown as {
      valid: boolean;
      errors: { rule_index: number; error: string }[];
      warnings: { rule_index: number; warning: string }[];
    };
  }

  // 下载批量替换模板
  async downloadBatchReplaceTemplate(): Promise<Blob> {
    const response = await this.apiService.get<ApiResponse<Blob>>('/templates/batch-replace.csv');
    return response.data as unknown as Blob;
  }

  // 上传批量替换规则文件
  async uploadBatchReplaceRules(file: File): Promise<{ rules: ReplaceRule[]; errors: string[] }> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await this.apiService.upload<ApiResponse<{ rules: ReplaceRule[]; errors: string[] }>>(
      '/upload/batch-replace-rules',
      formData
    );
    return response.data as unknown as { rules: ReplaceRule[]; errors: string[] };
  }

  // 获取批量替换历史
  async getBatchReplaceHistory(sessionId: string, limit?: number, offset?: number): Promise<{
    tasks: Array<{
      task_id: string;
      start_time: string;
      end_time?: string;
      status: string;
      total_files: number;
      processed_files: number;
      total_replacements: number;
      rules_count: number;
    }>;
    total: number;
  }> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', limit.toString());
    if (offset) params.append('offset', offset.toString());

    const response = await this.apiService.get<ApiResponse<{
      tasks: Array<{
        task_id: string;
        start_time: string;
        end_time?: string;
        status: string;
        total_files: number;
        processed_files: number;
        total_replacements: number;
        rules_count: number;
      }>;
      total: number;
    }>>(`/sessions/${sessionId}/batch-replace/history?${params.toString()}`);
    return response.data as unknown as {
      tasks: Array<{
        task_id: string;
        start_time: string;
        end_time?: string;
        status: string;
        total_files: number;
        processed_files: number;
        total_replacements: number;
        rules_count: number;
      }>;
      total: number;
    };
  }

  // 获取批量替换结果详情
  async getBatchReplaceResult(sessionId: string, taskId: string): Promise<{
    task_id: string;
    status: string;
    total_files: number;
    processed_files: number;
    total_replacements: number;
    files: Array<{
      file_path: string;
      replacements_count: number;
      status: 'success' | 'error' | 'skipped';
      error_message?: string;
    }>;
    start_time: string;
    end_time?: string;
    duration_ms?: number;
  }> {
    const response = await this.apiService.get<ApiResponse<{
      task_id: string;
      status: string;
      total_files: number;
      processed_files: number;
      total_replacements: number;
      files: Array<{
        file_path: string;
        replacements_count: number;
        status: 'success' | 'error' | 'skipped';
        error_message?: string;
      }>;
      start_time: string;
      end_time?: string;
      duration_ms?: number;
    }>>(`/sessions/${sessionId}/batch-replace/${taskId}/result`);
    return response.data as unknown as {
      task_id: string;
      status: string;
      total_files: number;
      processed_files: number;
      total_replacements: number;
      files: Array<{
        file_path: string;
        replacements_count: number;
        status: 'success' | 'error' | 'skipped';
        error_message?: string;
      }>;
      start_time: string;
      end_time?: string;
      duration_ms?: number;
    };
  }
}

import { apiService } from './api';
export const batchReplaceService = new BatchReplaceService(apiService);
export { BatchReplaceService };