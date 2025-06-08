<template>
    <v-container fluid class="fill-height">
        <v-row class="fill-height">
            <!-- Left Panel: Tree View -->
            <v-col cols="3" class="tree-panel  left-container">
                <v-card class="fill-height">
                    <v-card-title>Exported Cases</v-card-title>
                    <v-card-text class="fill-height scroll-y">
                        <v-treeview :items="treeData" item-key="path" item-text="name" density="compact" activatable
                            return-object open-on-click @update:activated="handleActiveChange">
                            <template v-slot:prepend="{ item }">
                                <v-icon v-if="item.type === 'file'">mdi-file-document-outline</v-icon>
                                <v-icon v-else>mdi-folder</v-icon>
                            </template>
                            <template v-slot:title="{ item }">
                                <span class="tree-item-title scroll-x">{{ item.name }}</span>
                            </template>
                        </v-treeview>
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Right Panel: Code Editors -->
            <v-col cols="9" class="code-editors-panel">
                <v-card class="fill-height d-flex flex-column">
                    <v-card-title>Code Comparison</v-card-title>
                    <v-card-text class="flex-grow-1 d-flex flex-row">
                        <v-col cols="6" class="fill-height d-flex flex-column">
                            <h3>Generated Code</h3>
                            <v-textarea v-model="generatedCode" outlined rows="20" class="flex-grow-1"
                                readonly></v-textarea>
                        </v-col>
                        <v-col cols="6" class="fill-height d-flex flex-column">
                            <h3>Modified Code</h3>
                            <v-textarea v-model="modifiedCode" outlined rows="20" class="flex-grow-1"></v-textarea>
                        </v-col>
                    </v-card-text>
                    <v-card-actions>
                        <v-spacer></v-spacer>
                        <v-btn color="primary" @click="saveModifiedCode">Save Modified Code</v-btn>
                    </v-card-actions>
                </v-card>
            </v-col>
        </v-row>
    </v-container>
</template>

<script>
import { ref, onMounted } from 'vue';
import { getExportedCases, handleExport } from '@/api/api'; // 假设 handleExport 用于保存修改
import { VTreeview } from 'vuetify/labs/VTreeview';

export default {
    name: 'ErrorRecord',
    components: {
        VTreeview,
    },
    setup() {
        const treeData = ref([]);
        const generatedCode = ref('');
        const modifiedCode = ref('');
        const currentCasePath = ref(''); // 用于保存当前选中的案例路径

        // 获取树结构数据的异步函数
        const fetchTreeData = async () => {
            try {
                const response = await getExportedCases();
                if (Array.isArray(response.data)) {
                    treeData.value = response.data;
                    console.log('Fetched treeData:', treeData.value);
                } else {
                    console.error('Expected response.data to be an array, but got:', response.data);
                    treeData.value = [];
                }
            } catch (error) {
                console.error('Error fetching tree data:', error);
                // 可以添加错误提示，例如使用 Vuetify 的 snackbar
            }
        };

        // 处理树节点激活事件
        const handleActiveChange = (activeNodes) => {
            if (activeNodes && activeNodes.length > 0) {
                const selectedNode = activeNodes[0];
                // 只有当点击的是文件节点时才加载内容
                if (selectedNode.type === 'file') {
                    const parentNode = findParentDirectory(treeData.value, selectedNode.path);
                    if (parentNode && parentNode.children) {
                        const generatedFile = parentNode.children.find(child => child.name === 'generated_code.html' && child.type === 'file');
                        const modifiedFile = parentNode.children.find(child => child.name === 'modified_code.html' && child.type === 'file');

                        generatedCode.value = generatedFile ? generatedFile.content || '' : '';
                        modifiedCode.value = modifiedFile ? modifiedFile.content || '' : '';
                        currentCasePath.value = parentNode.path; // 保存父目录路径，用于保存时定位
                    } else {
                        // 如果没有找到父目录，或者父目录没有子文件，则清空内容
                        generatedCode.value = '';
                        modifiedCode.value = '';
                        currentCasePath.value = '';
                    }
                } else {
                    // 如果点击的是目录，则清空内容
                    generatedCode.value = '';
                    modifiedCode.value = '';
                    currentCasePath.value = '';
                }
            }
        };

        // 辅助函数：查找父目录节点
        const findParentDirectory = (nodes, targetPath) => {
            for (const node of nodes) {
                if (node.children) {
                    if (node.children.some(child => child.path === targetPath)) {
                        return node; // 找到父目录
                    }
                    const found = findParentDirectory(node.children, targetPath);
                    if (found) {
                        return found;
                    }
                }
            }
            return null;
        };

        // 保存修改后的代码
        const saveModifiedCode = async () => {
            if (!currentCasePath.value) {
                console.warn('No case selected to save.');
                // 可以添加提示，例如“请选择一个案例”
                return;
            }
            try {
                // 假设后端 handleExport 接口可以接收路径和修改后的内容
                await handleExport({
                    casePath: currentCasePath.value,
                    modifiedCode: modifiedCode.value,
                });
                console.log('Modified code saved successfully!');
                // 可以添加成功提示
            } catch (error) {
                console.error('Error saving modified code:', error);
                // 可以添加错误提示
            }
        };

        onMounted(() => {
            fetchTreeData();
        });

        return {
            treeData,
            generatedCode,
            modifiedCode,
            handleActiveChange,
            saveModifiedCode,
        };
    },
};
</script>

<style scoped>
.left-container {
    height: 95vh;
    width: 100%;


}

.scroll-y {
    white-space: nowrap;
    overflow-y: scroll;
    /* 隐藏滚动条，但仍可滚动 */
    scrollbar-width: none;
    /* Firefox */
    -ms-overflow-style: none;
}

.scroll-x {
    white-space: nowrap;
    overflow-x: scroll;
    /* 隐藏滚动条，但仍可滚动 */
    scrollbar-width: none;
    /* Firefox */
    -ms-overflow-style: none;
}

.fill-height {
    height: 100%;
    /* IE and Edge */
}

.tree-panel {
    border-right: 1px solid #e0e0e0;
}

.code-editors-panel {
    display: flex;
    flex-direction: column;
}

.tree-item-title {
    width: 100%;
    white-space: nowrap;
    overflow-x: auto;
    /* 隐藏滚动条，但仍可滚动 */
    scrollbar-width: none;
    /* Firefox */
    -ms-overflow-style: none;
    /* IE and Edge */
}

.tree-item-title::-webkit-scrollbar {
    display: none;
    /* Chrome, Safari, Opera*/
}
</style>