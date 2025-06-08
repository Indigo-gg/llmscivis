import axios from 'axios';
const baseURL='http://127.0.0.1:5000'
// 创建axios实例
const service = axios.create({
    baseURL: baseURL, // 设置统一的请求前缀
    timeout: 600000 // 设置统一的超时时长
});

// POST请求封装
function post(url, data) {
    return service({
        url: url,
        method: 'post',
        data: data
    });
}
function get(url, data) {
    return service({
        url: url,
        method: 'get',
        params: data
    });
}
function postStream(url,data,onProgress) {
    return service({
        url: url,
        method: 'post',
        data:data,
        responseType: 'stream',
        onDownloadProgress: (progressEvent) => {
            const chunk = progressEvent.currentTarget.responseText; // 获取当前分块数据
            onProgress(chunk); // 处理流式数据
        },
    })
}
export {post,postStream,get}
