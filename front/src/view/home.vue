<template>

  <div class="home">
    <div class="head">
      <div class="title">
        {{ title }}
      </div>
      <div class="setting">
        <div class="showVis">
          <v-switch v-model="isShowVis" hide-details inset :label="isShowVis ? 'Visible' : 'Hidden'"
            @change="handleVisibilityChange"></v-switch>
        </div>
      </div>
    </div>
    <!-- Dashboard 区域 -->
    <div class="dashboard">
      <v-container fluid>
        <v-row>
          <v-col cols="12" md="4">
            <QueryExpansionCard :content="currentCase.queryExpansion" />
          </v-col>
          <v-col cols="12" md="4">
            <RetrievalResultsCard :results="currentCase.retrievalResults" />
          </v-col>
          <v-col cols="12" md="4">
            <EvaluationScoreCard 
              :score="currentCase.score" 
              :evaluation="currentCase.evaluatorEvaluation"
              :is-loading="isEvaluating"
              @trigger-evaluation="triggerEvaluation"
            />
          </v-col>
        </v-row>
      </v-container>
    </div>
    <div class="container">
      <div class="left">

        <div class="preview">
          <edit class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.generatedCode"
            @console-output="handleConsoleOutput" ref="generatedPreview">
            <v-btn v-if="isShowVis" :icon="isFullScreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'" size="small"
              variant="text" @click="toggleFullScreen('generated')" class="fullscreen-btn"></v-btn>
          </edit>
          <preview class="scrollable" :is-show-vis="isShowVis" :htmlContent="currentCase.groundTruth"
            ref="truthPreview">
            <template #actions>
              <v-btn v-if="isShowVis" :icon="isFullScreen ? 'mdi-fullscreen-exit' : 'mdi-fullscreen'" size="small"
                variant="text" @click="toggleFullScreen('truth')" class="fullscreen-btn"></v-btn>
            </template>
          </preview>
        </div>
        <!-- 在输出组件部分添加导出按钮 -->
        <div class="output">
          <div class="output-container">
            <Output 
              :console-output="currentCase.consoleOutput" 
              :evaluator-output="currentCase.evaluatorEvaluation"
              @export-results="exportResults"
            >
            </Output>
          </div>
        </div>
      </div>
      <div class="right">
        <config :case-list="caseList" @end="handleSeGenEnd" @getNewCase="setCurrentCase">
        </config>
      </div>
    </div>

    <v-snackbar v-model="info.snackbar" :timeout="info.timeout">
      {{ info.message }}

      <template v-slot:actions>
        <v-btn color="blue" variant="text" @click="info.snackbar = false">
          Close
        </v-btn>
      </template>
    </v-snackbar>

  </div>

</template>


<script>
import preview from "@/components/preview/index.vue";
import edit from "@/components/edit/index.vue";
import config from "@/components/config/index.vue";
import output from "@/components/output/index.vue"
import QueryExpansionCard from "@/components/dashboard/QueryExpansionCard.vue";
import RetrievalResultsCard from "@/components/dashboard/RetrievalResultsCard.vue";
import EvaluationScoreCard from "@/components/dashboard/EvaluationScoreCard.vue";
import axios from "axios";
import { nextTick, onMounted, reactive, ref } from "vue";
import { getAllCase, getEvalResult, generateCode } from "@/api/api.js";
import { appConfig } from "@/view/config.js";
import html2canvas from 'html2canvas';  // 需要安装这个包
import { ExportUtils } from '@/utils/export';
import { useRouter } from 'vue-router'; // 导入useRouter

