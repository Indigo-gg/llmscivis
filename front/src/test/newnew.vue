<!--全屏显示-->
<!--点击数字加一-->
<!--更换颜色和音乐-->
<template>
<div class="main" @click="add">

  <div class="number">
    您已获得{{number}}万元
  </div>
  <div class="emoji-container">
    <img
        v-for="(emoji, index) in emojis"
        :key="index"
        :src="emoji.src"
        :style="emoji.style"
        class="emoji"
    />
  </div>
</div>
</template>

<script>

import {onMounted, ref} from "vue";
import store from "@/view/store.js";

export default {
  name: "newnew",
  setup() {

    let number=ref(0)
    const musicPath='https:\\/\\/img.tukuppt.com\\/newpreview_music\\/09\\/00\\/62\\/5c893bc792bbf37441.mp3'
    let audio = new Audio(musicPath); // 替换为你的音乐文件路径
    let emojis = ref([]);
    let showDialog = ref(false);
    function add(){
      number.value++
      store.set('number',number.value)

      if(number.value%10===0){
        dropEmoji()
      }
          // showDialog.value=true
      playSound()
    }
    const playSound = () => {
      audio.currentTime = 0; // 重置音频时间
      audio.play().catch(error => console.error('Error playing sound:', error));
    };
    const dropEmoji = () => {
      const emojiSrcs = [
        'https://emojipic.cn/Pics/72/apple/smiling-face-with-heart-shaped-eyes_1f60d.png',
        'https://emojipic.cn/Pics/72/apple/heavy-black-heart_2764.png',
        'https://emojipic.cn/Pics/72/apple/orange-heart_1f9e1.png',
        'https://emojipic.cn/Pics/72/apple/blue-heart_1f499.png',
        'https://emojipic.cn/Pics/72/apple/blue-heart_1f499.png'
      ];
      const randomEmojiSrc = emojiSrcs[Math.floor(Math.random() * emojiSrcs.length)];
      const randomX = Math.random() * 100 + '%';
      const randomY = Math.random() * 100 + '%';

      const emoji = {
        src: randomEmojiSrc,
        style: {
          left: randomX,
          top: randomY,
          animationDuration: `${Math.random() * 2 + 1}s` // 随机动画持续时间
        }
      };

      emojis.value.push(emoji);

      // 移除已经完成动画的表情包
      setTimeout(() => {
        emojis.value = emojis.value.filter(e => e !== emoji);
      }, 3000); // 3秒后移除表情包
    };


    const fullscreenElement = ref(null);

    const toggleFullscreen = () => {
      if (!document.fullscreenElement) {
        fullscreenElement.value.requestFullscreen().catch(err => console.error(err));
      } else {
        document.exitFullscreen();
      }
    };
    onMounted(()=>{
      if (store.get('number')){
        number.value=store.get('number')
      }


    })
    return {number,add,toggleFullscreen,showDialog,emojis}
  }
}
</script>

<style scoped>
.main {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;

  /* 背景颜色 */
  background-color: #e0f7fa; /* 浅蓝色背景 */

  /* 渐变背景 */
  background: linear-gradient(135deg, #e0f7fa 0%, #b2ebf2 100%);

  /* 边框半径 */
  border-radius: 10px;

  /* 阴影效果 */
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);

  /* 内边距 */
  padding: 20px;

}
.number {
  /* 字体大小 */
  font-size: 4rem; /* 根据需要调整 */

  /* 字体颜色 */
  color: #ff6f61; /* 粉红色 */

  /* 文字阴影 */
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);

  /* 字体样式 */
  font-family: 'Courier New', Courier, monospace;

  /* 字体粗细 */
  font-weight: bold;

  /* 渐变背景 */
  background: linear-gradient(45deg, #ff9a9e 0%, #fad0c4 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;

  /* 动画效果 */
  animation: glow 2s infinite alternate;
}

@keyframes glow {
  from {
    text-shadow: 0 0 10px #ff6f61;
  }
  to {
    text-shadow: 0 0 20px #ff6f61;
  }
}

.emoji-container {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none; /* 使表情包不影响点击事件 */
}

.emoji {
  position: absolute;
  width: 50px; /* 表情包大小 */
  height: 50px;
  animation: drop 3s ease-out forwards;
}

@keyframes drop {
  0% {
    transform: translateY(-100%);
    opacity: 1;
  }
  100% {
    transform: translateY(110vh);
    opacity: 0;
  }
}
</style>
