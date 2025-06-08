<template>
  <v-layout class="rounded rounded-md" style="display: flex; flex-direction: column; height: 100vh;width: 100vw">
    <v-container

          id="input-usage"
          fluid
          class="d-flex flex-column no-padding"
      >
        <v-row class="flex-grow-1"> <!-- Adjusted height to leave space for input -->
          <v-col cols="6" class="d-flex flex-column no-padding">
            <div class="chat-container">
              <v-btn @click="clearMsg">清除记录</v-btn>

              <div class="chat" style="flex: 1; overflow-y: auto;">
                <code_chat :chat-list="state.msgList" :sys-avatar="sys"
                           :user-avatar="user"
                ></code_chat>
              </div>
              <div class="input">
                <v-text-field
                    v-model="input"
                    min-width="20em"
                    @keydown.enter="send"
                    class="ma-0 pa-0"
                    style="margin-top: 10px;"
                >
                  <template v-slot:append>
                    <v-btn @click="send">发送</v-btn>
                  </template>
                </v-text-field>
              </div>
            </div>

          </v-col>
          <v-col cols="6" class="no-padding">

          </v-col>
        </v-row>
      </v-container>
<!--    </v-main>-->
  </v-layout>
</template>

<script>
import {onMounted, reactive, ref, toRefs} from "vue";
import {getCodeStream} from "@/api/api.js";
import {MSG_LIST, SysMsgClass, UserMsgClass} from "@/view/config.js";
import storage from "@/view/store.js";
import sys from '@/assets/sys.png'
import code_chat from "@/components/code_chat/index.vue";
import user from '@/assets/user.png'
// import {VInput} from 'vuetify/lib/components/VInput/index'
export default {
  name: "home",
  components: {
    code_chat
// VInput
  },
  setup() {
    let code = ref('')
    let input=ref('')
    const state=reactive({
      msgList:[]
    })



    //将消息插入消息列表
    function setSysMsgList(content){
      // code.value=msg
      if(state.msgList===null)
        state.msgList=[]
      state.msgList.push(SysMsgClass(content))
      storage.set(MSG_LIST,state.msgList)
    }
    function setUserMsgList(content){
      // code.value=msg
      // console.log('打印消息列表：',state)
      if(state.msgList===null)
        state.msgList=[]
      state.msgList.push(UserMsgClass(content))
      storage.set(MSG_LIST,state.msgList)
    }

    /**
     * 发送用户查询
     * @param userInput
     */
    function sendQuery(userInput) {
      getCodeStream({input: userInput},(r)=>{
        console.log('模型输出打印',r.event.target.responseText)
        // setSysMsgList(r.event.target.responseText)
      }).then(r=>{

        // console.log('getCodeStream函数返回结果打印',r)
        setSysMsgList(r.data)

      })
    }
    function send(){
      setUserMsgList(input.value)
      sendQuery(input.value)
      input.value=''
    }
    function loadMessage(){
      state.msgList=storage.get(MSG_LIST)
    }
    function clearMsg(){
      state.msgList=[]
      storage.set(MSG_LIST,state.msgList)
    }

    onMounted(() => {
      loadMessage()

      //渲染msgList

      // sendQuery('你好')
    })


    return {
      code,input,send,state,
      sys,
      user,
      clearMsg
    }

  }
}
</script>

<style scoped>

/* 聊天区域和输入区域的总高度应等于视口高度减去应用栏的高度 */
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh; /* 100vh 是视口高度，48px 是应用栏的高度 */
}

.chat {
  flex: 1; /* 使得聊天区域填充剩余空间 */
  overflow-y: auto; /* 启用垂直滚动 */
}

.input{
  width: 100%;
  height: 60px; /* 假设输入区域的高度为 60px */
  position: relative; /* Changed from absolute to relative */
  bottom: 0; /* Removed the bottom margin */
}
.chat{
  width: 100%;
  /*height: 100%;*/
  overflow-y: auto; /* Added to enable scrolling */

}
.no-padding {
  padding: 0 !important;
}

</style>
