<template>
  <div class="retrieval-results-card">
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
            title="驳回此语料"
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

        <!-- Footer with relevance score -->
        <div class="corpus-footer">
          <div class="relevance-indicator">
            <span class="relevance-label">相关度</span>
            <div class="relevance-bar-wrapper">
              <div 
                class="relevance-bar-fill" 
                :style="{ width: getRelevancePercent(result.relevance) + '%' }"
                :class="getRelevanceClass(result.relevance)"
              ></div>
            </div>
            <span class="relevance-value" :class="getRelevanceClass(result.relevance)">
              {{ getRelevancePercent(result.relevance) }}%
            </span>
          </div>
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
      <p class="empty-text">暂无检索结果</p>
      <p class="empty-hint">请先执行检索操作</p>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue';
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
    
    // Load images when results change
    watch(() => props.results, async (newResults) => {
      if (!newResults || newResults.length === 0) return;
      
      // 加载所有缩略图
      for (const result of newResults) {
        if (result.thumbnail_url && !imageCache.value.has(result.thumbnail_url)) {
          await loadThumbnail(result.thumbnail_url);
        }
      }
    }, { immediate: true });
    
    // Load thumbnail from backend
    const loadThumbnail = async (thumbnailUrl) => {
      try {
        // 提取路径部分（移除 /get_image/ 前缀）
        const imagePath = thumbnailUrl.replace(/^\/get_image\//, '');
        
        // 请求后端获取 base64 图片
        const response = await axios.get(`http://127.0.0.1:5001/get_image/${imagePath}`);
        
        if (response.data && response.data.success) {
          // 缓存 base64 图片数据
          imageCache.value.set(thumbnailUrl, response.data.image_url);
        }
      } catch (error) {
        console.error('Failed to load thumbnail:', thumbnailUrl, error);
        imageCache.value.set(thumbnailUrl, null); // 标记为加载失败
      }
    };
    
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
  height: 70vh;
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
