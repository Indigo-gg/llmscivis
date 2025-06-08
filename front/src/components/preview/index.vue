<template>
  <div class="preview-container">
    <div class="preview-header">
      <slot name="actions"></slot>
    </div>
    <div v-if="!isShowVis" class="code-container">
      <pre><code class="hljs" v-html="highlightedCode"></code></pre>
    </div>
    <div class="preview-frame" v-else>
      <iframe ref="previewFrame" sandbox="allow-scripts allow-same-origin allow-top-navigation"
        style="width: 100%;height:100%" src="about:blank" frameBorder="0"></iframe>
    </div>
  </div>
</template>

<script>
import { onMounted, nextTick, ref, watch, computed } from 'vue';
import hljs from 'highlight.js';
import 'highlight.js/styles/github.css'; // 选择一种高亮主题

export default {
  name: 'index',
  emits: ['error', 'console-output'],
  props: {
    htmlContent: {
      type: String,
      required: true,
    },
    isShowVis: {
      type: Boolean,
      required: false,
      default: false
    }
  },
  setup(props, { emit }) {  // 正确获取emit
    const previewFrame = ref(null);

    // onMounted(async () => {
    //   await nextTick(); // 确保DOM更新
    //   if (props.isShowVis) {  // 初始加载检查
    //     loadHtmlContentIntoIframe();
    //   }
    // });


    function extractHtmlCode(input) {
      const regex = /```html([\s\S]*?)```/
      const match = input.match(regex);

      // 如果匹配成功，返回提取的代码，否则返回
      return match ? match[1].trim() : input;
    }
    const highlightedCode = computed(() => {

      return hljs.highlightAuto(extractHtmlCode(props.htmlContent)).value;
    })


    function loadHtmlContentIntoIframe() {
      const iframe = previewFrame.value;
      if (iframe) {
        const doc = iframe.contentDocument || iframe.contentWindow.document;
        doc.open();
        doc.write('');
        doc.close();

        nextTick(() => {
          // 注入错误处理和控制台重写代码
          const consoleScript = `
            <script>
              // 捕获全局错误
              window.onerror = function(message, source, lineno, colno, error) {
                window.parent.postMessage({
                  type: 'console',
                  logType: 'error',
                  message: 'Error: ' + message + ' (at ' + source + ':' + lineno + ':' + colno + ')',
                  timestamp: new Date().toISOString()
                }, '*');
                return false;
              };

              // 捕获 Promise 错误
              window.addEventListener('unhandledrejection', function(event) {
                window.parent.postMessage({
                  type: 'console',
                  logType: 'error',
                  message: 'Unhandled Promise Rejection: ' + event.reason,
                  timestamp: new Date().toISOString()
                }, '*');
              });

              // 重写所有console方法
              ['log', 'info', 'warn', 'error'].forEach(type => {
                const originalConsole = console[type];
                console[type] = function(...args) {
                  // 处理复杂对象
                  const processedArgs = args.map(arg => {
                    if (typeof arg === 'object') {
                      try {
                        return JSON.stringify(arg);
                      } catch (e) {
                        return String(arg);
                      }
                    }
                    return String(arg);
                  });

                  // 保持原始输出
                  originalConsole.apply(this, args);
                  
                  // 发送消息到父窗口
                  window.parent.postMessage({
                    type: 'console',
                    logType: type,
                    message: processedArgs,
                    timestamp: new Date().toISOString()
                  }, '*');
                };
              });
            <\/script>
          `;

          const content = extractHtmlCode(props.htmlContent);
          doc.open();
          // Create a basic HTML structure first
          doc.write('<!DOCTYPE html><html><head></head><body></body></html>');
          doc.close(); // Close the document write stream before modifying the body

          // Inject the console script and the actual content into the body
          if (doc.body) {
            // Inject console script into head
            const scriptElement = doc.createElement('script');
            // Remove <script> tags from the consoleScript string before setting textContent
            scriptElement.textContent = consoleScript.replace(/^\s*<script>\s*|\s*<\/script>\s*$/g, '');
            doc.head.appendChild(scriptElement);

            // Set the main content in the body
            doc.body.innerHTML = content;
          } else {
             console.error("Iframe body not found after writing basic structure.");
             emit('error', { type: 'error', message: 'Failed to load content: iframe body not found.' });
          }

          // 清除之前的事件监听器
          const messageHandler = (event) => {
            if (event.data && event.data.type === 'console') {
              const logEntry = {
                type: event.data.logType,
                message: Array.isArray(event.data.message) ? event.data.message.join(' ') : event.data.message,
                timestamp: event.data.timestamp
              };

              // 立即发送日志
              emit('console-output', [logEntry]);

              // 如果是错误类型，同时触发error事件
              if (event.data.logType === 'error') {
                emit('error', logEntry);
              }
            }
          };

          window.removeEventListener('message', messageHandler);
          window.addEventListener('message', messageHandler);
          // 新增：调试输出日志内容，便于排查日志传递问题
          window.addEventListener('message', (event) => {
            if (event.data && event.data.type === 'console') {
              console.log('[Preview] 收到iframe日志：', event.data);
            }
          });
        });
      }
    }

    watch(() => props.isShowVis, (newValue) => {  // 移除不正确的emit参数
      // if (newValue) {
      console.log(`isShowVis changed to ` + newValue);
      nextTick(() => {
        loadHtmlContentIntoIframe();
      });

    });
    return {
      previewFrame,
      highlightedCode
    };
  },
};

</script>

<style scoped>
.preview-container {
  position: relative;
  width: 100%;
  height: 70vh;
  /*background-color: #2c3e50;*/
  margin: 5px;
}

.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
  /* 可选：移除边框 */
}

.code-container {
  height: 100%;
}

.code-container pre {
  margin: 0;
  padding: 10px;
  height: 100%;
  text-align: left;
  /*background-color: #f6f8fa; !* 背景色 *!*/
  border-radius: 4px;
  /* 圆角 */
  overflow-x: auto;
  /* 水平溢出时滚动 */
}

.hljs {
  font-family: 'Courier New', Courier, monospace;
  /* 等宽字体 */
  font-size: 14px;
}

.preview-container:fullscreen {
  padding: 0;
  width: 100vw;
  height: 100vh;
  background: white;
}
</style>
