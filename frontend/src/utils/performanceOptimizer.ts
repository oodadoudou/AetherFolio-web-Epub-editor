/**
 * 性能优化器 - 监控和优化EPUB编辑器性能
 * 包括内存管理、FPS监控、缓存优化等功能
 */

import { debounce, throttle } from 'lodash';

// 性能指标接口
export interface PerformanceMetrics {
  renderTime: number;
  fps: number;
  frameDrops: number;
  syncTime: number;
  syncLatency: number;
  syncErrors: number;
  memoryUsage: number;
  memoryPeak: number;
  memoryLeaks: number;
  resourceLoadTime: number;
  cacheHitRate: number;
  networkRequests: number;
  inputLatency: number;
  scrollLatency: number;
  clickLatency: number;
  cpuUsage: number;
  domNodes: number;
  eventListeners: number;
}

// 性能阈值配置
export interface PerformanceThresholds {
  maxMemoryUsage: number; // MB
  minFPS: number;
  maxRenderTime: number; // ms
  maxSyncLatency: number; // ms
  maxInputLatency: number; // ms
}

// 优化选项
export interface OptimizationOptions {
  enableMonitoring: boolean;
  enableOptimization: boolean;
  memoryThreshold: number;
  fpsThreshold: number;
  autoGC: boolean;
  cacheOptimization: boolean;
  domOptimization: boolean;
  eventOptimization: boolean;
}

// 性能优化器选项
export interface PerformanceOptimizerOptions {
  enableMonitoring: boolean;
  enableOptimization: boolean;
  memoryThreshold: number;
  fpsThreshold: number;
  onMetricsUpdate?: (metrics: PerformanceMetrics) => void;
  onPerformanceWarning?: (warning: PerformanceWarning) => void;
}

// 性能警告接口
export interface PerformanceWarning {
  type: 'memory' | 'fps' | 'latency' | 'leak';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  value: number;
  threshold: number;
  timestamp: number;
  suggestions: string[];
}

// 内存快照接口
interface MemorySnapshot {
  timestamp: number;
  usedJSHeapSize: number;
  totalJSHeapSize: number;
  jsHeapSizeLimit: number;
  domNodes: number;
  eventListeners: number;
}

// FPS监控器
class FPSMonitor {
  private frames: number[] = [];
  private lastTime: number = 0;
  private frameCount: number = 0;
  private animationId: number | null = null;
  
  public start(): void {
    this.lastTime = performance.now();
    this.frameCount = 0;
    this.frames = [];
    this.tick();
  }
  
  public stop(): void {
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }
  
  private tick = (): void => {
    const now = performance.now();
    const delta = now - this.lastTime;
    
    this.frames.push(1000 / delta);
    if (this.frames.length > 60) {
      this.frames.shift();
    }
    
    this.lastTime = now;
    this.frameCount++;
    
    this.animationId = requestAnimationFrame(this.tick);
  };
  
  public getFPS(): number {
    if (this.frames.length === 0) return 0;
    return this.frames.reduce((sum, fps) => sum + fps, 0) / this.frames.length;
  }
  
  public getFrameDrops(): number {
    return this.frames.filter(fps => fps < 30).length;
  }
}

// 内存监控器
class MemoryMonitor {
  private snapshots: MemorySnapshot[] = [];
  private maxSnapshots: number = 100;
  private intervalId: number | null = null;
  
  public start(interval: number = 5000): void {
    this.intervalId = window.setInterval(() => {
      this.takeSnapshot();
    }, interval);
  }
  
