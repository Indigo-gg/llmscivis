<template>
  <v-card variant="outlined" class="query-expansion-card">
    <v-card-title class="card-title">
      <v-icon class="mr-2">mdi-magnify-expand</v-icon>
      查询拓展结果
    </v-card-title>
    <v-card-text>
      <div v-if="content && content.trim()" class="content-area">
        {{ content }}
      </div>
      <div v-else class="empty-state">
        <v-icon size="64" color="grey-lighten-1">mdi-magnify-expand</v-icon>
        <p class="empty-text">暂无查询拓展信息</p>
      </div>
    </v-card-text>
  </v-card>
</template>

<script>
export default {
  name: 'QueryExpansionCard',
  props: {
    content: {
      type: String,
      required: true,
      default: ''
    }
  }
}
</script>

<style scoped>
.query-expansion-card {
  height: 100%;
}

.card-title {
  font-size: 18px;
  font-weight: 500;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.content-area {
  text-align: left;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 200px;
  overflow-y: auto;
  color: #333333;
  line-height: 1.6;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  min-height: 150px;
}

.empty-text {
  margin-top: 12px;
  font-size: 16px;
  color: #9e9e9e;
}
</style>
