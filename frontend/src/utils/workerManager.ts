/**
 * Web Worker管理器
 * 管理EPUB解析和其他后台任务的Web Workers
 */

import type { WorkerMessage, WorkerResponse, EpubStructure, ParseOptions } from '../workers/epubParserWorker';

// Worker任务状态
type TaskStatus = 'pending' | 'running' | 'completed' | 'failed';

// Worker任务接口
interface WorkerTask {
  id: string;
  type: string;
  status: TaskStatus;
  progress: number;
  result?: any;
  error?: string;
  startTime: number;
  endTime?: number;
  worker?: Worker;
}

// Worker池配置
interface WorkerPoolConfig {
  maxWorkers: number;
  workerTimeout: number;
  retryAttempts: number;
  enableLogging: boolean;
}

// 任务选项
interface TaskOptions {
  timeout?: number;
  retries?: number;
  priority?: 'low' | 'normal' | 'high';
  onProgress?: (progress: number, message?: string) => void;
}

/**
 * Worker池管理器
 */
class WorkerPool {
  private workers: Worker[] = [];
  private availableWorkers: Worker[] = [];
  private busyWorkers: Set<Worker> = new Set();
  private config: WorkerPoolConfig;
  private workerScript: string;

  constructor(workerScript: string, config: Partial<WorkerPoolConfig> = {}) {
    this.workerScript = workerScript;
    this.config = {
      maxWorkers: config.maxWorkers || Math.max(2, navigator.hardwareConcurrency - 1),
      workerTimeout: config.workerTimeout || 30000,
      retryAttempts: config.retryAttempts || 3,
      enableLogging: config.enableLogging || false
    };

    this.initializeWorkers();
  }

  /**
   * 初始化Worker池
   */
  private initializeWorkers(): void {
    for (let i = 0; i < this.config.maxWorkers; i++) {
      try {
        const worker = new Worker(this.workerScript, { type: 'module' });
        this.workers.push(worker);
        this.availableWorkers.push(worker);
        
        if (this.config.enableLogging) {
          console.log(`Worker ${i + 1} initialized`);
        }
      } catch (error) {
        console.error(`Failed to create worker ${i + 1}:`, error);
      }
    }

    if (this.workers.length === 0) {
      console.warn('No workers could be created');
    }
  }

  /**
   * 获取可用的Worker
   */
  public getAvailableWorker(): Worker | null {
    if (this.availableWorkers.length > 0) {
      const worker = this.availableWorkers.pop()!;
      this.busyWorkers.add(worker);
      return worker;
    }
    return null;
  }

  /**
   * 释放Worker
   */
  public releaseWorker(worker: Worker): void {
    if (this.busyWorkers.has(worker)) {
      this.busyWorkers.delete(worker);
      this.availableWorkers.push(worker);
    }
  }

  /**
   * 获取池状态
   */
  public getStatus(): {
    total: number;
    available: number;
    busy: number;
  } {
    return {
      total: this.workers.length,
      available: this.availableWorkers.length,
      busy: this.busyWorkers.size
    };
  }

  /**
   * 销毁Worker池
   */
  public destroy(): void {
    this.workers.forEach(worker => {
      worker.terminate();
    });
    this.workers = [];
    this.availableWorkers = [];
    this.busyWorkers.clear();

    if (this.config.enableLogging) {
      console.log('Worker pool destroyed');
    }
  }
}

/**
 * Web Worker管理器
 */
export class WorkerManager {
  private static instance: WorkerManager;
  private workerPool: WorkerPool;
  private tasks: Map<string, WorkerTask> = new Map();
  private taskQueue: WorkerTask[] = [];
  private isProcessingQueue: boolean = false;

  private constructor() {
    // 创建EPUB解析Worker池
    this.workerPool = new WorkerPool(
      new URL('../workers/epubParserWorker.ts', import.meta.url).href,
      {
        maxWorkers: 2,
        workerTimeout: 60000,
        retryAttempts: 2,
        enableLogging: true
      }
    );

    // 开始处理任务队列
    this.processTaskQueue();
  }

  /**
   * 获取单例实例
   */
  public static getInstance(): WorkerManager {
    if (!WorkerManager.instance) {
      WorkerManager.instance = new WorkerManager();
    }
    return WorkerManager.instance;
  }

