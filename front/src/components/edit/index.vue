<template>
  <div class="preview-container" :class="{ 'fullscreen': isFullscreen }">
    <!-- Title Bar -->
    <div class="editor-title-bar">
      <div class="title-left">
        <div class="mac-buttons">
          <span class="mac-dot red"></span>
          <span class="mac-dot yellow"></span>
          <span class="mac-dot green"></span>
        </div>
        <h3 class="editor-title">Generated Code</h3>
      </div>
      <div class="title-actions">
        <!-- 插槽用于放置按钮 -->
        <slot name="actions"></slot>
      </div>
    </div>

    <!-- Content Area -->
    <div class="content-wrapper">
      <div v-if="!isShowVis" class="code-area">
        <div v-if="hasContent" class="monaco-wrapper" ref="editorContainer"></div>
        <div v-else class="empty-state">
          <div class="empty-icon-bg">
            <!-- 假设你有 v-icon 组件，如果没有可以用 svg 代替 -->
            <slot name="empty-icon">
               <svg style="width:48px;height:48px;color:#cbd5e1" viewBox="0 0 24 24">
                 <path fill="currentColor" d="M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z" />
               </svg>
            </slot>
          </div>
          <p class="empty-text">Waiting for code generation...</p>
        </div>
      </div>
      
      <div v-else class="preview-area">
        <iframe 
          ref="previewFrame" 
          sandbox="allow-scripts allow-same-origin allow-top-navigation"
          class="preview-iframe"
          src="about:blank" 
          frameBorder="0"
        ></iframe>
      </div>
    </div>
  </div>
</template>

<script>
import { onMounted, nextTick, ref, watch, computed, onBeforeUnmount } from 'vue';
import * as monaco from 'monaco-editor';