  public stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }
  
  private takeSnapshot(): void {
    if (!('memory' in performance)) return;
    
    const memory = (performance as any).memory;
    const snapshot: MemorySnapshot = {
      timestamp: Date.now(),
      usedJSHeapSize: memory.usedJSHeapSize,
      totalJSHeapSize: memory.totalJSHeapSize,
      jsHeapSizeLimit: memory.jsHeapSizeLimit,
      domNodes: document.querySelectorAll('*').length,
      eventListeners: this.getEventListenerCount()
    };
    
    this.snapshots.push(snapshot);
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots.shift();
    }
  }
  
  private getEventListenerCount(): number {
    // 简化的事件监听器计数（实际实现可能更复杂）
    return document.querySelectorAll('[onclick], [onload], [onchange]').length;
  }
  
  public getCurrentMemoryUsage(): number {
    if (!('memory' in performance)) return 0;
    return (performance as any).memory.usedJSHeapSize;
  }
  
  public getPeakMemoryUsage(): number {
    if (this.snapshots.length === 0) return 0;
    return Math.max(...this.snapshots.map(s => s.usedJSHeapSize));
  }
  
  public detectMemoryLeaks(): number {
    if (this.snapshots.length < 10) return 0;
    
    const recent = this.snapshots.slice(-10);
    const trend = this.calculateTrend(recent.map(s => s.usedJSHeapSize));
    
    // 如果内存使用呈持续上升趋势，可能存在内存泄漏
    return trend > 0.1 ? trend : 0;
  }
  
  private calculateTrend(values: number[]): number {
    if (values.length < 2) return 0;
    
    const n = values.length;
    const sumX = (n * (n - 1)) / 2;
    const sumY = values.reduce((sum, val) => sum + val, 0);
    const sumXY = values.reduce((sum, val, i) => sum + i * val, 0);
    const sumX2 = (n * (n - 1) * (2 * n - 1)) / 6;
    
    const slope = (n * sumXY - sumX * sumY) / (n * sumX2 - sumX * sumX);
    return slope / (sumY / n); // 归一化斜率
  }
  
  public getSnapshots(): MemorySnapshot[] {
    return [...this.snapshots];
  }
}

// 延迟监控器
class LatencyMonitor {
  private inputLatencies: number[] = [];
  private scrollLatencies: number[] = [];
  private clickLatencies: number[] = [];
  private maxSamples: number = 50;
  
  public recordInputLatency(latency: number): void {
    this.inputLatencies.push(latency);
    if (this.inputLatencies.length > this.maxSamples) {
      this.inputLatencies.shift();
    }
  }
  
  public recordScrollLatency(latency: number): void {
    this.scrollLatencies.push(latency);
    if (this.scrollLatencies.length > this.maxSamples) {
      this.scrollLatencies.shift();
    }
  }
  
  public recordClickLatency(latency: number): void {
    this.clickLatencies.push(latency);
    if (this.clickLatencies.length > this.maxSamples) {
      this.clickLatencies.shift();
    }
  }
  
  public getAverageInputLatency(): number {
    return this.calculateAverage(this.inputLatencies);
  }
  
  public getAverageScrollLatency(): number {
    return this.calculateAverage(this.scrollLatencies);
  }
  
  public getAverageClickLatency(): number {
    return this.calculateAverage(this.clickLatencies);
  }
  
  private calculateAverage(values: number[]): number {
    if (values.length === 0) return 0;
    return values.reduce((sum, val) => sum + val, 0) / values.length;
  }
}

export class PerformanceOptimizer {
  private options: PerformanceOptimizerOptions;
  private onMetricsUpdate?: (metrics: PerformanceMetrics) => void;
  private onPerformanceWarning?: (warning: PerformanceWarning) => void;
  
  private fpsMonitor: FPSMonitor;
  private memoryMonitor: MemoryMonitor;
  private latencyMonitor: LatencyMonitor;
  
  private metrics: PerformanceMetrics;
  private thresholds: PerformanceThresholds;
  private isMonitoring: boolean = false;
  private updateInterval: number | null = null;
  
  // 缓存管理
  private cacheStats = {
    hits: 0,
    misses: 0,
    size: 0
  };
  
  // 性能观察器
  private performanceObserver: PerformanceObserver | null = null;
  private resizeObserver: ResizeObserver | null = null;
  
  // 防抖和节流函数
  private debouncedOptimization: Function;
  private throttledMetricsUpdate: Function;
  
  constructor(options: PerformanceOptimizerOptions) {
    this.options = options;
    this.onMetricsUpdate = options.onMetricsUpdate;
    this.onPerformanceWarning = options.onPerformanceWarning;
    
    // 初始化监控器
    this.fpsMonitor = new FPSMonitor();
    this.memoryMonitor = new MemoryMonitor();
    this.latencyMonitor = new LatencyMonitor();
    
    // 初始化指标
    this.metrics = this.createInitialMetrics();
    
    // 设置阈值
    this.thresholds = {
      maxMemoryUsage: this.options.memoryThreshold / (1024 * 1024), // 转换为MB
      minFPS: this.options.fpsThreshold,
      maxRenderTime: 16.67, // 60fps对应的帧时间
      maxSyncLatency: 100,
      maxInputLatency: 50
    };
    
    // 初始化防抖和节流函数
    this.debouncedOptimization = debounce(this.performOptimization.bind(this), 1000);
    this.throttledMetricsUpdate = throttle(this.updateMetrics.bind(this), 1000);
    
    if (this.options.enableMonitoring) {
      this.startMonitoring();
    }
  }
  
