<template>

  <div>

    <div class="list-container">
    <v-list>
      <v-list-item v-for="(item, index) in caseList" class="item" :key="index">
        <v-list-item-content style="text-align: left">
          <v-list-item-title>
            <span class="prompt">
              {{ item.prompt }}
              <v-tooltip activator="parent" location="top">
                <pre>{{ item.prompt }}</pre>
              </v-tooltip>
            </span>
          </v-list-item-title>
<!--          <v-list-item-title><span class="fileName">{{ item.fileName }}</span></v-list-item-title>-->
        </v-list-item-content>
      </v-list-item>
    </v-list>
  </div>
  <div class="upload">
    <v-dialog v-model="showDialog" max-width="1200px">
      <template v-slot:activator></template>
      <v-card>
        <v-card-title>create new case</v-card-title>
       <v-card-item>
         <div class="content">
          <div class="left" style="min-width: 25%">
            <v-treeview
              :items="treeData"
              item-key="path"
              item-text="name"
              density="compact"
              activatable
              return-object
              open-on-click
              @update:activated="handleActiveChange">
              <template v-slot:prepend="{ item }">
              
                <v-icon v-if="item.type === 'file'">mdi-file-document-outline</v-icon>
                <v-icon v-else>mdi-folder</v-icon>
              </template>
              <template v-slot:title="{ item }">
                {{ item.name }}
              </template>
            </v-treeview>
          </div>
           <div class="middle" style="min-width: 40%">
             <div class="input">
               <v-text-field label="prompt" v-model="newCase.prompt"></v-text-field>
             </div>
             <v-textarea
                 v-model="newCase.groundTruth"
                 outlined
                 placeholder="Please paste the ground truth here. "
                 rows="15"
             ></v-textarea>
           </div>
           <div class="right" style="min-width: 25%">
              <div class="generator">
                <v-select
                    v-model="newCase.generator"
                    :items="models"
                    label="generator"
                    outlined
                ></v-select>
              </div>
             <div class="evaluator">
               <v-select
                   v-model="newCase.evaluator"
                   :items="models"
                   label="evaluator"
                   outlined
               ></v-select>
             </div>
             <div class="workflow">
               <div class="workflow-item">
                 <v-checkbox v-model="inquiryExpansionSelected"
                             :label="'Inquiry expansion'"
                             prepend-icon="mdi-magnify-expand"
                             @change="updateWorkflow('inquiryExpansion')"
                 ></v-checkbox>
                 <v-checkbox v-model="ragSelected"
                             :label="'RAG'"
                             prepend-icon="mdi-database"
                             @change="updateWorkflow('rag')"
                 ></v-checkbox>
                 <v-checkbox v-model="iterativeLoopSelected"
                             :label="'Iterative loop'"
                             prepend-icon="mdi-reload"
                             @change="updateWorkflow('iterativeLoop')"
                 ></v-checkbox>
               </div>
             </div>
           </div>

         </div>

        </v-card-item>

        <v-card-actions>
          <v-btn color="blue darken-1" text @click="showDialog = false">cancel</v-btn>
          <!-- 绑定 loading 属性 -->
          <v-btn color="blue darken-1" text @click="handleUpload">start</v-btn>
        </v-card-actions>
      </v-card>
      <div class="workflow">
        <div class="workflow-item">


        </div>
      </div>
    </v-dialog>
    <v-btn icon="mdi-plus" :loading="isLoading" color="blue" @click="showAddDialog">
          <v-icon>mdi-plus</v-icon>
        </v-btn>

  </div>
  <div>
    <v-snackbar
      v-model="info.snackbar"
      :timeout="info.timeout"
  >
    {{ info.message }}

    <template v-slot:actions>
      <div>
        <v-btn
          color="blue"
          variant="text"
          @click="info.snackbar = false"
      >
        Close
      </v-btn>
      </div>
    </template>
  </v-snackbar>

  </div>

  </div>

 
  <!-- 弹窗组件 -->
</template>

