/**
 * 虚拟滚动组件 - 优化大文件渲染性能
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { throttle, debounce } from 'lodash';

interface VirtualScrollItem {
  id: string | number;
  height?: number;
  data?: any;
}

interface VirtualScrollProps {
  items: VirtualScrollItem[];
  itemHeight: number | ((index: number, item: VirtualScrollItem) => number);
  containerHeight: number;
  renderItem: (item: VirtualScrollItem, index: number, style: React.CSSProperties) => React.ReactNode;
  overscan?: number;
  scrollToIndex?: number;
  scrollToAlignment?: 'start' | 'center' | 'end' | 'auto';
  onScroll?: (scrollTop: number, scrollLeft: number) => void;
  onItemsRendered?: (startIndex: number, endIndex: number, visibleStartIndex: number, visibleEndIndex: number) => void;
  className?: string;
  style?: React.CSSProperties;
  estimatedItemHeight?: number;
  direction?: 'vertical' | 'horizontal';
  width?: number;
  enableSmoothScrolling?: boolean;
  cacheSize?: number;
}

interface ItemCache {
  height: number;
  offset: number;
}

const VirtualScroll: React.FC<VirtualScrollProps> = ({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  overscan = 5,
  scrollToIndex,
  scrollToAlignment = 'auto',
  onScroll,
  onItemsRendered,
  className,
  style,
  estimatedItemHeight = 50,
  direction = 'vertical',
  width,
  enableSmoothScrolling = true,
  cacheSize = 100
}) => {
  const [scrollTop, setScrollTop] = useState(0);
  const [scrollLeft, setScrollLeft] = useState(0);
  const [isScrolling, setIsScrolling] = useState(false);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const itemCacheRef = useRef<Map<number, ItemCache>>(new Map());
  const scrollTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastScrollTopRef = useRef(0);
  const lastScrollLeftRef = useRef(0);
  const measurementCacheRef = useRef<Map<number, number>>(new Map());
  
  // 获取项目高度
  const getItemHeight = useCallback((index: number): number => {
    if (typeof itemHeight === 'function') {
      const cached = measurementCacheRef.current.get(index);
      if (cached !== undefined) {
        return cached;
      }
      
      const height = itemHeight(index, items[index]);
      measurementCacheRef.current.set(index, height);
      
      // 限制缓存大小
      if (measurementCacheRef.current.size > cacheSize) {
        const firstKey = measurementCacheRef.current.keys().next().value;
        measurementCacheRef.current.delete(firstKey);
      }
      
      return height;
    }
    return itemHeight;
  }, [itemHeight, items, cacheSize]);
  
  // 计算项目偏移量
  const getItemOffset = useCallback((index: number): number => {
    const cached = itemCacheRef.current.get(index);
    if (cached) {
      return cached.offset;
    }
    
    let offset = 0;
    for (let i = 0; i < index; i++) {
      offset += getItemHeight(i);
    }
    
    itemCacheRef.current.set(index, {
      height: getItemHeight(index),
      offset
    });
    
    return offset;
  }, [getItemHeight]);
  
  // 计算总高度
  const getTotalHeight = useCallback((): number => {
    if (items.length === 0) return 0;
    
    let totalHeight = 0;
    for (let i = 0; i < items.length; i++) {
      totalHeight += getItemHeight(i);
    }
    
    return totalHeight;
  }, [items.length, getItemHeight]);
  
  // 查找指定偏移量的项目索引
  const findItemIndex = useCallback((offset: number): number => {
    let low = 0;
    let high = items.length - 1;
    
    while (low <= high) {
      const mid = Math.floor((low + high) / 2);
      const midOffset = getItemOffset(mid);
      const midHeight = getItemHeight(mid);
      
      if (offset >= midOffset && offset < midOffset + midHeight) {
        return mid;
      } else if (offset < midOffset) {
        high = mid - 1;
      } else {
        low = mid + 1;
      }
    }
    
    return Math.min(low, items.length - 1);
  }, [items.length, getItemOffset, getItemHeight]);
  
  // 计算可见范围
  const getVisibleRange = useCallback(() => {
    if (items.length === 0) {
      return {
        startIndex: 0,
        endIndex: 0,
        visibleStartIndex: 0,
        visibleEndIndex: 0
      };
    }
    
    const currentScrollTop = direction === 'vertical' ? scrollTop : scrollLeft;
    const currentContainerSize = direction === 'vertical' ? containerHeight : (width || 0);
    
    const visibleStartIndex = findItemIndex(currentScrollTop);
    const visibleEndIndex = findItemIndex(currentScrollTop + currentContainerSize);
    
    const startIndex = Math.max(0, visibleStartIndex - overscan);
    const endIndex = Math.min(items.length - 1, visibleEndIndex + overscan);
    
    return {
      startIndex,
      endIndex,
      visibleStartIndex,
      visibleEndIndex
    };
  }, [items.length, scrollTop, scrollLeft, containerHeight, width, direction, overscan, findItemIndex]);
  
  // 渲染的项目
  const visibleItems = useMemo(() => {
    const { startIndex, endIndex } = getVisibleRange();
    const rendered: React.ReactNode[] = [];
    
    for (let index = startIndex; index <= endIndex; index++) {
      const item = items[index];
      if (!item) continue;
      
      const offset = getItemOffset(index);
      const height = getItemHeight(index);
      
      const itemStyle: React.CSSProperties = {
        position: 'absolute',
        [direction === 'vertical' ? 'top' : 'left']: offset,
        [direction === 'vertical' ? 'height' : 'width']: height,
        [direction === 'vertical' ? 'width' : 'height']: '100%',
        ...(direction === 'horizontal' && { display: 'inline-block' })
      };
      
      rendered.push(
        <div key={item.id} style={itemStyle}>
          {renderItem(item, index, itemStyle)}
        </div>
      );
    }
    
    return rendered;
  }, [items, getVisibleRange, getItemOffset, getItemHeight, direction, renderItem]);
  
  // 滚动到指定索引
  const scrollToItem = useCallback((index: number, alignment: string = scrollToAlignment) => {
    if (!containerRef.current || index < 0 || index >= items.length) {
      return;
    }
    
    const offset = getItemOffset(index);
    const itemSize = getItemHeight(index);
    const containerSize = direction === 'vertical' ? containerHeight : (width || 0);
    
    let scrollTo = offset;
    
    switch (alignment) {
      case 'start':
        scrollTo = offset;
        break;
      case 'center':
        scrollTo = offset - (containerSize - itemSize) / 2;
        break;
      case 'end':
        scrollTo = offset - containerSize + itemSize;
        break;
      case 'auto':
      default:
        const currentScroll = direction === 'vertical' ? scrollTop : scrollLeft;
        if (offset < currentScroll) {
          scrollTo = offset;
        } else if (offset + itemSize > currentScroll + containerSize) {
          scrollTo = offset - containerSize + itemSize;
        } else {
          return; // 已经在可见范围内
        }
        break;
    }
    
    scrollTo = Math.max(0, Math.min(scrollTo, getTotalHeight() - containerSize));
    
    if (direction === 'vertical') {
      containerRef.current.scrollTop = scrollTo;
    } else {
      containerRef.current.scrollLeft = scrollTo;
    }
  }, [items.length, getItemOffset, getItemHeight, containerHeight, width, direction, scrollTop, scrollLeft, scrollToAlignment, getTotalHeight]);
  
  // 节流的滚动处理
  const throttledScrollHandler = useCallback(
    throttle((scrollTop: number, scrollLeft: number) => {
      setScrollTop(scrollTop);
      setScrollLeft(scrollLeft);
      onScroll?.(scrollTop, scrollLeft);
    }, 16), // 60fps
    [onScroll]
  );
  
  // 防抖的滚动结束处理
  const debouncedScrollEndHandler = useCallback(
    debounce(() => {
      setIsScrolling(false);
    }, 150),
    []
  );
  
  // 滚动事件处理
  const handleScroll = useCallback((event: React.UIEvent<HTMLDivElement>) => {
    const { scrollTop: newScrollTop, scrollLeft: newScrollLeft } = event.currentTarget;
    
    // 检查是否真的发生了滚动
    if (newScrollTop !== lastScrollTopRef.current || newScrollLeft !== lastScrollLeftRef.current) {
      lastScrollTopRef.current = newScrollTop;
      lastScrollLeftRef.current = newScrollLeft;
      
      setIsScrolling(true);
      throttledScrollHandler(newScrollTop, newScrollLeft);
      debouncedScrollEndHandler();
      
      // 清除之前的超时
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
      
      // 设置新的超时
      scrollTimeoutRef.current = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
    }
  }, [throttledScrollHandler, debouncedScrollEndHandler]);
  
  // 监听scrollToIndex变化
  useEffect(() => {
    if (scrollToIndex !== undefined && scrollToIndex >= 0 && scrollToIndex < items.length) {
      scrollToItem(scrollToIndex, scrollToAlignment);
    }
  }, [scrollToIndex, scrollToAlignment, items.length, scrollToItem]);
  
  // 监听可见项目变化
  useEffect(() => {
    const { startIndex, endIndex, visibleStartIndex, visibleEndIndex } = getVisibleRange();
    onItemsRendered?.(startIndex, endIndex, visibleStartIndex, visibleEndIndex);
  }, [getVisibleRange, onItemsRendered]);
  
  // 清理定时器
  useEffect(() => {
    return () => {
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, []);
  
  // 清理缓存
  useEffect(() => {
    itemCacheRef.current.clear();
    measurementCacheRef.current.clear();
  }, [items]);
  
  const totalSize = getTotalHeight();
  const containerStyle: React.CSSProperties = {
    height: containerHeight,
    width: width || '100%',
    overflow: 'auto',
    position: 'relative',
    ...(enableSmoothScrolling && {
      scrollBehavior: isScrolling ? 'auto' : 'smooth'
    }),
    ...style
  };
  
  const innerStyle: React.CSSProperties = {
    position: 'relative',
    [direction === 'vertical' ? 'height' : 'width']: totalSize,
    [direction === 'vertical' ? 'width' : 'height']: '100%'
  };
  
  return (
    <div
      ref={containerRef}
      className={`virtual-scroll ${className || ''}`}
      style={containerStyle}
      onScroll={handleScroll}
    >
      <div style={innerStyle}>
        {visibleItems}
      </div>
    </div>
  );
};

export default VirtualScroll;
export type { VirtualScrollItem, VirtualScrollProps };