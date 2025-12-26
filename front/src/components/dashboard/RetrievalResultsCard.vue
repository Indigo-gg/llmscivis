<template>
  <div class="retrieval-results-card">
    <!-- Debug Info -->
    <!-- <div style="padding: 8px; background: #f0f0f0; margin-bottom: 8px; font-size: 11px;">
      Debug: Results count = {{ results ? results.length : 'null' }} | 
      Filtered count = {{ filteredResults ? filteredResults.length : 'null' }}
    </div> -->
    
    <div v-if="filteredResults && filteredResults.length > 0" class="results-list">
      <div 
        v-for="(result, index) in filteredResults" 
        :key="result.id || index" 
        class="corpus-item"
        :class="{ 'corpus-item--rejected': isRejected(index) }"
      >
        <!-- Header with title and actions -->
        <div class="corpus-header">
          <div class="corpus-title-wrapper">
            <v-icon size="18" color="primary" class="corpus-icon">mdi-code-braces</v-icon>
            <h4 class="corpus-title" :title="getDisplayTitle(result)">
              {{ getDisplayTitle(result) }}
            </h4>
          </div>
          <v-btn
            icon="mdi-close-circle"
            size="x-small"
            variant="text"
            color="error"
            @click="rejectCorpus(index)"
            class="reject-btn"
            title="Reject this corpus"
          ></v-btn>
        </div>

        <!-- Content wrapper for thumbnail and description -->
        <div class="corpus-content">
          <!-- Thumbnail image -->
          <div v-if="result.thumbnail_url && getThumbnailSrc(result)" class="corpus-thumbnail-wrapper">
            <img 
              :src="getThumbnailSrc(result)" 
              :alt="getDisplayTitle(result)"
              class="corpus-thumbnail"
              @error="handleImageError($event, index)"
            />
          </div>
          
          <!-- Description text section -->
          <div class="corpus-text-section">
            <p class="corpus-description" :title="result.description || 'No description'">
              {{ result.description || 'No description available' }}
            </p>
          </div>
        </div>

        <!-- Footer with matched keywords -->
        <div class="corpus-footer">
          <div v-if="result.matched_keywords && result.matched_keywords.length > 0" class="matched-keywords">
            <v-icon size="12" color="grey">mdi-tag-multiple</v-icon>
            <span class="keywords-text">
              {{ result.matched_keywords.slice(0, 3).join(', ') }}
              <span v-if="result.matched_keywords.length > 3">...</span>
            </span>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="empty-state">
      <v-icon size="48" color="grey-lighten-1">mdi-database-search</v-icon>
      <p class="empty-text">No retrieval results</p>
      <p class="empty-hint">Please perform retrieval first</p>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue';
import axios from 'axios';

