<template>
  <div class="chat-window" style="height: 100%; width: 100%; overflow-y: auto;" ref="chatMessagesRef">
    <v-card v-if="!chatList || chatList.length === 0">
      请开始对话！！！
    </v-card>
    <v-list
        density="compact"
        nav>
      <div ref="chatMessagesRef">
        <v-list-item v-for="message in chatList"
                     :key="message.id"
                     class="d-flex flex-column"
                     :class="{ 'user-message': message.role === 'user', 'sys-message': message.role === 'sys' }"
        >
          <div v-if="message.role === 'sys'" style="width: 100%">
            <div>
              <v-img :src="sysAvatar"
                     height="2em"
                     width="2em"
                     class="rounded-circle"
              ></v-img>
            </div>
            <div class="message-content-fill" style="text-align: left;">
              <div v-html="markedContent(message.content)"></div>
              <v-list-item-subtitle>{{ message.time }}</v-list-item-subtitle>
            </div>

          </div>
          <template v-else>
            <div style="width: 100%; text-align: right;">
              <div style="display: inline-block">
                <!--              <div class="d-flex justify-end">-->
                <v-img :src="userAvatar"
                       height="2em"
                       width="2em"
                       class="rounded-circle"
                ></v-img>
                <!--              </div>-->

              </div>
              <div>
                <div v-html="markedContent(message.content)"></div>
                <v-list-item-subtitle>{{ message.time }}</v-list-item-subtitle>
              </div>
            </div>
          </template>
        </v-list-item>

      </div>
    </v-list>
  </div>
</template>

<script>
import {nextTick, onMounted, ref} from 'vue';
import { marked } from 'marked';
import 'highlight.js/styles/monokai-sublime.css';

export default {
  name: 'index',
  props: {
    chatList: {
      type: Array,
      default: () => []
    },
    userAvatar: {
      type: String
    },
    sysAvatar: {
      type: String
    }
  },
  setup(props) {
    const chatMessagesRef = ref(null);

    marked.setOptions({
      renderer: new marked.Renderer(),
      highlight: function (code, lang) {
        const hljs = require('highlight.js');
        const language = hljs.getLanguage(lang) ? lang : 'plaintext';
        return hljs.highlight(code, { language }).value;
      },
      langPrefix: 'hljs language-',
      breaks: false,
      gfm: true,
      headerIds: true,
      headerPrefix: '',
      mangle: true,
      pedantic: false,
      sanitize: false,
      silent: false,
      smartLists: false,
      smartypants: false,
      xhtml: false
    });

    const scrollToBottom = () => {
      nextTick(() => {
        if (chatMessagesRef.value) {
          // 确保内容超出可视区域
          if (chatMessagesRef.value.scrollHeight > chatMessagesRef.value.clientHeight) {
            console.log('聊天窗口的高度', chatMessagesRef.value.scrollTop, chatMessagesRef.value.scrollHeight);
            chatMessagesRef.value.scrollTop = chatMessagesRef.value.scrollHeight;
          }
        }
      });
    };

    const markedContent = (content) => {
      return marked(content);
    };

    onMounted(() => {
      scrollToBottom();
    });

    return {
      chatMessagesRef,
      scrollToBottom,
      markedContent
    };
  }
};
</script>

<style scoped>
.chat-window {
  display: flex;
  flex-direction: column;
}

.rounded-circle {
  background-color: rgba(75, 74, 74, 0.09);
  border-radius: 50%;
}
</style>