export default {
  name: 'ModernEditor',
  emits: ['error', 'console-output', 'update:htmlContent'],
  props: {
    htmlContent: {
      type: String,
      required: true,
    },
    isShowVis: {
      type: Boolean,
      default: false
    },
    // 新增：报错行号 (从1开始)
    errorLine: {
      type: Number,
      default: null
    },
    // 新增：报错具体信息
    errorMessage: {
      type: String,
      default: ''
    }
  },
  setup(props, { emit }) {
    const editorContainer = ref(null);
    const previewFrame = ref(null);
    const isFullscreen = ref(false);
    
    let editor = null;
    let decorationIds = []; // 用于存储高亮的ID，以便清除

    const hasContent = computed(() => {
      return props.htmlContent && 
             props.htmlContent.trim() !== '' && 
             props.htmlContent !== 'Ground Truth:' &&
             props.htmlContent !== 'Generated Code:';
    });

    function initEditor() {
      destroyEditor();
      if (editorContainer.value && hasContent.value) {
        editor = monaco.editor.create(editorContainer.value, {
          value: extractHtmlCode(props.htmlContent),
          language: 'html',
          theme: 'vs-light', // 或者使用 'vs-dark' 配合暗色模式
          automaticLayout: true,
          minimap: { enabled: false },
          fontSize: 14,
          fontFamily: "'Fira Code', 'JetBrains Mono', 'Consolas', monospace", // 更现代的字体
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          roundedSelection: true,
          readOnly: false,
          cursorStyle: 'line',
          wordWrap: 'on', // 建议开启换行
          padding: { top: 16, bottom: 16 }, // 增加内边距
          renderLineHighlight: 'all',
          smoothScrolling: true,
          scrollbar: {
            useShadows: false,
            verticalScrollbarSize: 10,
            horizontalScrollbarSize: 10,
            vertical: 'auto',
            horizontal: 'auto'
          }
        });

        editor.onDidChangeModelContent(() => {
          const newValue = editor.getValue();
          if (newValue !== props.htmlContent) { 
             emit('update:htmlContent', newValue);
          }
        });

        // 初始化时如果已有报错，立即显示
        if (props.errorLine && props.errorMessage) {
          updateErrorHighlight(props.errorLine, props.errorMessage);
        }
      }
    }

    function destroyEditor() {
      if (editor) {
        editor.dispose();
        editor = null;
      }
    }

    // 核心功能：处理报错高亮
    function updateErrorHighlight(line, msg) {
      if (!editor) return;
      
      const model = editor.getModel();
      
      // 1. 清除旧的高亮和标记
      editor.removeDecorations(decorationIds);
      monaco.editor.setModelMarkers(model, 'owner', []);

      if (!line || line <= 0) return;

      // 2. 添加波浪线标记 (Markers) - 鼠标悬浮会显示错误信息
      monaco.editor.setModelMarkers(model, 'owner', [{
        startLineNumber: line,
        startColumn: 1,
        endLineNumber: line,
        endColumn: model.getLineContent(line).length + 1,
        message: msg || 'Error occurred here',
        severity: monaco.MarkerSeverity.Error
      }]);

      // 3. 添加整行背景色高亮 (Decorations)
      decorationIds = editor.deltaDecorations([], [
        {
          range: new monaco.Range(line, 1, line, 1),
          options: {
            isWholeLine: true,
            className: 'myErrorLineDecoration', // 对应 CSS 中的样式
            glyphMarginClassName: 'myErrorGlyphMargin'
          }
        }
      ]);

      // 4. 滚动到错误行
      editor.revealLineInCenter(line);
    }

    // 监听报错属性变化
    watch([() => props.errorLine, () => props.errorMessage], ([newLine, newMsg]) => {
      if (!props.isShowVis) {
        // 只有在代码视图才高亮
        nextTick(() => {
            updateErrorHighlight(newLine, newMsg);
        });
      }
    });

    onMounted(() => {
      initEditor();
    });

    onBeforeUnmount(() => {
      destroyEditor();
    });

    function extractHtmlCode(input) {
      const regex = /```html([\s\S]*?)```/;
      const match = input.match(regex);
      return match ? match[1].trim() : input;
    }

    function loadHtmlContentIntoIframe() {
      // (保持原有的 iframe 逻辑不变，为了节省篇幅此处省略，请保留你原代码中的内容)
      // ... 你的 iframe 注入逻辑 ...
      const iframe = previewFrame.value;
      if (iframe) {
         // 这里简单复现一下关键部分，实际请使用你原来的完整逻辑
         const content = extractHtmlCode(props.htmlContent);
         const doc = iframe.contentDocument || iframe.contentWindow.document;
         doc.open();
         doc.write(content); // 这里建议还是加上你的 console 拦截脚本
         doc.close();
      }
    }

    watch(() => props.isShowVis, (newValue) => {
      nextTick(() => {
        if (newValue) {
          destroyEditor();
          loadHtmlContentIntoIframe();
        } else {
          initEditor();
        }
      });
    });

    watch(() => props.htmlContent, (newValue) => {
      if (props.isShowVis) {
          loadHtmlContentIntoIframe(); // 预览模式下实时更新 iframe
          return;
      }

      const extractedValue = extractHtmlCode(newValue);
      if (!hasContent.value) {
        destroyEditor();
        return;
      }
      if (!editor) {
        nextTick(() => initEditor());
        return;
      }
      if (editor && editor.getValue() !== extractedValue) {
        const position = editor.getPosition(); // 保持光标位置
        editor.setValue(extractedValue);
        editor.setPosition(position);
        
        // 内容更新后，如果有报错，需要重新高亮，因为 setValue 会清除 decorations
        if (props.errorLine) {
            updateErrorHighlight(props.errorLine, props.errorMessage);
        }
      }
    });

    return {
      editorContainer,
      previewFrame,
      hasContent,
      isFullscreen
    };
  },
};
</script>

<style>
/* 这里放置全局或穿透样式，因为 Monaco 是动态挂载到 DOM 的 */

/* 错误行背景高亮 */
.myErrorLineDecoration {
  background: rgba(255, 0, 0, 0.2);
  border-left: 2px solid #ff5252;
}
</style>

<style scoped>
/* 容器：圆角 + 阴影 + 背景 */
.preview-container {
  position: relative;
  width: 100%;
  height: 70vh; /* 或者由父级控制 */
  border-radius: 12px;
  overflow: hidden;
  background-color: #ffffff;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

/* 头部：类似 VSCode 或 Mac 窗口 */
.editor-title-bar {
  background-color: #f8fafc; /* 浅灰白背景 */
  padding: 10px 16px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 48px;
  flex-shrink: 0;
}

.title-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

/* 模拟 Mac 窗口按钮 */
.mac-buttons {
  display: flex;
  gap: 6px;
}
.mac-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.mac-dot.red { background-color: #ff5f56; }
.mac-dot.yellow { background-color: #ffbd2e; }
.mac-dot.green { background-color: #27c93f; }

.editor-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  font-family: system-ui, -apple-system, sans-serif;
  letter-spacing: 0.5px;
}

.title-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 内容区域 */
.content-wrapper {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #fff;
}

.code-area, .preview-area {
  width: 100%;
  height: 100%;
}

.monaco-wrapper {
  width: 100%;
  height: 100%;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  display: block;
}

/* 空状态美化 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background-color: #f8fafc;
  color: #94a3b8;
}

.empty-icon-bg {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background-color: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 14px;
  font-weight: 500;
}

/* 可以在这里添加全屏样式 */
.preview-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  border-radius: 0;
}
</style>