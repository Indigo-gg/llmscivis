<template>
  <v-card variant="outlined" class="retrieval-results-card">
    <v-card-title class="card-title">
      <v-icon class="mr-2">mdi-database-search</v-icon>
      Retrieval Results
    </v-card-title>
    <v-card-text>
      <div v-if="results && results.length > 0" class="results-list">
        <v-list>
          <v-list-item v-for="(result, index) in displayResults" :key="result.id || index" class="result-item">
            <template v-slot:prepend>
              <v-avatar color="primary" size="32">
                {{ index + 1 }}
              </v-avatar>
            </template>
            <v-list-item-title class="result-title">
              {{ result.title || 'Untitled Result' }}
            </v-list-item-title>
            <v-list-item-subtitle class="result-description">
              {{ result.description || 'No description' }}
            </v-list-item-subtitle>
            <template v-slot:append v-if="result.relevance !== undefined">
              <div class="relevance-score">
                <v-progress-circular
                  :model-value="result.relevance * 100"
                  :size="40"
                  :width="4"
                  color="primary"
                >
                  {{ Math.round(result.relevance * 100) }}%
                </v-progress-circular>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </div>
      <div v-else class="empty-state">
        <v-icon size="64" color="grey-lighten-1">mdi-database-search</v-icon>
        <p class="empty-text">No retrieval results</p>
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: 'RetrievalResultsCard',
  props: {
    results: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  computed: {
    displayResults() {
      // Limit to maximum 10 items
      return this.results.slice(0, 10);
    }
  }
}
</script>

<style scoped>
.retrieval-results-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-title {
  font-size: 18px;
  font-weight: 500;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
  flex-shrink: 0;
}

.v-card-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 300px;
}

.results-list {
  overflow-y: auto;
  flex: 1;
}

.result-item {
  border-bottom: 1px solid #f0f0f0;
  padding: 12px 0;
}

.result-item:last-child {
  border-bottom: none;
}

.result-title {
  font-size: 14px;
  font-weight: 500;
  color: #333333;
  margin-bottom: 4px;
}

.result-description {
  font-size: 13px;
  color: #666666;
  line-height: 1.4;
}

.relevance-score {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 40px 20px;
}

.empty-text {
  margin-top: 12px;
  font-size: 16px;
  color: #9e9e9e;
}
</style>