export default {
  name: "home",
  components: {
    preview,
    config,
    edit,
    Output: output,
    QueryExpansionCard,
    RetrievalResultsCard,
    EvaluationScoreCard
  },
  setup() {
    const router = useRouter(); // 使用router
    const caseList = ref([])
    const info = reactive({
      message: '',
      timeout: 3000,
      snackbar: false
    })
    let isShowVis = ref(false)

    const isEvaluating = ref(false); // For loading state of the new button

    const isExporting = ref(false);
    const currentCase = reactive({
      evalId: 0,
      prompt: '',
      // groundTruth: appConfig.testCode,
      groundTruth: 'Ground Truth:',
      // generatedCode: appConfig.testGeneratedCode,
      generatedCode: 'Generated Code:',
      evaluatorPrompt: appConfig.evaluator_prompt,
      generator: '',
      evaluator: '',
      evaluatorEvaluation: '',
      consoleOutput: [],
      workflow: {
        inquiryExpansion: false,
        rag: false,
      },
      evalUser: appConfig.eval_user,
      score: '',
      manualEvaluation: [],
      options: '',
      queryExpansion: '',
      retrievalResults: []

    })
    const resetCurrentCase = (obj) => {
      currentCase.evalId = obj['eval_id']
      currentCase.score = obj['score']
      currentCase.evalId = obj['eval_id']
      currentCase.generatedCode = obj['generated_code']
      currentCase.manualEvaluation = obj['manual_evaluation']
      currentCase.options = obj['options']
      currentCase.evaluatorEvaluation = obj['evaluator_evaluation']
    }


    const handleSeGenEnd = async (res) => {
      try {
        currentCase.consoleOutput = []
        
        // 处理查询拓展数据
        if (res.analysis) {
          currentCase.queryExpansion = res.analysis;
        } else {
          currentCase.queryExpansion = '';
        }
        
        // 处理检索结果数据
        if (res.retrieval_results && Array.isArray(res.retrieval_results)) {
          currentCase.retrievalResults = res.retrieval_results;
        } else {
          currentCase.retrievalResults = [];
        }
        
        resetCurrentCase(res)
        isShowVis.value = true;

        // 等待预览组件渲染完成
        await nextTick();

        // 额外等待一段时间确保 VTK.js 初始化完成
        await new Promise(resolve => setTimeout(resolve, 1000));

        //启动自动评估
        setTimeout(() => {
          triggerEvaluation();
        }, 1000);
      } catch (error) {
        console.error('处理生成结果时出错:', error);
        info.message = '处理生成结果时出错';
        info.snackbar = true;
      }
    }
    const setCurrentCase = (caseItem) => {
      currentCase.prompt = caseItem.prompt
      currentCase.groundTruth = caseItem.groundTruth
      currentCase.generator = caseItem.generator
      currentCase.evaluator = caseItem.evaluator
      currentCase.evalUser = caseItem.evalUser
      currentCase.evaluatorPrompt = caseItem.evaluatorPrompt
      currentCase.workflow = caseItem.workflow
      // currentCase.currentGeneratedCode=currentGeneratedCode.value
    }


    const handleConsoleOutput = (output) => {

      nextTick(() => {
        // 在这里处理控制台输出
        console.log('handleConsoleOutput', currentCase.consoleOutput)
        currentCase.consoleOutput = output
      })
      // 在这里处理控制台输出
      // console.log('handleConsoleOutput',currentCase.consoleOutput)
      // currentCase.consoleOutput=output
    };
    const init = () => {
      getAllCase().then(res => {
        // console.log('caseList',res)
        caseList.value.push(...res.data)
      })
    }
    const handleVisibilityChange = (value) => {
      console.log("Visibility changed:", value.target.checked);
      isShowVis.value = value.target.checked
      // 在这里可以添加其他逻辑，例如更新组件显示状态
    };
    onMounted(() => {
      init()
    })
    const isFullScreen = ref(false);
    const generatedPreview = ref(null);
    const truthPreview = ref(null);

    const toggleFullScreen = async (type) => {
      const container = type === 'generated'
        ? generatedPreview.value.$el
        : truthPreview.value.$el;

      if (!document.fullscreenElement) {
        await container.requestFullscreen();
        isFullScreen.value = true;
      } else {
        await document.exitFullscreen();
        isFullScreen.value = false;
      }
    };
    const exportResults = async () => {
      try {
        isExporting.value = true;

        // 确保预览组件已经渲染完成
        await nextTick();

        // 获取预览组件实例
        const generatedPreviewInstance = generatedPreview.value; // Access .value for ref
        const truthPreviewInstance = truthPreview.value;         // Access .value for ref

        // 确保子组件实例存在
        if (!generatedPreviewInstance || !truthPreviewInstance) {
          throw new Error('无法获取预览组件实例');
        }

        // 直接从子组件实例获取 iframe 元素
        const generatedIframe = generatedPreviewInstance.previewFrame;
        const truthIframe = truthPreviewInstance.previewFrame;

        if (!generatedIframe || !truthIframe) {
          // 如果 iframe 元素没有找到，抛出更具体的错误
          throw new Error('无法获取预览 iframe 元素');
        }


        const result = await ExportUtils.exportResults(
          currentCase,
          {
            generatedPreviewEl: generatedIframe, // 直接传递 iframe 元素
            truthPreviewEl: truthIframe        // 直接传递 iframe 元素
          }
        );

        info.message = result.message;
        info.snackbar = true;
      } catch (error) {
        console.error('导出错误:', error);
        info.message = '导出失败: ' + error.message;
        info.snackbar = true;
      } finally {
        isExporting.value = false;
      }
    };

    const triggerEvaluation = async () => {
      if (!currentCase.generatedCode || currentCase.generatedCode === 'Generated Code:' || currentCase.generatedCode === null || currentCase.generatedCode.trim() === '') {
        info.message = '没有可评估的生成代码';
        info.snackbar = true;
        return;
      }
      isEvaluating.value = true;
      info.message = '正在评估...';
      info.snackbar = true;
      try {
        const evalRes = await getEvalResult(currentCase);
        console.log('evaluation', evalRes.data);
        currentCase.score = evalRes.data['score'];
        currentCase.evaluatorEvaluation = evalRes.data['evaluator_evaluation'];
        info.message = '评估完成';
        info.snackbar = true;
      } catch (error) {
        console.error('评估失败:', error);
        const errorMessage = error.response?.data?.detail || error.response?.data?.error || error.message || '未知错误';
        info.message = '评估失败: ' + errorMessage;
        info.snackbar = true;
      } finally {
        isEvaluating.value = false;
      }
    };


    // 监听全屏变化
    onMounted(() => {
      document.addEventListener('fullscreenchange', () => {
        isFullScreen.value = !!document.fullscreenElement;
      });
    });

    // 在 return 中添加新的属性
    return {
      title: 'Vtkjs Evaluator',
      caseList,
      handleSeGenEnd,
      setCurrentCase,
      currentCase,
      info,
      isShowVis,
      handleVisibilityChange,
      handleConsoleOutput,
      // 添加全屏相关的属性
      isFullScreen,
      generatedPreview,
      truthPreview,
      toggleFullScreen,
      isExporting,
      exportResults,
      triggerEvaluation,
      isEvaluating,
    };
  }
}
</script>