  /**
   * 创建初始性能指标
   */
  private createInitialMetrics(): PerformanceMetrics {
    return {
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
    };
  }
  
  /**
   * 开始性能监控
   */
  public startMonitoring(): void {
    if (this.isMonitoring) return;
    
    this.isMonitoring = true;
    
    // 启动各种监控器
    this.fpsMonitor.start();
    this.memoryMonitor.start();
    this.setupPerformanceObserver();
    this.setupEventListeners();
    
    // 定期更新指标
    this.updateInterval = window.setInterval(() => {
      this.throttledMetricsUpdate();
    }, 1000);
    
    console.log('⚡ Performance monitoring started');
  }
  
  /**
   * 停止性能监控
   */
  public stopMonitoring(): void {
    if (!this.isMonitoring) return;
    
    this.isMonitoring = false;
    
    // 停止监控器
    this.fpsMonitor.stop();
    this.memoryMonitor.stop();
    
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }
    
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
    
    this.removeEventListeners();
    
    console.log('⚡ Performance monitoring stopped');
  }
  
  /**
   * 设置性能观察器
   */
  private setupPerformanceObserver(): void {
    if (!('PerformanceObserver' in window)) return;
    
    this.performanceObserver = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      
      for (const entry of entries) {
        switch (entry.entryType) {
          case 'measure':
            if (entry.name.includes('render')) {
              this.metrics.renderTime = entry.duration;
            } else if (entry.name.includes('sync')) {
              this.metrics.syncTime = entry.duration;
            }
            break;
          case 'navigation':
            this.metrics.resourceLoadTime = entry.duration;
            break;
          case 'resource':
            this.metrics.networkRequests++;
            break;
        }
      }
    });
    
    try {
      this.performanceObserver.observe({ entryTypes: ['measure', 'navigation', 'resource'] });
    } catch (error) {
      console.warn('Failed to setup performance observer:', error);
    }
  }
  
  /**
   * 设置事件监听器
   */
  private setupEventListeners(): void {
    // 输入延迟监控
    document.addEventListener('input', this.handleInputEvent.bind(this));
    document.addEventListener('scroll', this.handleScrollEvent.bind(this));
    document.addEventListener('click', this.handleClickEvent.bind(this));
    
    // 窗口大小变化监控
    if ('ResizeObserver' in window) {
      this.resizeObserver = new ResizeObserver(() => {
        this.debouncedOptimization();
      });
      this.resizeObserver.observe(document.body);
    }
  }
  
  /**
   * 移除事件监听器
   */
  private removeEventListeners(): void {
    document.removeEventListener('input', this.handleInputEvent.bind(this));
    document.removeEventListener('scroll', this.handleScrollEvent.bind(this));
    document.removeEventListener('click', this.handleClickEvent.bind(this));
  }
  
  /**
   * 处理输入事件
   */
  private handleInputEvent(event: Event): void {
    const startTime = performance.now();
    
    requestAnimationFrame(() => {
      const latency = performance.now() - startTime;
      this.latencyMonitor.recordInputLatency(latency);
      
      if (latency > this.thresholds.maxInputLatency) {
        this.emitPerformanceWarning({
          type: 'latency',
          severity: 'medium',
          message: 'High input latency detected',
          value: latency,
          threshold: this.thresholds.maxInputLatency,
          timestamp: Date.now(),
          suggestions: [
            'Reduce DOM complexity',
            'Optimize event handlers',
            'Use debouncing for frequent events'
          ]
        });
      }
    });
  }
  
  /**
   * 处理滚动事件
   */
  private handleScrollEvent(event: Event): void {
    const startTime = performance.now();
    
    requestAnimationFrame(() => {
      const latency = performance.now() - startTime;
      this.latencyMonitor.recordScrollLatency(latency);
    });
  }
  
  /**
   * 处理点击事件
   */
  private handleClickEvent(event: Event): void {
    const startTime = performance.now();
    
    requestAnimationFrame(() => {
      const latency = performance.now() - startTime;
      this.latencyMonitor.recordClickLatency(latency);
    });
  }
  
  /**
   * 更新性能指标
   */
  private updateMetrics(): void {
    // 更新FPS指标
    this.metrics.fps = this.fpsMonitor.getFPS();
    this.metrics.frameDrops = this.fpsMonitor.getFrameDrops();
    
    // 更新内存指标
    this.metrics.memoryUsage = this.memoryMonitor.getCurrentMemoryUsage();
    this.metrics.memoryPeak = this.memoryMonitor.getPeakMemoryUsage();
    this.metrics.memoryLeaks = this.memoryMonitor.detectMemoryLeaks();
    
    // 更新延迟指标
    this.metrics.inputLatency = this.latencyMonitor.getAverageInputLatency();
    this.metrics.scrollLatency = this.latencyMonitor.getAverageScrollLatency();
    this.metrics.clickLatency = this.latencyMonitor.getAverageClickLatency();
    
    // 更新DOM指标
    this.metrics.domNodes = document.querySelectorAll('*').length;
    this.metrics.eventListeners = this.getEventListenerCount();
    
    // 更新缓存指标
    this.metrics.cacheHitRate = this.calculateCacheHitRate();
    
    // 检查性能阈值
    this.checkPerformanceThresholds();
    
    // 触发指标更新回调
    this.onMetricsUpdate?.(this.metrics);
    
    // 如果启用优化，执行优化操作
    if (this.options.enableOptimization) {
      this.debouncedOptimization();
    }
  }
  
  /**
   * 获取事件监听器数量
   */
  private getEventListenerCount(): number {
    // 简化实现，实际可能需要更复杂的计算
    return document.querySelectorAll('[onclick], [onload], [onchange], [oninput]').length;
  }
  
  /**
   * 计算缓存命中率
   */
  private calculateCacheHitRate(): number {
    const total = this.cacheStats.hits + this.cacheStats.misses;
    return total > 0 ? (this.cacheStats.hits / total) * 100 : 100;
  }
  
  /**
   * 检查性能阈值
   */
  private checkPerformanceThresholds(): void {
    // 检查内存使用
    const memoryMB = this.metrics.memoryUsage / (1024 * 1024);
    if (memoryMB > this.thresholds.maxMemoryUsage) {
      this.emitPerformanceWarning({
        type: 'memory',
        severity: memoryMB > this.thresholds.maxMemoryUsage * 1.5 ? 'high' : 'medium',
        message: 'High memory usage detected',
        value: memoryMB,
        threshold: this.thresholds.maxMemoryUsage,
        timestamp: Date.now(),
        suggestions: [
          'Clear unused caches',
          'Reduce DOM complexity',
          'Optimize image sizes',
          'Remove unused event listeners'
        ]
      });
    }
    
    // 检查FPS
    if (this.metrics.fps < this.thresholds.minFPS) {
      this.emitPerformanceWarning({
        type: 'fps',
        severity: this.metrics.fps < this.thresholds.minFPS * 0.5 ? 'high' : 'medium',
        message: 'Low FPS detected',
        value: this.metrics.fps,
        threshold: this.thresholds.minFPS,
        timestamp: Date.now(),
        suggestions: [
          'Reduce animation complexity',
          'Optimize rendering operations',
          'Use CSS transforms instead of changing layout properties',
          'Implement virtual scrolling'
        ]
      });
    }
    
    // 检查内存泄漏
    if (this.metrics.memoryLeaks > 0.1) {
      this.emitPerformanceWarning({
        type: 'leak',
        severity: 'high',
        message: 'Potential memory leak detected',
        value: this.metrics.memoryLeaks,
        threshold: 0.1,
        timestamp: Date.now(),
        suggestions: [
          'Check for uncleaned event listeners',
          'Verify proper cleanup of intervals and timeouts',
          'Review closure usage',
          'Use WeakMap for temporary references'
        ]
      });
    }
  }
  
  /**
   * 发出性能警告
   */
  private emitPerformanceWarning(warning: PerformanceWarning): void {
    console.warn(`⚠️ Performance Warning [${warning.severity}]:`, warning.message, {
      value: warning.value,
      threshold: warning.threshold,
      suggestions: warning.suggestions
    });
    
    this.onPerformanceWarning?.(warning);
  }
  
  /**
   * 执行性能优化
   */
  private performOptimization(): void {
    if (!this.options.enableOptimization) return;
    
    console.log('🔧 Performing automatic optimization...');
    
    // 内存优化
    this.optimizeMemory();
    
    // DOM优化
    this.optimizeDOM();
    
    // 缓存优化
    this.optimizeCache();
    
    // 事件优化
    this.optimizeEvents();
  }
  
  /**
   * 内存优化
   */
  private optimizeMemory(): void {
    // 强制垃圾回收（如果可用）
    if ('gc' in window && typeof (window as any).gc === 'function') {
      (window as any).gc();
    }
    
    // 清理未使用的缓存
    this.clearUnusedCaches();
  }
  
  /**
   * DOM优化
   */
  private optimizeDOM(): void {
    // 移除不可见的元素
    const hiddenElements = document.querySelectorAll('[style*="display: none"], [hidden]');
    hiddenElements.forEach(element => {
      if (element.parentNode && !element.hasAttribute('data-keep')) {
        element.remove();
      }
    });
    
    // 优化图片加载
    const images = document.querySelectorAll('img[data-src]');
    images.forEach(img => {
      const rect = img.getBoundingClientRect();
      if (rect.top < window.innerHeight + 100) {
        const src = img.getAttribute('data-src');
        if (src) {
          img.setAttribute('src', src);
          img.removeAttribute('data-src');
        }
      }
    });
  }
  
  /**
   * 缓存优化
   */
  private optimizeCache(): void {
    // 清理过期的缓存项
    if ('caches' in window) {
      caches.keys().then(cacheNames => {
        cacheNames.forEach(cacheName => {
          if (cacheName.includes('old') || cacheName.includes('temp')) {
            caches.delete(cacheName);
          }
        });
      });
    }
  }
  
  /**
   * 事件优化
   */
  private optimizeEvents(): void {
    // 移除重复的事件监听器（简化实现）
    const elements = document.querySelectorAll('[onclick]');
    elements.forEach(element => {
      const onclick = element.getAttribute('onclick');
      if (onclick && onclick.includes('duplicate')) {
        element.removeAttribute('onclick');
      }
    });
  }
  
  /**
   * 清理未使用的缓存
   */
  private clearUnusedCaches(): void {
    // 实现缓存清理逻辑
    this.cacheStats.size = 0;
  }
  
  /**
   * 记录缓存命中
   */
  public recordCacheHit(): void {
    this.cacheStats.hits++;
  }
  
  /**
   * 记录缓存未命中
   */
  public recordCacheMiss(): void {
    this.cacheStats.misses++;
  }
  
  /**
   * 记录同步时间
   */
  public recordSyncTime(time: number): void {
    this.metrics.syncTime = time;
  }
  
  /**
   * 记录同步延迟
   */
  public recordSyncLatency(latency: number): void {
    this.metrics.syncLatency = latency;
  }
  
  /**
   * 记录同步错误
   */
  public recordSyncError(): void {
    this.metrics.syncErrors++;
  }
  
  /**
   * 获取当前性能指标
   */
  public getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }
  
  /**
   * 重置性能指标
   */
  public resetMetrics(): void {
    this.metrics = this.createInitialMetrics();
    this.cacheStats = { hits: 0, misses: 0, size: 0 };
  }
  
  /**
   * 更新配置
   */
  public updateOptions(newOptions: Partial<PerformanceOptimizerOptions>): void {
    this.options = { ...this.options, ...newOptions };
    
    if (newOptions.enableMonitoring !== undefined) {
      if (newOptions.enableMonitoring && !this.isMonitoring) {
        this.startMonitoring();
      } else if (!newOptions.enableMonitoring && this.isMonitoring) {
        this.stopMonitoring();
      }
    }
  }
  
  /**
   * 获取性能报告
   */
  public getPerformanceReport(): {
    metrics: PerformanceMetrics;
    thresholds: PerformanceThresholds;
    memorySnapshots: MemorySnapshot[];
    recommendations: string[];
  } {
    const recommendations: string[] = [];
    
    if (this.metrics.fps < this.thresholds.minFPS) {
      recommendations.push('Consider optimizing rendering performance');
    }
    
    if (this.metrics.memoryUsage > this.thresholds.maxMemoryUsage * 1024 * 1024) {
      recommendations.push('Memory usage is high, consider cleanup');
    }
    
    if (this.metrics.inputLatency > this.thresholds.maxInputLatency) {
      recommendations.push('Input latency is high, optimize event handlers');
    }
    
    if (this.metrics.domNodes > 5000) {
      recommendations.push('DOM complexity is high, consider virtualization');
    }
    
    return {
      metrics: this.metrics,
      thresholds: this.thresholds,
      memorySnapshots: this.memoryMonitor.getSnapshots(),
      recommendations
    };
  }
  
  /**
   * 销毁性能优化器
   */
  public destroy(): void {
    this.stopMonitoring();
    
    // 清理资源
    this.cacheStats = { hits: 0, misses: 0, size: 0 };
    
    console.log('🗑️ Performance optimizer destroyed');
  }
}

export default PerformanceOptimizer;