import { createApp } from "vue";
import App from "@/App.vue";
import "@/assets/global.css";
import router from "@/router";
import store from "@/store";
import axios from '@/axios';

// 引入 Element Plus 组件和样式
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

const app = createApp(App);
app.use(ElementPlus);
app.use(store);
app.use(router);

// 全局注册axios实例
app.config.globalProperties.$http = axios;

app.mount("#app");

const debounce = (fn, delay) => {
  let timer = null;
  return function () {
    let context = this;
    let args = arguments;
    clearTimeout(timer);
    timer = setTimeout(function () {
      fn.apply(context, args);
    }, delay);
  };
};

// const _ResizeObserver = window.ResizeObserver;
// window.ResizeObserver = class ResizeObserver extends _ResizeObserver {
//   constructor(callback) {
//     callback = debounce(callback, 16);
//     super(callback);
//   }
// };