  /**
   * 解析EPUB文件
   */
  public async parseEpub(
    file: File,
    options: ParseOptions = {
      validateStructure: true,
      extractResources: true,
      generateAST: true,
      optimizeContent: false,
      preserveWhitespace: false
    },
    taskOptions: TaskOptions = {}
  ): Promise<EpubStructure> {
    const taskId = this.generateTaskId();
    
    const task: WorkerTask = {
      id: taskId,
      type: 'parse',
      status: 'pending',
      progress: 0,
      startTime: Date.now()
    };

    this.tasks.set(taskId, task);
    this.taskQueue.push(task);

    return new Promise((resolve, reject) => {
      const timeoutId = setTimeout(() => {
        this.cancelTask(taskId);
        reject(new Error('Task timeout'));
      }, taskOptions.timeout || 60000);

      const checkTask = () => {
        const currentTask = this.tasks.get(taskId);
        if (!currentTask) {
          clearTimeout(timeoutId);
          reject(new Error('Task not found'));
          return;
        }

        switch (currentTask.status) {
          case 'completed':
            clearTimeout(timeoutId);
            resolve(currentTask.result);
            this.tasks.delete(taskId);
            break;
          case 'failed':
            clearTimeout(timeoutId);
            reject(new Error(currentTask.error || 'Task failed'));
            this.tasks.delete(taskId);
            break;
          case 'running':
            if (taskOptions.onProgress) {
              taskOptions.onProgress(currentTask.progress);
            }
            setTimeout(checkTask, 100);
            break;
          default:
            setTimeout(checkTask, 100);
        }
      };

      // 开始检查任务状态
      setTimeout(checkTask, 100);

      // 触发队列处理
      this.processTaskQueue();
    });
  }

  /**
   * 验证EPUB文件
   */
  public async validateEpub(
    file: File,
    taskOptions: TaskOptions = {}
  ): Promise<{ valid: boolean; errors: string[] }> {
    try {
      await this.parseEpub(file, {
        validateStructure: true,
        extractResources: false,
        generateAST: false,
        optimizeContent: false,
        preserveWhitespace: false
      }, taskOptions);
      
      return { valid: true, errors: [] };
    } catch (error) {
      return {
        valid: false,
        errors: [error.message]
      };
    }
  }

  /**
   * 提取EPUB资源
   */
  public async extractEpubResources(
    file: File,
    taskOptions: TaskOptions = {}
  ): Promise<{
    images: string[];
    styles: string[];
    fonts: string[];
    scripts: string[];
  }> {
    const result = await this.parseEpub(file, {
      validateStructure: false,
      extractResources: true,
      generateAST: false,
      optimizeContent: false,
      preserveWhitespace: false
    }, taskOptions);

    return result.resources;
  }

  /**
   * 优化EPUB内容
   */
  public async optimizeEpubContent(
    file: File,
    taskOptions: TaskOptions = {}
  ): Promise<EpubStructure> {
    return this.parseEpub(file, {
      validateStructure: false,
      extractResources: true,
      generateAST: true,
      optimizeContent: true,
      preserveWhitespace: false
    }, taskOptions);
  }

  /**
   * 处理任务队列
   */
  private async processTaskQueue(): Promise<void> {
    if (this.isProcessingQueue) {
      return;
    }

    this.isProcessingQueue = true;

    while (this.taskQueue.length > 0) {
      const worker = this.workerPool.getAvailableWorker();
      if (!worker) {
        // 没有可用的Worker，等待一段时间后重试
        await this.sleep(100);
        continue;
      }

      const task = this.taskQueue.shift();
      if (!task) {
        this.workerPool.releaseWorker(worker);
        continue;
      }

      // 执行任务
      this.executeTask(task, worker);
    }

    this.isProcessingQueue = false;
  }

  /**
   * 执行单个任务
   */
  private async executeTask(task: WorkerTask, worker: Worker): Promise<void> {
    task.status = 'running';
    task.worker = worker;

    return new Promise((resolve) => {
      const messageHandler = (event: MessageEvent<WorkerResponse>) => {
        const { id, type, data, error } = event.data;
        
        if (id !== task.id) {
          return;
        }

        switch (type) {
          case 'progress':
            task.progress = data.progress || 0;
            break;
          case 'success':
            task.status = 'completed';
            task.result = data;
            task.endTime = Date.now();
            cleanup();
            resolve();
            break;
          case 'error':
            task.status = 'failed';
            task.error = error || 'Unknown error';
            task.endTime = Date.now();
            cleanup();
            resolve();
            break;
        }
      };

      const errorHandler = (error: ErrorEvent) => {
        task.status = 'failed';
        task.error = error.message;
        task.endTime = Date.now();
        cleanup();
        resolve();
      };

      const cleanup = () => {
        worker.removeEventListener('message', messageHandler);
        worker.removeEventListener('error', errorHandler);
        this.workerPool.releaseWorker(worker);
      };

      // 添加事件监听器
      worker.addEventListener('message', messageHandler);
      worker.addEventListener('error', errorHandler);

      // 发送任务消息
      const message: WorkerMessage = {
        id: task.id,
        type: task.type as any,
        data: this.getTaskData(task)
      };

      worker.postMessage(message);
    });
  }

