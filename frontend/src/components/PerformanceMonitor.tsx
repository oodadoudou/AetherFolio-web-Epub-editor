/**
 * 性能监控器组件 - 实时监控编辑器性能指标
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, Progress, Statistic, Row, Col, Switch, Button, Tooltip, Badge } from 'antd';
import { 
  MonitorOutlined, 
  ThunderboltOutlined, 
  ClockCircleOutlined, 
  DatabaseOutlined,
  EyeOutlined,
  EyeInvisibleOutlined,
  ReloadOutlined,
  WarningOutlined
} from '@ant-design/icons';

interface PerformanceMetrics {
  // 渲染性能
  renderTime: number;
  fps: number;
  frameDrops: number;
  
  // 同步性能
  syncTime: number;
  syncLatency: number;
  syncErrors: number;
  
  // 内存使用
  memoryUsage: number;
  memoryPeak: number;
  memoryLeaks: number;
  
  // 资源加载
  resourceLoadTime: number;
  cacheHitRate: number;
  networkRequests: number;
  
  // 用户交互
  inputLatency: number;
  scrollLatency: number;
  clickLatency: number;
  
  // 系统指标
  cpuUsage: number;
  domNodes: number;
  eventListeners: number;
}

interface PerformanceAlert {
  id: string;
  type: 'warning' | 'error' | 'info';
  message: string;
  timestamp: Date;
  metric: keyof PerformanceMetrics;
  value: number;
  threshold: number;
}

interface PerformanceMonitorProps {
  visible?: boolean;
  onVisibilityChange?: (visible: boolean) => void;
  className?: string;
  style?: React.CSSProperties;
}

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = ({
  visible = false,
  onVisibilityChange,
  className,
  style
}) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
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
  
  const [alerts, setAlerts] = useState<PerformanceAlert[]>([]);
  const [isMonitoring, setIsMonitoring] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  
  const metricsRef = useRef<PerformanceMetrics>(metrics);
  const alertIdRef = useRef(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const observerRef = useRef<PerformanceObserver | null>(null);
  const fpsCounterRef = useRef({ frames: 0, lastTime: performance.now() });
  
  // 性能阈值配置
  const thresholds = {
    renderTime: 16, // 16ms (60fps)
    fps: 30, // 最低30fps
    syncTime: 10, // 10ms
    syncLatency: 50, // 50ms
    memoryUsage: 100, // 100MB
    inputLatency: 100, // 100ms
    scrollLatency: 16, // 16ms
    cpuUsage: 80, // 80%
    domNodes: 5000, // 5000个节点
    eventListeners: 1000 // 1000个监听器
  };
  
  // 添加性能警告
  const addAlert = (type: PerformanceAlert['type'], message: string, metric: keyof PerformanceMetrics, value: number, threshold: number) => {
    const alert: PerformanceAlert = {
      id: `alert-${alertIdRef.current++}`,
      type,
      message,
      timestamp: new Date(),
      metric,
      value,
      threshold
    };
    
    setAlerts(prev => [alert, ...prev.slice(0, 9)]); // 保留最近10个警告
  };
  
  // 检查性能阈值
  const checkThresholds = (newMetrics: PerformanceMetrics) => {
    Object.entries(thresholds).forEach(([key, threshold]) => {
      const metric = key as keyof PerformanceMetrics;
      const value = newMetrics[metric] as number;
      
      if (metric === 'fps' && value < threshold) {
        addAlert('warning', `帧率过低: ${value.toFixed(1)}fps`, metric, value, threshold);
      } else if (metric !== 'fps' && value > threshold) {
        const type = value > threshold * 1.5 ? 'error' : 'warning';
        addAlert(type, `${getMetricName(metric)}过高: ${formatMetricValue(metric, value)}`, metric, value, threshold);
      }
    });
  };
  
  // 获取指标名称
  const getMetricName = (metric: keyof PerformanceMetrics): string => {
    const names: Record<keyof PerformanceMetrics, string> = {
      renderTime: '渲染时间',
      fps: '帧率',
      frameDrops: '丢帧数',
      syncTime: '同步时间',
      syncLatency: '同步延迟',
      syncErrors: '同步错误',
      memoryUsage: '内存使用',
      memoryPeak: '内存峰值',
      memoryLeaks: '内存泄漏',
      resourceLoadTime: '资源加载时间',
      cacheHitRate: '缓存命中率',
      networkRequests: '网络请求',
      inputLatency: '输入延迟',
      scrollLatency: '滚动延迟',
      clickLatency: '点击延迟',
      cpuUsage: 'CPU使用率',
      domNodes: 'DOM节点数',
      eventListeners: '事件监听器'
    };
    return names[metric];
  };
  
  // 格式化指标值
  const formatMetricValue = (metric: keyof PerformanceMetrics, value: number): string => {
    switch (metric) {
      case 'renderTime':
      case 'syncTime':
      case 'syncLatency':
      case 'resourceLoadTime':
      case 'inputLatency':
      case 'scrollLatency':
      case 'clickLatency':
        return `${value.toFixed(1)}ms`;
      case 'fps':
        return `${value.toFixed(1)}fps`;
      case 'memoryUsage':
      case 'memoryPeak':
        return `${(value / 1024 / 1024).toFixed(1)}MB`;
      case 'cacheHitRate':
      case 'cpuUsage':
        return `${value.toFixed(1)}%`;
      default:
        return value.toString();
    }
  };
  
  // 获取指标颜色
  const getMetricColor = (metric: keyof PerformanceMetrics, value: number): string => {
    const threshold = thresholds[metric as keyof typeof thresholds];
    if (!threshold) return '#52c41a';
    
    if (metric === 'fps') {
      if (value >= threshold) return '#52c41a';
      if (value >= threshold * 0.8) return '#faad14';
      return '#ff4d4f';
    } else {
      if (value <= threshold) return '#52c41a';
      if (value <= threshold * 1.2) return '#faad14';
      return '#ff4d4f';
    }
  };
  
  // FPS计算
  const calculateFPS = () => {
    const now = performance.now();
    const delta = now - fpsCounterRef.current.lastTime;
    
    if (delta >= 1000) {
      const fps = (fpsCounterRef.current.frames * 1000) / delta;
      fpsCounterRef.current.frames = 0;
      fpsCounterRef.current.lastTime = now;
      return fps;
    }
    
    fpsCounterRef.current.frames++;
    return null;
  };
  
  // 获取内存使用情况
  const getMemoryUsage = (): number => {
    if ('memory' in performance) {
      const memory = (performance as any).memory;
      return memory.usedJSHeapSize || 0;
    }
    return 0;
  };
  
  // 获取DOM节点数
  const getDOMNodeCount = (): number => {
    return document.querySelectorAll('*').length;
  };
  
  // 获取事件监听器数量（估算）
  const getEventListenerCount = (): number => {
    // 这是一个估算值，实际实现可能需要更复杂的逻辑
    const elements = document.querySelectorAll('*');
    let count = 0;
    
    elements.forEach(element => {
      // 检查常见的事件属性
      const events = ['onclick', 'onmouseover', 'onmouseout', 'onkeydown', 'onkeyup', 'onscroll'];
      events.forEach(event => {
        if ((element as any)[event]) count++;
      });
    });
    
    return count;
  };
  
  // 更新性能指标
  const updateMetrics = () => {
    const newMetrics: PerformanceMetrics = {
      ...metricsRef.current,
      memoryUsage: getMemoryUsage(),
      domNodes: getDOMNodeCount(),
      eventListeners: getEventListenerCount()
    };
    
    // 计算FPS
    const fps = calculateFPS();
    if (fps !== null) {
      newMetrics.fps = fps;
    }
    
    // 获取性能条目
    if (observerRef.current) {
      const entries = performance.getEntriesByType('measure');
      const renderEntries = entries.filter(entry => entry.name.includes('render'));
      if (renderEntries.length > 0) {
        newMetrics.renderTime = renderEntries[renderEntries.length - 1].duration;
      }
    }
    
    // 更新内存峰值
    if (newMetrics.memoryUsage > newMetrics.memoryPeak) {
      newMetrics.memoryPeak = newMetrics.memoryUsage;
    }
    
    metricsRef.current = newMetrics;
    setMetrics(newMetrics);
    
    // 检查阈值
    checkThresholds(newMetrics);
  };
  
  // 重置指标
  const resetMetrics = () => {
    const resetMetrics: PerformanceMetrics = {
      renderTime: 0,
      fps: 60,
      frameDrops: 0,
      syncTime: 0,
      syncLatency: 0,
      syncErrors: 0,
      memoryUsage: getMemoryUsage(),
      memoryPeak: 0,
      memoryLeaks: 0,
      resourceLoadTime: 0,
      cacheHitRate: 100,
      networkRequests: 0,
      inputLatency: 0,
      scrollLatency: 0,
      clickLatency: 0,
      cpuUsage: 0,
      domNodes: getDOMNodeCount(),
      eventListeners: getEventListenerCount()
    };
    
    metricsRef.current = resetMetrics;
    setMetrics(resetMetrics);
    setAlerts([]);
    
    console.log('📊 Performance metrics reset');
  };
  
  // 开始监控
  const startMonitoring = () => {
    if (isMonitoring) return;
    
    setIsMonitoring(true);
    
    // 设置定时更新
    if (autoRefresh) {
      intervalRef.current = setInterval(updateMetrics, 1000);
    }
    
    // 设置性能观察器
    if ('PerformanceObserver' in window) {
      observerRef.current = new PerformanceObserver((list) => {
        const entries = list.getEntries();
        entries.forEach(entry => {
          if (entry.entryType === 'measure') {
            // 处理测量条目
            console.log('📏 Performance measure:', entry.name, entry.duration);
          }
        });
      });
      
      try {
        observerRef.current.observe({ entryTypes: ['measure', 'navigation', 'resource'] });
      } catch (error) {
        console.warn('Performance observer not supported:', error);
      }
    }
    
    console.log('📊 Performance monitoring started');
  };
  
  // 停止监控
  const stopMonitoring = () => {
    if (!isMonitoring) return;
    
    setIsMonitoring(false);
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    
    console.log('📊 Performance monitoring stopped');
  };
  
  // 组件挂载时开始监控
  useEffect(() => {
    if (visible) {
      startMonitoring();
    } else {
      stopMonitoring();
    }
    
    return () => {
      stopMonitoring();
    };
  }, [visible, autoRefresh]);
  
  // 自动刷新切换
  useEffect(() => {
    if (isMonitoring) {
      if (autoRefresh && !intervalRef.current) {
        intervalRef.current = setInterval(updateMetrics, 1000);
      } else if (!autoRefresh && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  }, [autoRefresh, isMonitoring]);
  
  if (!visible) {
    return (
      <Tooltip title="显示性能监控器">
        <Button
          type="text"
          icon={<MonitorOutlined />}
          onClick={() => onVisibilityChange?.(true)}
          className="performance-monitor-toggle"
        />
      </Tooltip>
    );
  }
  
  return (
    <Card
      title={
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MonitorOutlined />
            <span>性能监控器</span>
            <Badge count={alerts.length} size="small" />
          </div>
          <div className="flex items-center gap-2">
            <Switch
              size="small"
              checked={autoRefresh}
              onChange={setAutoRefresh}
              checkedChildren="自动"
              unCheckedChildren="手动"
            />
            <Button
              type="text"
              size="small"
              icon={<ReloadOutlined />}
              onClick={updateMetrics}
              disabled={autoRefresh}
            />
            <Button
              type="text"
              size="small"
              icon={<EyeInvisibleOutlined />}
              onClick={() => onVisibilityChange?.(false)}
            />
          </div>
        </div>
      }
      size="small"
      className={`performance-monitor ${className || ''}`}
      style={{ width: 400, ...style }}
    >
      {/* 核心性能指标 */}
      <Row gutter={[8, 8]} className="mb-4">
        <Col span={12}>
          <Statistic
            title="FPS"
            value={metrics.fps}
            precision={1}
            suffix="fps"
            valueStyle={{ color: getMetricColor('fps', metrics.fps), fontSize: '14px' }}
            prefix={<ThunderboltOutlined />}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title="渲染时间"
            value={metrics.renderTime}
            precision={1}
            suffix="ms"
            valueStyle={{ color: getMetricColor('renderTime', metrics.renderTime), fontSize: '14px' }}
            prefix={<ClockCircleOutlined />}
          />
        </Col>
      </Row>
      
      {/* 内存使用 */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-gray-500">内存使用</span>
          <span className="text-xs">{formatMetricValue('memoryUsage', metrics.memoryUsage)}</span>
        </div>
        <Progress
          percent={(metrics.memoryUsage / (100 * 1024 * 1024)) * 100}
          size="small"
          strokeColor={getMetricColor('memoryUsage', metrics.memoryUsage)}
          showInfo={false}
        />
      </div>
      
      {/* 同步性能 */}
      <Row gutter={[8, 8]} className="mb-4">
        <Col span={12}>
          <Statistic
            title="同步时间"
            value={metrics.syncTime}
            precision={1}
            suffix="ms"
            valueStyle={{ fontSize: '12px' }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title="同步延迟"
            value={metrics.syncLatency}
            precision={1}
            suffix="ms"
            valueStyle={{ fontSize: '12px' }}
          />
        </Col>
      </Row>
      
      {/* 系统指标 */}
      <Row gutter={[8, 8]} className="mb-4">
        <Col span={12}>
          <Statistic
            title="DOM节点"
            value={metrics.domNodes}
            valueStyle={{ fontSize: '12px' }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title="事件监听器"
            value={metrics.eventListeners}
            valueStyle={{ fontSize: '12px' }}
          />
        </Col>
      </Row>
      
      {/* 性能警告 */}
      {alerts.length > 0 && (
        <div className="performance-alerts">
          <div className="text-xs text-gray-500 mb-2 flex items-center gap-1">
            <WarningOutlined />
            <span>性能警告</span>
          </div>
          <div className="max-h-20 overflow-y-auto">
            {alerts.slice(0, 3).map(alert => (
              <div
                key={alert.id}
                className={`text-xs p-1 mb-1 rounded ${
                  alert.type === 'error' ? 'bg-red-50 text-red-600' :
                  alert.type === 'warning' ? 'bg-yellow-50 text-yellow-600' :
                  'bg-blue-50 text-blue-600'
                }`}
              >
                {alert.message}
              </div>
            ))}
          </div>
        </div>
      )}
      
      {/* 操作按钮 */}
      <div className="flex justify-between mt-4">
        <Button
          size="small"
          onClick={resetMetrics}
          type="text"
        >
          重置指标
        </Button>
        <Button
          size="small"
          onClick={() => setAlerts([])}
          type="text"
          disabled={alerts.length === 0}
        >
          清除警告
        </Button>
      </div>
    </Card>
  );
};

export default PerformanceMonitor;
export type { PerformanceMetrics, PerformanceAlert };