<script>
import {onMounted,reactive, ref} from "vue";
import workflow from "@/components/config/workflow.vue";
import {appConfig} from "@/view/config.js";
import {generateCode} from "@/api/api.js";
import { getCaseList } from "../../api/api";
import { VTreeview } from "vuetify/labs/VTreeview";
export default {
  name: "index",
  components: {
    workflow,
    VTreeview,
  },
  props: {
    /***
     * {
     *   "prompt": "...",
     *   "groundTruth": "...",
     * }
     */
    caseList: {
      type: Array,
      required: true
    }
  },
  setup(props, context) {
    let showDialog = ref(false);
    const newCase = ref({
      // prompt: null,
      path:null,
      name:null,
      prompt:appConfig.testDes,
      groundTruth:appConfig.testCode,
      // groundTruth: null,
      // fileName: null,
      evaluatorPrompt: appConfig.evaluator_prompt,
      generatorPrompt:appConfig.generator_prompt,
      generator:null,
      evaluator:null,
      // score:'',
      // evaluatorEvaluation:'',
      errorCount: 0,
      maxIterations: 3,
      workflow:{
        inquiryExpansion:false,
        rag:false,
        iterativeLoop:false,
      },
      evalUser:appConfig.eval_user
    });
    // const emit= defineEmits(['start'])
    let inquiryExpansionSelected = ref(false);
    let ragSelected = ref(false);
    let iterativeLoopSelected = ref(false);

    const info = reactive({
      message: '',
      timeout: 3000,
      snackbar: false
    });

    // 添加 isLoading 状态变量
    const isLoading = ref(false);

    // 定义 treeData 响应式变量
    const treeData = ref([]);

    // 定义获取树结构数据的异步函数
    const fetchTreeData = async () => {
      try {
        const response = await getCaseList();
        // Ensure response.data is an array, otherwise provide an empty array or handle error
        if (Array.isArray(response.data)) {
          // Recursively remove content from file nodes
          // const stripFileContent = (nodes) => {
          //   return nodes.map(node => {
          //     if (node.type === 'file' && node.content) {
          //       const { content, ...rest } = node;
          //       return rest;
          //     }
          //     if (node.children) {
          //       node.children = stripFileContent(node.children);
          //     }
          //     return node;
          //   });
          // };
          // treeData.value = stripFileContent(response.data);
          treeData.value = response.data;
          console.log('Processed treeData.value:', treeData.value);
        } else {
          console.error('Expected response.data to be an array, but got:', response.data);
          treeData.value = []; // Default to empty array to prevent further errors
        }
        // console.log('Processed treeData.value (content stripped):', JSON.stringify(treeData.value, null, 2));
      } catch (error) {
        console.error('Error fetching tree data:', error);
        info.message = '获取用例列表失败';
        info.snackbar = true;
      }
    };

    // 处理树节点激活事件
    const handleActiveChange=(activeNodes)=> {
      console.log('activeNodes',activeNodes);
      // activeNodes is an array containing the selected node object
      if (activeNodes && activeNodes.length > 0) {
        const selectedNode = activeNodes[0];
        const filePath = selectedNode.path;

        // Find the corresponding node in treeData using the path
        const findNodeByPath = (nodes, path) => {
          for (const node of nodes) {
            if (node.path === path) {
              return node;
            }
            if (node.children) {
              const found = findNodeByPath(node.children, path);
              if (found) {
                return found;
              }
            }
          }
          return null;
        };

        const node = findNodeByPath(treeData.value, filePath);

        if (node && node.type === 'file') {
          // Find the parent directory
          const findParent = (nodes, targetNode) => {
            for (const node of nodes) {
              if (node.children) {
                if (node.children.some(child => child.path === targetNode.path)) {
                  return node;
                }
                const found = findParent(node.children, targetNode);
                if (found) {
                  return found;
                }
              }
            }
            return null;
          };

          const parentNode = findParent(treeData.value, node);

          if (parentNode && parentNode.children) {
            let groundTruthContent = '';
            let descriptionContent = '';

            // Look for ground_truth.html and description.txt in the parent directory's children
            for (const child of parentNode.children) {
              if (child.type === 'file') {
                if (child.name === 'ground_truth.html' && child.content) {
                  groundTruthContent = child.content;
                } else if (child.name === 'description.txt' && child.content) {
                  descriptionContent = child.content;
                }
              }
            }

            // If ground_truth.html and description.txt are found, use their content
            if (groundTruthContent || descriptionContent) {
              newCase.value.groundTruth = groundTruthContent;
              newCase.value.prompt = descriptionContent;
              newCase.value.name = node.name;
              newCase.value.path = node.path;
            } else {
              // Fallback: load the clicked file's content and generate prompt
              newCase.value.groundTruth = node.content || '';
              newCase.value.prompt = `Please generate a VTK.js visualization code for the file: ${node.name}`; // Example prompt
              newCase.value.name = node.name;
              newCase.value.path = node.path;
            }
          } else {
            // Fallback if parent not found: load the clicked file's content and generate prompt
            newCase.value.groundTruth = node.content || '';
            newCase.value.prompt = `Please generate a VTK.js visualization code for the file: ${node.name}`; // Example prompt
            newCase.value.name = node.name;
            newCase.value.path = node.path;
          }
        } else {
          // Handle directory clicks or no node found
          newCase.value.groundTruth = '';
          newCase.value.prompt = '';
          newCase.value.name = '';
          newCase.value.path = '';
        }
      }
    }

    const showAddDialog = ()=>{
      console.log('showDialog',showDialog.value);
      if (!showDialog.value)
        showDialog.value = true;
    }
    const handleUpload = () => {
      // 处理上传逻辑
      // 获取需要校验的字段
      const { prompt, groundTruth, generator, evaluator, maxIterations } = newCase.value;
      // 字段校验逻辑
      if (!prompt || prompt.trim() === '') {
        info.message = 'prompt 不能为空';
        info.snackbar = true;
        console.error('prompt 不能为空');
        return;
      }

      if (!maxIterations || maxIterations < 1) {
        info.message = '最大迭代次数必须大于0';
        info.snackbar = true;
        console.error('最大迭代次数必须大于0');
        return;
      }

      if (!groundTruth || groundTruth.trim() === '') {
        info.message = 'groundTruth 不能为空';
        info.snackbar = true;
        console.error('groundTruth 不能为空');
        return;
      }

      if (!generator || generator.trim() === '') {
        info.message = 'generator 不能为空';
        info.snackbar = true;
        console.error('generator 不能为空');
        return;
      }

      if (!evaluator || evaluator.trim() === '') {
        info.message = 'evaluator 不能为空';
        info.snackbar = true;
        console.error('evaluator 不能为空');
        return;
      }

      // 设置加载状态为 true
      isLoading.value = true;

      generateCode(newCase.value).then((res)=>{
        info.message = 'generation end';
        info.snackbar = true;
        context.emit('end', res.data);
      }).catch(error => {
        // 处理错误情况
        info.message = 'generation failed: ' + error.message;
        info.snackbar = true;
        console.error('Generation failed:', error);
      }).finally(() => {
        // 无论成功或失败，都设置加载状态为 false
        isLoading.value = false;
      });

      showDialog.value = false;
      context.emit('getNewCase', newCase.value);
    };

    const updateWorkflow = (type) => {

      switch (type) {

        case 'inquiryExpansion':
          // inquiryExpansionSelected.value = !inquiryExpansionSelected.value;
          if (inquiryExpansionSelected.value) {

            // ragSelected.value = true;
            // iterativeLoopSelected.value = true;
          }
          newCase.value.workflow.inquiryExpansion=inquiryExpansionSelected.value
          console.log('1',newCase.value.workflow);

          break;
        case 'rag':
          // ragSelected.value = !ragSelected.value;
          if (ragSelected.value) {
            // iterativeLoopSelected.value = true;
            inquiryExpansionSelected.value = true;
          }
          newCase.value.workflow.inquiryExpansion=inquiryExpansionSelected.value
          newCase.value.workflow.rag=ragSelected.value
          console.log('2',newCase.value.workflow);
          break;
        case 'iterativeLoop':
          // iterativeLoopSelected.value = !iterativeLoopSelected.value;
          if(iterativeLoopSelected.value){
            inquiryExpansionSelected.value = true;
            ragSelected.value = true;
            // inquiryExpansionSelected=true
          }
          newCase.value.workflow.inquiryExpansion=inquiryExpansionSelected.value
          newCase.value.workflow.rag=ragSelected.value
          newCase.value.workflow.iterativeLoop=iterativeLoopSelected.value
          console.log('3',newCase.value.workflow);
          break;
          default:
            console.log('workflow',newCase.value.workflow);

      }

      //检测workflow的boolean值，并赋给newCase.value.workflow
      // if(inquiryExpansionSelected.value)

    };


    onMounted(()=>{
      // sendCase()
      fetchTreeData(); // 在组件挂载时调用获取数据函数
    })
    // const showDialog = ref(false);
    return {
      newCase,
      showDialog, // 控制弹窗显示的变量
      handleUpload,
      showAddDialog,
      updateWorkflow,
      iterativeLoopSelected,
      inquiryExpansionSelected,
      ragSelected,
      info,
      models:appConfig.models,
      isLoading, // 暴露 isLoading 变量给模板
      treeData, // 暴露 treeData 变量给模板
      handleActiveChange, // 暴露 handleNodeClick 函数给模板
    };

  }
};
</script>

<style scoped>
.list-container {
  height: 70vh;
  overflow-y: scroll;
}
.upload {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 10vh;
  text-align: center;
}
.item {
  border-bottom: 1px solid #e5e5e5;
}
.content{
  display: flex;
  justify-content: space-around;
}
.item:hover {
  background-color: #f5f5f5;
  transform: scale(1.1);
}
.prompt {
  color: #242424;
  font-size: 18px;
  cursor: pointer;
}
.fileName {
  color: #747bff;
  font-size: 18px;
  cursor: pointer;
}
</style>