<style scoped>
.home {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  /*align-items: center;*/
}

.head {
  height: 8vh;
  width: 100vw;
  display: flex;
  justify-content: space-between;
  /* 确保两端对齐 */
  align-items: center;
  /* 垂直居中 */
  padding: 10px;
  background-color: #f0f0f0;
}

.dashboard {
  padding: 16px;
  background-color: #fafafa;
  border-bottom: 1px solid #e0e0e0;
}

.container {
  flex: 1;
  display: flex;
  /*justify-content: space-around;*/
  /*flex: 10 2 auto;*/
  padding: 10px;
  overflow: hidden;
}


.left,
.right {
  padding: 10px;
  overflow-y: scroll;
}

.left {
  flex: 10;
}

.right {
  flex: 2;
}

.preview {
  display: flex;
  flex-direction: row;
  justify-content: space-around;
  position: relative;
  /* 添加相对定位 */
}

.scrollable {
  overflow-y: auto;
  max-height: 80vh;
  border: 1px solid #ccc;
  padding: 10px;
  position: relative;
  /* 添加相对定位 */
}

.fullscreen-btn {
  position: absolute !important;
  top: 8px;
  right: 8px;
  z-index: 100;
  background: rgba(255, 255, 255, 0.7) !important;
  backdrop-filter: blur(4px);
}

.title {
  flex: 1;
  text-align: center;
}

.head .setting {
  display: flex;
  gap: 8px;
  align-items: center;
}



.output-container {
  position: relative;
  width: 100%;
}


</style>
