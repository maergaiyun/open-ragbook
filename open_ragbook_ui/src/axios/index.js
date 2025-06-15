import axios from "axios";
import Cookies from "js-cookie";
import { ElMessage } from "element-plus";
import router from "@/router";

// 全局轮询清理器
window.globalPollingCleanup = window.globalPollingCleanup || [];

const instance = axios.create({
  baseURL: process.env.VUE_APP_API_BASE_URL, // 动态加载 API 前缀
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

// 添加请求拦截器
instance.interceptors.request.use(
  (config) => {
    const token = Cookies.get("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    ElMessage.error("请求发送失败");
    return Promise.reject(error);
  }
);

// 添加响应拦截器
instance.interceptors.response.use(
  (response) => {
    // 如果响应正常则直接返回数据
    return response.data;
  },
  (error) => {
    if (error.response) {
      switch (error.response.status) {
        case 401: // 未授权，token过期或无效
          ElMessage.error("登录状态已过期，请重新登录");
          // 清除token
          Cookies.remove("token");
          // 清理所有全局轮询
          if (window.globalPollingCleanup) {
            window.globalPollingCleanup.forEach(cleanup => {
              if (typeof cleanup === 'function') {
                cleanup();
              }
            });
            window.globalPollingCleanup = [];
          }
          // 跳转到登录页
          router.push({
            name: "Login",
            query: { redirect: router.currentRoute.value.fullPath }
          });
          break;
        case 403: // 权限不足
          ElMessage.error("您没有权限执行此操作");
          break;
        case 404: // 资源不存在
          ElMessage.error("请求的资源不存在");
          break;
        case 500: { // 服务器错误
          // 尝试获取后端返回的具体错误信息
          const errorMessage = error.response.data?.message || "服务器错误，请稍后再试";
          ElMessage.error(errorMessage);
          break;
        }
        default:
          ElMessage.error(error.response.data?.message || "请求失败");
      }
    } else {
      // 请求超时或网络错误
      if (error.message.includes("timeout")) {
        ElMessage.error("请求超时，请检查网络连接");
      } else {
        ElMessage.error("网络异常，请检查网络连接");
      }
    }
    return Promise.reject(error);
  }
);

export default instance;