  /**
   * 获取任务数据
   */
  private getTaskData(task: WorkerTask): any {
    // 这里应该根据任务类型返回相应的数据
    // 由于我们无法直接访问原始文件对象，这里返回占位数据
    return {
      file: null, // 实际实现中需要传递文件数据
      options: {
        validateStructure: true,
        extractResources: true,
        generateAST: true,
        optimizeContent: false,
        preserveWhitespace: false
      }
    };
  }

  /**
   * 取消任务
   */
  public cancelTask(taskId: string): boolean {
    const task = this.tasks.get(taskId);
    if (!task) {
      return false;
    }

    if (task.worker) {
      this.workerPool.releaseWorker(task.worker);
    }

    // 从队列中移除
    const queueIndex = this.taskQueue.findIndex(t => t.id === taskId);
    if (queueIndex !== -1) {
      this.taskQueue.splice(queueIndex, 1);
    }

    task.status = 'failed';
    task.error = 'Task cancelled';
    task.endTime = Date.now();

    return true;
  }

  /**
   * 获取任务状态
   */
  public getTaskStatus(taskId: string): WorkerTask | null {
    return this.tasks.get(taskId) || null;
  }

  /**
   * 获取所有任务
   */
  public getAllTasks(): WorkerTask[] {
    return Array.from(this.tasks.values());
  }

  /**
   * 获取活跃任务
   */
  public getActiveTasks(): WorkerTask[] {
    return Array.from(this.tasks.values()).filter(
      task => task.status === 'running' || task.status === 'pending'
    );
  }

  /**
   * 获取Worker池状态
   */
  public getWorkerPoolStatus(): {
    total: number;
    available: number;
    busy: number;
    queueLength: number;
    activeTasks: number;
  } {
    const poolStatus = this.workerPool.getStatus();
    return {
      ...poolStatus,
      queueLength: this.taskQueue.length,
      activeTasks: this.getActiveTasks().length
    };
  }

  /**
   * 清理已完成的任务
   */
  public cleanupCompletedTasks(): number {
    let cleaned = 0;
    const now = Date.now();
    const maxAge = 5 * 60 * 1000; // 5分钟

    for (const [taskId, task] of this.tasks.entries()) {
      if (
        (task.status === 'completed' || task.status === 'failed') &&
        task.endTime &&
        now - task.endTime > maxAge
      ) {
        this.tasks.delete(taskId);
        cleaned++;
      }
    }

    return cleaned;
  }

  /**
   * 获取性能统计
   */
  public getPerformanceStats(): {
    totalTasks: number;
    completedTasks: number;
    failedTasks: number;
    averageExecutionTime: number;
    successRate: number;
  } {
    const allTasks = Array.from(this.tasks.values());
    const completedTasks = allTasks.filter(task => task.status === 'completed');
    const failedTasks = allTasks.filter(task => task.status === 'failed');
    
    const executionTimes = completedTasks
      .filter(task => task.endTime)
      .map(task => task.endTime! - task.startTime);
    
    const averageExecutionTime = executionTimes.length > 0
      ? executionTimes.reduce((sum, time) => sum + time, 0) / executionTimes.length
      : 0;
    
    const successRate = allTasks.length > 0
      ? (completedTasks.length / allTasks.length) * 100
      : 0;

    return {
      totalTasks: allTasks.length,
      completedTasks: completedTasks.length,
      failedTasks: failedTasks.length,
      averageExecutionTime,
      successRate
    };
  }

  /**
   * 生成任务ID
   */
  private generateTaskId(): string {
    return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 睡眠函数
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 销毁管理器
   */
  public destroy(): void {
    // 取消所有活跃任务
    const activeTasks = this.getActiveTasks();
    activeTasks.forEach(task => this.cancelTask(task.id));

    // 销毁Worker池
    this.workerPool.destroy();

    // 清理任务
    this.tasks.clear();
    this.taskQueue = [];

    console.log('WorkerManager destroyed');
  }
}

// 导出单例实例
export const workerManager = WorkerManager.getInstance();

// 导出类型
export type { WorkerTask, TaskStatus, TaskOptions, WorkerPoolConfig };

// 默认导出
export default WorkerManager;