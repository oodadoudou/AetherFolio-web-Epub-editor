/**
 * 防抖函数类型定义
 */
type DebouncedFunction<T extends (...args: any[]) => any> = {
  (...args: Parameters<T>): void;
  cancel: () => void;
  flush: () => void;
  pending: () => boolean;
};

/**
 * 防抖函数实现
 * @param func 要防抖的函数
 * @param delay 延迟时间（毫秒）
 * @param immediate 是否立即执行第一次调用
 * @returns 防抖后的函数
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number,
  immediate: boolean = false
): DebouncedFunction<T> {
  let timeoutId: NodeJS.Timeout | null = null;
  let lastArgs: Parameters<T> | null = null;
  let lastThis: any = null;
  let result: ReturnType<T>;

  const debounced = function (this: any, ...args: Parameters<T>) {
    lastArgs = args;
    lastThis = this;

    const callNow = immediate && !timeoutId;

    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      timeoutId = null;
      if (!immediate) {
        result = func.apply(lastThis, lastArgs!);
      }
    }, delay);

    if (callNow) {
      result = func.apply(this, args);
    }

    return result;
  };

  // 取消防抖
  debounced.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    lastArgs = null;
    lastThis = null;
  };

  // 立即执行
  debounced.flush = () => {
    if (timeoutId && lastArgs) {
      clearTimeout(timeoutId);
      timeoutId = null;
      result = func.apply(lastThis, lastArgs);
      lastArgs = null;
      lastThis = null;
    }
  };

  // 检查是否有待执行的调用
  debounced.pending = () => {
    return timeoutId !== null;
  };

  return debounced as DebouncedFunction<T>;
}

/**
 * 节流函数实现
 * @param func 要节流的函数
 * @param delay 节流间隔（毫秒）
 * @param options 选项
 * @returns 节流后的函数
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  delay: number,
  options: {
    leading?: boolean;
    trailing?: boolean;
  } = {}
): DebouncedFunction<T> {
  const { leading = true, trailing = true } = options;
  let timeoutId: NodeJS.Timeout | null = null;
  let lastExecTime = 0;
  let lastArgs: Parameters<T> | null = null;
  let lastThis: any = null;
  let result: ReturnType<T>;

  const throttled = function (this: any, ...args: Parameters<T>) {
    const now = Date.now();
    lastArgs = args;
    lastThis = this;

    const timeSinceLastExec = now - lastExecTime;

    const execute = () => {
      lastExecTime = Date.now();
      result = func.apply(lastThis, lastArgs!);
      lastArgs = null;
      lastThis = null;
    };

    if (timeSinceLastExec >= delay) {
      if (leading) {
        execute();
      } else {
        lastExecTime = now;
      }
    } else if (trailing && !timeoutId) {
      timeoutId = setTimeout(() => {
        timeoutId = null;
        if (trailing && lastArgs) {
          execute();
        }
      }, delay - timeSinceLastExec);
    }

    return result;
  };

  throttled.cancel = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
      timeoutId = null;
    }
    lastArgs = null;
    lastThis = null;
    lastExecTime = 0;
  };

  throttled.flush = () => {
    if (timeoutId && lastArgs) {
      clearTimeout(timeoutId);
      timeoutId = null;
      result = func.apply(lastThis, lastArgs);
      lastArgs = null;
      lastThis = null;
    }
  };

  throttled.pending = () => {
    return timeoutId !== null;
  };

  return throttled as DebouncedFunction<T>;
}

/**
 * 创建一个可取消的延迟执行函数
 * @param func 要延迟执行的函数
 * @param delay 延迟时间（毫秒）
 * @returns 包含执行和取消方法的对象
 */
export function createDelayedExecution<T extends (...args: any[]) => any>(
  func: T,
  delay: number
) {
  let timeoutId: NodeJS.Timeout | null = null;

  return {
    execute: (...args: Parameters<T>) => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      
      return new Promise<ReturnType<T>>((resolve) => {
        timeoutId = setTimeout(() => {
          timeoutId = null;
          const result = func(...args);
          resolve(result);
        }, delay);
      });
    },
    
    cancel: () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
    },
    
    pending: () => timeoutId !== null
  };
}

/**
 * 批量处理函数，将多个调用合并为一次执行
 * @param func 要批量处理的函数
 * @param delay 批量延迟时间（毫秒）
 * @param maxBatchSize 最大批量大小
 * @returns 批量处理函数
 */
export function createBatchProcessor<T, R>(
  func: (items: T[]) => R,
  delay: number = 100,
  maxBatchSize: number = 100
) {
  let batch: T[] = [];
  let timeoutId: NodeJS.Timeout | null = null;
  let resolvers: Array<(result: R) => void> = [];
  let rejecters: Array<(error: any) => void> = [];

  const processBatch = async () => {
    if (batch.length === 0) return;

    const currentBatch = [...batch];
    const currentResolvers = [...resolvers];
    const currentRejecters = [...rejecters];

    // 清空当前批次
    batch = [];
    resolvers = [];
    rejecters = [];
    timeoutId = null;

    try {
      const result = await func(currentBatch);
      currentResolvers.forEach(resolve => resolve(result));
    } catch (error) {
      currentRejecters.forEach(reject => reject(error));
    }
  };

  const scheduleProcessing = () => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    
    timeoutId = setTimeout(processBatch, delay);
  };

  return {
    add: (item: T): Promise<R> => {
      return new Promise<R>((resolve, reject) => {
        batch.push(item);
        resolvers.push(resolve);
        rejecters.push(reject);

        // 如果达到最大批量大小，立即处理
        if (batch.length >= maxBatchSize) {
          if (timeoutId) {
            clearTimeout(timeoutId);
          }
          processBatch();
        } else {
          scheduleProcessing();
        }
      });
    },

    flush: () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
      return processBatch();
    },

    cancel: () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      
      // 拒绝所有待处理的Promise
      rejecters.forEach(reject => reject(new Error('Batch processing cancelled')));
      
      batch = [];
      resolvers = [];
      rejecters = [];
    },

    pending: () => batch.length > 0,
    size: () => batch.length
  };
}

export default debounce;