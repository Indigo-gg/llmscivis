<template>
  <v-card variant="outlined" class="evaluation-score-card" :color="cardColor">
    <v-card-title class="card-title">
      <v-icon class="mr-2">mdi-star</v-icon>
      评估分数
    </v-card-title>
    <v-card-text>
      <div v-if="hasScore" class="score-display">
        <div class="score-number" :style="{ color: scoreColor }">
          {{ displayScore }}
        </div>
        <v-rating
          :model-value="ratingValue"
          readonly
          :length="5"
          :size="32"
          color="yellow-darken-2"
          class="rating-stars"
        ></v-rating>
        <div class="score-level" :style="{ color: scoreColor }">
          {{ scoreLevel }}
        </div>
      </div>
      <div v-else class="empty-state">
        <v-icon size="64" color="grey-lighten-1">mdi-star-outline</v-icon>
        <p class="empty-text">暂无评估分数</p>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-btn
        variant="tonal"
        color="primary"
        @click="$emit('trigger-evaluation')"
        :loading="isLoading"
        block
      >
        <v-icon left>mdi-play-circle-outline</v-icon>
        开始评估
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  name: 'EvaluationScoreCard',
  props: {
    score: {
      type: [String, Number],
      required: false,
      default: ''
    },
    evaluation: {
      type: String,
      required: false,
      default: ''
    },
    isLoading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['trigger-evaluation'],
  computed: {
    hasScore() {
      return this.score !== '' && this.score !== null && this.score !== undefined;
    },
    displayScore() {
      if (!this.hasScore) return '0';
      const numScore = typeof this.score === 'string' ? parseFloat(this.score) : this.score;
      return isNaN(numScore) ? '0' : numScore.toFixed(1);
    },
    numericScore() {
      const num = parseFloat(this.displayScore);
      return isNaN(num) ? 0 : num;
    },
    scoreColor() {
      if (this.numericScore >= 81) return '#4caf50'; // 绿色
      if (this.numericScore >= 61) return '#ffc107'; // 黄色
      return '#f44336'; // 红色
    },
    cardColor() {
      if (!this.hasScore) return '';
      if (this.numericScore >= 81) return 'green-lighten-5';
      if (this.numericScore >= 61) return 'yellow-lighten-5';
      return 'red-lighten-5';
    },
    scoreLevel() {
      if (this.numericScore >= 90) return '优秀';
      if (this.numericScore >= 81) return '良好';
      if (this.numericScore >= 61) return '及格';
      return '不及格';
    },
    ratingValue() {
      // 将分数转换为5星评分
      return (this.numericScore / 100) * 5;
    }
  }
}
</script>

<style scoped>
.evaluation-score-card {
  height: 100%;
  transition: background-color 0.3s ease;
}

.card-title {
  font-size: 18px;
  font-weight: 500;
  padding: 16px;
  border-bottom: 1px solid #e0e0e0;
}

.score-display {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.score-number {
  font-size: 48px;
  font-weight: 700;
  line-height: 1;
  margin-bottom: 16px;
}

.rating-stars {
  margin-bottom: 12px;
}

.score-level {
  font-size: 18px;
  font-weight: 500;
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
