// 搜索替换服务

import { ApiService } from './api';
import { 
  SearchRequest, 
  SearchResponse, 
  ReplaceResponse 
} from './types/file';
import { ApiResponse, SearchOptions } from '../types/api';

class SearchReplaceService {
  constructor(private apiService: ApiService) {}

  // 搜索文本
  async searchText(sessionId: string, query: string, options?: SearchOptions): Promise<SearchResponse> {
    const request: SearchRequest = {
      query,
      options: {
        case_sensitive: options?.case_sensitive || false,
        whole_word: options?.whole_word || false,
        regex: options?.regex || false,
        file_types: options?.file_types,
        include_paths: options?.include_paths,
        exclude_paths: options?.exclude_paths
      }
    };

    const response = await this.apiService.post<ApiResponse<SearchResponse>>(
      `/sessions/${sessionId}/search`,
      request
    );
    return response.data as unknown as SearchResponse;
  }

  // 替换文本
  async replaceText(sessionId: string, filePath: string, searchText: string, replaceText: string, options?: {
    case_sensitive?: boolean;
    whole_word?: boolean;
    regex?: boolean;
    replace_all?: boolean;
  }): Promise<ReplaceResponse> {
    const response = await this.apiService.post<ApiResponse<ReplaceResponse>>(
      `/sessions/${sessionId}/replace`,
      {
        file_path: filePath,
        search_text: searchText,
        replace_text: replaceText,
        options: {
          case_sensitive: options?.case_sensitive || false,
          whole_word: options?.whole_word || false,
          regex: options?.regex || false,
          replace_all: options?.replace_all || false
        }
      }
    );
    return response.data as unknown as ReplaceResponse;
  }


}

import { apiService } from './api';

// 创建服务实例
export const searchReplaceService = new SearchReplaceService(apiService);
export default SearchReplaceService;