export default {
  name: 'RetrievalResultsCard',
  props: {
    results: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  emits: ['update:results', 'reject'],
  setup(props, { emit }) {
    const rejectedIndices = ref(new Set());
    const imageErrors = ref(new Set());
    const imageCache = ref(new Map()); // 缓存已加载的图片
    let isUnmounted = false; // 跟踪组件是否已卸载
    let loadingAbortController = null; // 用于取消正在进行的加载
    
    // 异步加载所有缩略图（并行加载，有错误处理）
    const loadAllThumbnails = async (results, signal) => {
      try {
        const loadPromises = results
          .filter(result => result.thumbnail_url && !imageCache.value.has(result.thumbnail_url))
          .map(result => loadThumbnail(result.thumbnail_url, signal));
        
        // 使用 allSettled 避免单个失败影响其他
        await Promise.allSettled(loadPromises);
      } catch (error) {
        if (error.name !== 'AbortError') {
          console.error('Error loading thumbnails:', error);
        }
      }
    };
    
    // Load thumbnail from backend
    const loadThumbnail = async (thumbnailUrl, signal) => {
      if (isUnmounted) return;
      if (signal?.aborted) return;
      
      try {
        // 提取路径部分（移除 /get_image/ 前缀）
        const imagePath = thumbnailUrl.replace(/^\/get_image\//, '');
        
        // 请求后端获取 base64 图片
        const response = await axios.get(`http://127.0.0.1:5001/get_image/${imagePath}`, {
          signal: signal,
          timeout: 10000 // 10秒超时
        });
        
        if (isUnmounted) return;
        
        if (response.data && response.data.success) {
          // 缓存 base64 图片数据
          imageCache.value.set(thumbnailUrl, response.data.image_url);
        }
      } catch (error) {
        if (error.name === 'AbortError' || error.name === 'CanceledError') {
          // 请求被取消，正常情况
          return;
        }
        console.error('Failed to load thumbnail:', thumbnailUrl, error);
        imageCache.value.set(thumbnailUrl, null); // 标记为加载失败
      }
    };
    
    // Load images when results change - 使用同步 watcher 调用异步函数
    watch(() => props.results, (newResults) => {
      if (!newResults || newResults.length === 0) return;
      if (isUnmounted) return;
      
      // 取消之前的加载
      if (loadingAbortController) {
        loadingAbortController.abort();
      }
      loadingAbortController = new AbortController();
      
      // 异步加载缩略图（不阻塞 watcher）
      loadAllThumbnails(newResults, loadingAbortController.signal);
    }, { immediate: true });
    
    // Get cached image URL
    const getThumbnailSrc = (result) => {
      if (!result.thumbnail_url) return '';
      return imageCache.value.get(result.thumbnail_url) || '';
    };
    
    // Handle image load errors
    const handleImageError = (event, index) => {
      imageErrors.value.add(index);
      console.error('Image load error for index:', index);
    };

    // Filtered results excluding rejected items
    const filteredResults = computed(() => {
      return props.results.filter((_, index) => !rejectedIndices.value.has(index));
    });

    // Check if an item is rejected
    const isRejected = (index) => {
      return rejectedIndices.value.has(index);
    };

    // Get display title - prefer title over file_path
    const getDisplayTitle = (result) => {
      if (result.title && !result.title.includes('\\') && !result.title.includes('/')) {
        return result.title;
      }
      // Extract meaningful name from file_path
      const path = result.title || result.file_path || '';
      const parts = path.split(/[\\/]/);
      // Find the most meaningful part (usually the folder name before code.html)
      for (let i = parts.length - 2; i >= 0; i--) {
        if (parts[i] && parts[i] !== 'code.html' && !parts[i].includes('.')) {
          return parts[i];
        }
      }
      return parts[parts.length - 1] || 'Untitled';
    };

    // Get relevance percentage (already normalized 0-1)
    const getRelevancePercent = (relevance) => {
      if (relevance === undefined || relevance === null) return 0;
      // Relevance should already be 0-1 from backend
      return Math.round(Math.min(relevance, 1) * 100);
    };

    // Get relevance class for styling
    const getRelevanceClass = (relevance) => {
      const percent = getRelevancePercent(relevance);
      if (percent >= 80) return 'relevance--high';
      if (percent >= 50) return 'relevance--medium';
      return 'relevance--low';
    };

    // Reject a corpus item
    const rejectCorpus = (index) => {
      rejectedIndices.value.add(index);
      // Find the original index in props.results
      const originalItem = props.results[index];
      // Emit reject event with item details
      emit('reject', { index, item: originalItem });
      // Emit updated results (excluding rejected)
      emit('update:results', filteredResults.value);
    };

    // Reset when results change
    watch(() => props.results, () => {
      rejectedIndices.value.clear();
    });

    // 组件卸载时清理
    onBeforeUnmount(() => {
      isUnmounted = true;
      if (loadingAbortController) {
        loadingAbortController.abort();
        loadingAbortController = null;
      }
    });

    return {
      filteredResults,
      isRejected,
      getDisplayTitle,
      getRelevancePercent,
      getRelevanceClass,
      rejectCorpus,
      handleImageError,
      getThumbnailSrc
    };
  }
}
</script>

<style scoped>
.retrieval-results-card {
  width: 100%;
  height: 80vh;
  overflow-y: scroll;
  padding: 4px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Corpus Item Card */
.corpus-item {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: white;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  min-height: auto;
}

.corpus-item:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  border-color: #1976d2;
}

.corpus-item--rejected {
  opacity: 0.5;
  pointer-events: none;
}

/* Header */
.corpus-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.corpus-title-wrapper {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.corpus-icon {
  flex-shrink: 0;
}

.corpus-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.4;
}

.reject-btn {
  flex-shrink: 0;
  opacity: 0;
  transition: opacity 0.2s;
  margin: -4px -4px 0 0;
}

.corpus-item:hover .reject-btn {
  opacity: 1;
}

/* Content wrapper */
.corpus-content {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

/* Thumbnail */
.corpus-thumbnail-wrapper {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 6px;
  overflow: hidden;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e0e0e0;
}

.corpus-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Text section */
.corpus-text-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

/* Description */
.corpus-description {
  font-size: 12px;
  font-weight: 600;
  color: #333;
  line-height: 1.6;
  margin: 0;
  text-align: left;
  white-space: normal;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

/* Modules */
.corpus-modules {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.module-tag {
  display: inline-block;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 400;
  color: #7fa3d1;
  background: #f0f5ff;
  border-radius: 4px;
  white-space: normal;
  word-wrap: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
  opacity: 0.7;
}

/* Footer */
.corpus-footer {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: auto;
  padding-top: 4px;
  border-top: 1px solid #f0f0f0;
}

.relevance-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.relevance-label {
  font-size: 10px;
  color: #888;
  white-space: nowrap;
  flex-shrink: 0;
  width: 40px;
}

.relevance-bar-wrapper {
  flex: 1;
  height: 4px;
  background: #f0f0f0;
  border-radius: 2px;
  overflow: hidden;
}

.relevance-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.relevance-bar-fill.relevance--high {
  background: linear-gradient(90deg, #4caf50, #66bb6a);
}

.relevance-bar-fill.relevance--medium {
  background: linear-gradient(90deg, #ff9800, #ffb74d);
}

.relevance-bar-fill.relevance--low {
  background: linear-gradient(90deg, #f44336, #ef5350);
}

.relevance-value {
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  flex-shrink: 0;
  min-width: 32px;
  text-align: right;
}

.relevance-value.relevance--high {
  color: #4caf50;
}

.relevance-value.relevance--medium {
  color: #ff9800;
}

.relevance-value.relevance--low {
  color: #f44336;
}

/* Matched Keywords */
.matched-keywords {
  display: flex;
  align-items: center;
  gap: 4px;
}

.keywords-text {
  font-size: 10px;
  color: #888;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px 16px;
  min-height: 150px;
}

.empty-text {
  margin-top: 12px;
  font-size: 14px;
  color: #888;
  font-weight: 500;
}

.empty-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #aaa;
}

/* Scrollbar */
.retrieval-results-card::-webkit-scrollbar {
  width: 4px;
}

.retrieval-results-card::-webkit-scrollbar-track {
  background: transparent;
}

.retrieval-results-card::-webkit-scrollbar-thumb {
  background: #ddd;
  border-radius: 2px;
}

.retrieval-results-card::-webkit-scrollbar-thumb:hover {
  background: #bbb;
}
</style>
