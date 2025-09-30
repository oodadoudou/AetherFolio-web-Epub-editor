/**
 * 优化的预览面板组件V3 - 集成最新同步管理器和性能监控
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Card, Button, Tooltip, Switch, Slider, Badge, Space, Dropdown, Menu } from 'antd';
import {
  SyncOutlined,
  ReloadOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  SettingOutlined,
  EyeOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  MenuOutlined,
  MonitorOutlined,
  ThunderboltOutlined,
  BugOutlined
} from '@ant-design/icons';
import { OptimizedSyncManagerV2, SyncEvent, SyncMetrics } from '../utils/optimizedSyncManagerV2';
import PerformanceMonitor, { PerformanceMetrics } from './PerformanceMonitor';
import VirtualScroll from './VirtualScroll';
import { debounce, throttle } from 'lodash';

interface PreviewSettings {
  fontSize: number;
  lineHeight: number;
  zoom: number;
  showLineNumbers: boolean;
  enableImagePreview: boolean;
  smoothScroll: boolean;
  virtualDOM: boolean;
  incrementalUpdate: boolean;
  performanceMonitor: boolean;
  syncEnabled: boolean;
  autoRefresh: boolean;
  theme: 'light' | 'dark';
}

interface PreviewPanelProps {
  content: string;
  editor?: any;
  onSyncEvent?: (event: SyncEvent) => void;
  className?: string;
  style?: React.CSSProperties;
  initialSettings?: Partial<PreviewSettings>;
  enableVirtualScroll?: boolean;
  maxContentLength?: number;
  isDarkMode?: boolean;
}

interface ContentChunk {
  id: string;
  content: string;
  lineStart: number;
  lineEnd: number;
  height?: number;
}

const OptimizedPreviewPanelV3: React.FC<PreviewPanelProps> = ({
  content,
  editor,
  onSyncEvent,
  className,
  style,
  initialSettings = {},
  enableVirtualScroll = true,
  maxContentLength = 100000,
  isDarkMode = false
}) => {
  const [settings, setSettings] = useState<PreviewSettings>({
    fontSize: 14,
    lineHeight: 1.6,
    zoom: 100,
    showLineNumbers: false,
    enableImagePreview: true,
    smoothScroll: true,
    virtualDOM: true,
    incrementalUpdate: true,
    performanceMonitor: false,
    syncEnabled: true,
    autoRefresh: true,
    theme: isDarkMode ? 'dark' : 'light',
    ...initialSettings
  });
  
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdateTime, setLastUpdateTime] = useState<Date | null>(null);
  const [renderTime, setRenderTime] = useState(0);
  const [contentChunks, setContentChunks] = useState<ContentChunk[]>([]);
  const [visibleChunks, setVisibleChunks] = useState<Set<string>>(new Set());
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    renderTime: 0,
    fps: 60,
    frameDrops: 0,
    syncTime: 0,
    syncLatency: 0,
    syncErrors: 0,
    memoryUsage: 0,
    memoryPeak: 0,
    memoryLeaks: 0,
    resourceLoadTime: 0,
    cacheHitRate: 100,
    networkRequests: 0,
    inputLatency: 0,
    scrollLatency: 0,
    clickLatency: 0,
    cpuUsage: 0,
    domNodes: 0,
    eventListeners: 0
  });
  
  const previewRef = useRef<HTMLDivElement>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const syncManagerRef = useRef<OptimizedSyncManagerV2 | null>(null);
  const contentCacheRef = useRef<Map<string, string>>(new Map());
  const renderTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const performanceObserverRef = useRef<PerformanceObserver | null>(null);
  const lastContentRef = useRef<string>('');
  const chunkSizeRef = useRef(1000); // 每个块的行数
  
  // 内容处理和缓存
  const processedContent = useMemo(() => {
    const startTime = performance.now();
    
    // 检查缓存
    const cacheKey = `content-${content.length}-${content.slice(0, 100)}`;
    const cached = contentCacheRef.current.get(cacheKey);
    
    if (cached && content === lastContentRef.current) {
      return cached;
    }
    
    // 处理内容
    let processed = content;
    
    // 添加行号（如果启用）
    if (settings.showLineNumbers) {
      const lines = processed.split('\n');
      processed = lines.map((line, index) => 
        `<div class="line" data-line="${index + 1}">
          <span class="line-number">${index + 1}</span>
          <span class="line-content">${line}</span>
        </div>`
      ).join('\n');
    }
    
    // 添加元素ID（用于同步）
    processed = processed.replace(/<(h[1-6]|p|div|section|article)([^>]*)>/gi, (match, tag, attrs) => {
      const id = `element-${Math.random().toString(36).substr(2, 9)}`;
      return `<${tag}${attrs} id="${id}">`;
    });
    
    // 优化图片加载
    if (settings.enableImagePreview) {
      processed = processed.replace(/<img([^>]*)src="([^"]+)"([^>]*)>/gi, 
        '<img$1src="$2"$3 loading="lazy" onerror="this.style.display=\'none\'">');
    }
    
    // 缓存处理结果
    contentCacheRef.current.set(cacheKey, processed);
    lastContentRef.current = content;
    
    // 更新渲染时间
    const endTime = performance.now();
    setRenderTime(endTime - startTime);
    
    return processed;
  }, [content, settings.showLineNumbers, settings.enableImagePreview]);
  
  // 内容分块（用于虚拟滚动）
  const generateContentChunks = useCallback(() => {
    if (!enableVirtualScroll || content.length < maxContentLength) {
      return [];
    }
    
    const lines = content.split('\n');
    const chunks: ContentChunk[] = [];
    const chunkSize = chunkSizeRef.current;
    
    for (let i = 0; i < lines.length; i += chunkSize) {
      const chunkLines = lines.slice(i, i + chunkSize);
      const chunkContent = chunkLines.join('\n');
      
      chunks.push({
        id: `chunk-${i}`,
        content: chunkContent,
        lineStart: i + 1,
        lineEnd: Math.min(i + chunkSize, lines.length),
        height: chunkLines.length * 20 // 估算高度
      });
    }
    
    return chunks;
  }, [content, enableVirtualScroll, maxContentLength]);
  
  // 更新内容块
  useEffect(() => {
    const chunks = generateContentChunks();
    setContentChunks(chunks);
  }, [generateContentChunks]);
  
  // 初始化同步管理器
  useEffect(() => {
    if (!editor || !iframeRef.current) return;
    
    const syncManager = new OptimizedSyncManagerV2({
      bidirectional: settings.syncEnabled,
      scrollSyncDelay: 50,
      contentSyncDelay: 300,
      smartSync: true,
      virtualDOM: settings.virtualDOM,
      incrementalUpdates: settings.incrementalUpdate,
      lineMapping: true,
      debug: process.env.NODE_ENV === 'development',
      performanceMonitoring: settings.performanceMonitor
    });
    
    syncManager.initEditor(editor);
    syncManager.initPreview(iframeRef.current);
    
    // 监听同步事件
    const handleSyncEvent = (event: CustomEvent<SyncEvent>) => {
      onSyncEvent?.(event.detail);
      
      // 更新性能指标
      if (settings.performanceMonitor) {
        const metrics = syncManager.getMetrics();
        setPerformanceMetrics(prev => ({
          ...prev,
          syncTime: metrics.syncTime,
          syncLatency: metrics.syncLatency,
          syncErrors: metrics.syncErrors
        }));
      }
    };
    
    window.addEventListener('sync', handleSyncEvent as EventListener);
    
    syncManagerRef.current = syncManager;
    
    return () => {
      window.removeEventListener('sync', handleSyncEvent as EventListener);
      syncManager.destroy();
      syncManagerRef.current = null;
    };
  }, [editor, settings.syncEnabled, settings.virtualDOM, settings.incrementalUpdate, settings.performanceMonitor, onSyncEvent]);
  
  // 性能监控
  useEffect(() => {
    if (!settings.performanceMonitor) return;
    
    // 设置性能观察器
    if ('PerformanceObserver' in window) {
      performanceObserverRef.current = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        
        entries.forEach(entry => {
          if (entry.name.includes('preview-render')) {
            setPerformanceMetrics(prev => ({
              ...prev,
              renderTime: entry.duration
            }));
          }
        });
      });
      
      try {
        performanceObserverRef.current.observe({ entryTypes: ['measure'] });
      } catch (error) {
        console.warn('Performance observer not supported:', error);
      }
    }
    
    // 定期更新性能指标
    const interval = setInterval(() => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        setPerformanceMetrics(prev => ({
          ...prev,
          memoryUsage: memory.usedJSHeapSize || 0,
          domNodes: document.querySelectorAll('*').length
        }));
      }
    }, 1000);
    
    return () => {
      clearInterval(interval);
      if (performanceObserverRef.current) {
        performanceObserverRef.current.disconnect();
        performanceObserverRef.current = null;
      }
    };
  }, [settings.performanceMonitor]);
  
  // 内容更新处理
  const updateContent = useCallback(
    debounce(() => {
      if (!iframeRef.current) return;
      
      const startTime = performance.now();
      performance.mark('preview-render-start');
      
      setIsLoading(true);
      
      // 清除之前的超时
      if (renderTimeoutRef.current) {
        clearTimeout(renderTimeoutRef.current);
      }
      
      renderTimeoutRef.current = setTimeout(() => {
        try {
          const iframe = iframeRef.current;
          if (!iframe || !iframe.contentDocument) return;
          
          const doc = iframe.contentDocument;
          
          // 构建完整的HTML文档
          const htmlContent = `
            <!DOCTYPE html>
            <html>
            <head>
              <meta charset="utf-8">
              <meta name="viewport" content="width=device-width, initial-scale=1">
              <title>Preview</title>
              <style>
                body {
                  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                  font-size: ${settings.fontSize}px;
                  line-height: ${settings.lineHeight};
                  margin: 0;
                  padding: 20px;
                  background: ${settings.theme === 'dark' ? '#1f1f1f' : '#ffffff'};
                  color: ${settings.theme === 'dark' ? '#e0e0e0' : '#333333'};
                  zoom: ${settings.zoom}%;
                  scroll-behavior: ${settings.smoothScroll ? 'smooth' : 'auto'};
                }
                
                .line {
                  display: flex;
                  min-height: 1.2em;
                }
                
                .line-number {
                  display: inline-block;
                  width: 40px;
                  text-align: right;
                  margin-right: 10px;
                  color: #999;
                  font-family: 'Monaco', 'Menlo', monospace;
                  font-size: 0.9em;
                  user-select: none;
                }
                
                .line-content {
                  flex: 1;
                }
                
                .sync-highlight {
                  background-color: rgba(255, 255, 0, 0.3);
                  outline: 2px solid rgba(255, 165, 0, 0.5);
                  transition: background-color 0.3s, outline 0.3s;
                }
                
                img {
                  max-width: 100%;
                  height: auto;
                  border-radius: 4px;
                  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                }
                
                pre {
                  background: ${settings.theme === 'dark' ? '#2d2d2d' : '#f5f5f5'};
                  padding: 12px;
                  border-radius: 4px;
                  overflow-x: auto;
                }
                
                code {
                  background: ${settings.theme === 'dark' ? '#2d2d2d' : '#f5f5f5'};
                  padding: 2px 4px;
                  border-radius: 2px;
                  font-family: 'Monaco', 'Menlo', monospace;
                }
                
                blockquote {
                  border-left: 4px solid #ddd;
                  margin: 0;
                  padding-left: 16px;
                  color: #666;
                }
                
                table {
                  border-collapse: collapse;
                  width: 100%;
                  margin: 16px 0;
                }
                
                th, td {
                  border: 1px solid #ddd;
                  padding: 8px 12px;
                  text-align: left;
                }
                
                th {
                  background: ${settings.theme === 'dark' ? '#2d2d2d' : '#f5f5f5'};
                  font-weight: 600;
                }
                
                .virtual-chunk {
                  border-bottom: 1px solid transparent;
                }
                
                .chunk-placeholder {
                  background: ${settings.theme === 'dark' ? '#2a2a2a' : '#f9f9f9'};
                  color: #999;
                  text-align: center;
                  padding: 20px;
                  font-style: italic;
                }
              </style>
            </head>
            <body>
              ${processedContent}
              
              <script>
                // 同步脚本已在syncManager中注入
                console.log('Preview content loaded');
              </script>
            </body>
            </html>
          `;
          
          // 写入内容
          doc.open();
          doc.write(htmlContent);
          doc.close();
          
          // 更新时间戳
          setLastUpdateTime(new Date());
          
          performance.mark('preview-render-end');
          performance.measure('preview-render', 'preview-render-start', 'preview-render-end');
          
          const endTime = performance.now();
          setRenderTime(endTime - startTime);
          
        } catch (error) {
          console.error('Error updating preview content:', error);
        } finally {
          setIsLoading(false);
        }
      }, 50);
    }, settings.autoRefresh ? 300 : 0),
    [processedContent, settings]
  );
  
  // 监听内容变化
  useEffect(() => {
    updateContent();
  }, [updateContent]);
  
  // 设置更新处理
  const handleSettingChange = useCallback((key: keyof PreviewSettings, value: any) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  }, []);
  
  // 刷新预览
  const handleRefresh = useCallback(() => {
    updateContent();
    
    // 清除缓存
    contentCacheRef.current.clear();
    
    // 重置性能指标
    if (syncManagerRef.current) {
      syncManagerRef.current.resetMetrics();
    }
  }, [updateContent]);
  
  // 全屏切换
  const handleFullscreenToggle = useCallback(() => {
    setIsFullscreen(prev => !prev);
  }, []);
  
  // 缩放控制
  const handleZoomIn = useCallback(() => {
    handleSettingChange('zoom', Math.min(settings.zoom + 10, 200));
  }, [settings.zoom, handleSettingChange]);
  
  const handleZoomOut = useCallback(() => {
    handleSettingChange('zoom', Math.max(settings.zoom - 10, 50));
  }, [settings.zoom, handleSettingChange]);
  
  // 虚拟滚动渲染项目
  const renderVirtualChunk = useCallback((chunk: ContentChunk, index: number, style: React.CSSProperties) => {
    const isVisible = visibleChunks.has(chunk.id);
    
    return (
      <div style={style} className="virtual-chunk">
        {isVisible ? (
          <div dangerouslySetInnerHTML={{ __html: chunk.content }} />
        ) : (
          <div className="chunk-placeholder">
            Lines {chunk.lineStart}-{chunk.lineEnd} (Click to load)
          </div>
        )}
      </div>
    );
  }, [visibleChunks]);
  
  // 虚拟滚动项目可见性变化
  const handleVirtualItemsRendered = useCallback((startIndex: number, endIndex: number) => {
    const newVisibleChunks = new Set<string>();
    
    for (let i = startIndex; i <= endIndex; i++) {
      if (contentChunks[i]) {
        newVisibleChunks.add(contentChunks[i].id);
      }
    }
    
    setVisibleChunks(newVisibleChunks);
  }, [contentChunks]);
  
  // 设置菜单
  const settingsMenu = (
    <Menu>
      <Menu.Item key="fontSize">
        <div className="flex items-center justify-between w-48">
          <span>字体大小</span>
          <Slider
            min={10}
            max={24}
            value={settings.fontSize}
            onChange={(value) => handleSettingChange('fontSize', value)}
            style={{ width: 80 }}
          />
        </div>
      </Menu.Item>
      
      <Menu.Item key="lineHeight">
        <div className="flex items-center justify-between w-48">
          <span>行高</span>
          <Slider
            min={1.0}
            max={2.0}
            step={0.1}
            value={settings.lineHeight}
            onChange={(value) => handleSettingChange('lineHeight', value)}
            style={{ width: 80 }}
          />
        </div>
      </Menu.Item>
      
      <Menu.Divider />
      
      <Menu.Item key="lineNumbers">
        <div className="flex items-center justify-between w-48">
          <span>显示行号</span>
          <Switch
            size="small"
            checked={settings.showLineNumbers}
            onChange={(checked) => handleSettingChange('showLineNumbers', checked)}
          />
        </div>
      </Menu.Item>
      
      <Menu.Item key="imagePreview">
        <div className="flex items-center justify-between w-48">
          <span>图片预览</span>
          <Switch
            size="small"
            checked={settings.enableImagePreview}
            onChange={(checked) => handleSettingChange('enableImagePreview', checked)}
          />
        </div>
      </Menu.Item>
      
      <Menu.Item key="smoothScroll">
        <div className="flex items-center justify-between w-48">
          <span>平滑滚动</span>
          <Switch
            size="small"
            checked={settings.smoothScroll}
            onChange={(checked) => handleSettingChange('smoothScroll', checked)}
          />
        </div>
      </Menu.Item>
      
      <Menu.Divider />
      
      <Menu.Item key="virtualDOM">
        <div className="flex items-center justify-between w-48">
          <span>虚拟DOM</span>
          <Switch
            size="small"
            checked={settings.virtualDOM}
            onChange={(checked) => handleSettingChange('virtualDOM', checked)}
          />
        </div>
      </Menu.Item>
      
      <Menu.Item key="incrementalUpdate">
        <div className="flex items-center justify-between w-48">
          <span>增量更新</span>
          <Switch
            size="small"
            checked={settings.incrementalUpdate}
            onChange={(checked) => handleSettingChange('incrementalUpdate', checked)}
          />
        </div>
      </Menu.Item>
      
      <Menu.Item key="performanceMonitor">
        <div className="flex items-center justify-between w-48">
          <span>性能监控</span>
          <Switch
            size="small"
            checked={settings.performanceMonitor}
            onChange={(checked) => handleSettingChange('performanceMonitor', checked)}
          />
        </div>
      </Menu.Item>
    </Menu>
  );
  
  // 工具栏
  const toolbar = (
    <div className="flex items-center justify-between p-2 border-b">
      <div className="flex items-center gap-2">
        <Tooltip title={settings.syncEnabled ? "同步已启用" : "同步已禁用"}>
          <Button
            type={settings.syncEnabled ? "primary" : "default"}
            size="small"
            icon={<SyncOutlined spin={isLoading} />}
            onClick={() => handleSettingChange('syncEnabled', !settings.syncEnabled)}
          />
        </Tooltip>
        
        <Tooltip title="刷新预览">
          <Button
            size="small"
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={isLoading}
          />
        </Tooltip>
        
        <Tooltip title="目录">
          <Button
            size="small"
            icon={<MenuOutlined />}
            onClick={() => {/* TODO: 实现目录功能 */}}
          />
        </Tooltip>
        
        {settings.performanceMonitor && (
          <PerformanceMonitor
            visible={settings.performanceMonitor}
            onVisibilityChange={(visible) => handleSettingChange('performanceMonitor', visible)}
          />
        )}
      </div>
      
      <div className="flex items-center gap-2">
        <Space size="small">
          <Tooltip title="缩小">
            <Button
              size="small"
              icon={<ZoomOutOutlined />}
              onClick={handleZoomOut}
              disabled={settings.zoom <= 50}
            />
          </Tooltip>
          
          <span className="text-xs text-gray-500 min-w-12 text-center">
            {settings.zoom}%
          </span>
          
          <Tooltip title="放大">
            <Button
              size="small"
              icon={<ZoomInOutlined />}
              onClick={handleZoomIn}
              disabled={settings.zoom >= 200}
            />
          </Tooltip>
        </Space>
        
        <Dropdown overlay={settingsMenu} trigger={['click']} placement="bottomRight">
          <Button size="small" icon={<SettingOutlined />} />
        </Dropdown>
        
        <Tooltip title={isFullscreen ? "退出全屏" : "全屏"}>
          <Button
            size="small"
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={handleFullscreenToggle}
          />
        </Tooltip>
      </div>
    </div>
  );
  
  // 状态栏
  const statusBar = (
    <div className="flex items-center justify-between p-2 border-t bg-gray-50 text-xs text-gray-500">
      <div className="flex items-center gap-4">
        <span>渲染时间: {renderTime.toFixed(1)}ms</span>
        {lastUpdateTime && (
          <span>更新时间: {lastUpdateTime.toLocaleTimeString()}</span>
        )}
        {settings.performanceMonitor && (
          <Badge count={performanceMetrics.syncErrors} size="small">
            <span>同步: {performanceMetrics.syncTime.toFixed(1)}ms</span>
          </Badge>
        )}
      </div>
      
      <div className="flex items-center gap-4">
        {enableVirtualScroll && contentChunks.length > 0 && (
          <span>块数: {contentChunks.length}</span>
        )}
        <span>字符: {content.length}</span>
        <span>行数: {content.split('\n').length}</span>
      </div>
    </div>
  );
  
  const containerStyle: React.CSSProperties = {
    height: isFullscreen ? '100vh' : '100%',
    width: isFullscreen ? '100vw' : '100%',
    position: isFullscreen ? 'fixed' : 'relative',
    top: isFullscreen ? 0 : undefined,
    left: isFullscreen ? 0 : undefined,
    zIndex: isFullscreen ? 9999 : undefined,
    background: '#fff',
    ...style
  };
  
  return (
    <Card
      className={`optimized-preview-panel ${className || ''}`}
      style={containerStyle}
      bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}
    >
      {toolbar}
      
      <div className="flex-1 relative overflow-hidden">
        {enableVirtualScroll && contentChunks.length > 0 ? (
          <VirtualScroll
            items={contentChunks}
            itemHeight={(index) => contentChunks[index]?.height || 400}
            containerHeight={400}
            renderItem={renderVirtualChunk}
            onItemsRendered={handleVirtualItemsRendered}
            overscan={2}
            enableSmoothScrolling={settings.smoothScroll}
            className="h-full"
          />
        ) : (
          <iframe
            ref={iframeRef}
            className="w-full h-full border-0"
            title="Preview"
            sandbox="allow-scripts allow-same-origin"
            style={{
              opacity: isLoading ? 0.7 : 1,
              transition: 'opacity 0.2s'
            }}
          />
        )}
        
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-75">
            <div className="flex items-center gap-2 text-gray-500">
              <SyncOutlined spin />
              <span>正在渲染...</span>
            </div>
          </div>
        )}
      </div>
      
      {statusBar}
    </Card>
  );
};

export default OptimizedPreviewPanelV3;
export type { PreviewSettings, PreviewPanelProps };