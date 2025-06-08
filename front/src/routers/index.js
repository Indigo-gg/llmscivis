import { createRouter, createMemoryHistory } from "vue-router"
import home from "@/view/home.vue";
import demo from "@/components/demo.vue";
import errorRecord from "@/view/error-record.vue";
// import newnew from "@/test/newnew.vue"
//创建路由器
const router = createRouter({

    //管理路由
    routes: [  //一个一个的路由规则
        {
            //路径
            path: '/',
            //组件绑定
            component: home
        },
        {
            //路径
            path: '/error-record',
            //组件绑定
            component: errorRecord
        },
        {
            //路径
            path: '/demo',
            //组件绑定
            component: demo
        }
    ],
    history: createMemoryHistory()
})

export default router

