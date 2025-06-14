import { createRouter, createWebHistory } from "vue-router";
import Home from "@/views/Home.vue";
import Login from "@/views/Login.vue";
import Register from "@/views/Register.vue";
// 知识库管理
import KnowledgeMgt from "@/views/Knowledge/KnowledgeMgt.vue";
import DocumentMgt from "@/views/Knowledge/DocumentMgt.vue";
import SingleChat from "@/views/Chat/SingleChat.vue";
import RecallTest from "@/views/Knowledge/RecallTest.vue";
// import Employee from "../views/Hr/Employee/Employee.vue";
// import Dtm from "../views/Hr/Dtm.vue";
// import JobCertificate from "../views/Hr/JobCertificate.vue";
// import FilesDownload from "../views/Hr/FilesDownload.vue";

// import ConstructionContractor from "../views/Project/ConstructionContractor.vue";
// import MaterialProcurement from "../views/Fin/MaterialProcurement.vue";
// import UnitPrice from "../views/Fin/UnitPrice.vue";

// 系统设置
import UsersMgr from "@/views/System/UsersMgr.vue";
import ModelsMgr from "@/views/System/ModelsMgr.vue";
import EmbeddingMgr from "@/views/System/EmbeddingMgr.vue";
import ProfileCenter from "@/views/System/ProfileCenter.vue";

import Cookies from "js-cookie";
import { ElMessage } from "element-plus";

const routes = [
  {
    path: "/",
    name: "Home",
    redirect: "/knowledge/mgt",
  },
  {
    path: "/login",
    name: "Login",
    component: Login,
    meta: { noAuth: true },
  },
  {
    path: "/register",
    name: "Register",
    component: Register,
    meta: { noAuth: true },
  },
  {
    path: "/knowledge",
    component: Home,
    children: [
      {
        path: "mgt",
        name: "Mgt",
        component: KnowledgeMgt,
        meta: { title: "知识库管理", parent: "知识库配置" },
      },
      {
        path: "document",
        name: "DocumentMgr",
        component: DocumentMgt,
        meta: { title: "文档管理", parent: "知识库配置" },
      },
      {
        path: "recall-test",
        name: "RecallTest",
        component: RecallTest,
        meta: { title: "召回检索测试", parent: "知识库配置" },
      },
    ],
  },
  {
    path: "/chat",
    component: Home,
    children: [
      {
        path: "single",
        name: "Single",
        component: SingleChat,
        meta: { title: "单知识库检索对话", parent: "对话管理" },
      },
    ],
  },
  {
    path: "/system",
    component: Home,
    children: [
      {
        path: "users-mgr",
        name: "UsersMgr",
        component: UsersMgr,
        meta: { title: "用户管理", parent: "系统管理", requiresAdmin: true },
      },
      {
        path: "models-mgr",
        name: "ModelsMgr",
        component: ModelsMgr,
        meta: { title: "模型管理", parent: "系统管理" },
      },
      {
        path: "embedding-mgr",
        name: "EmbeddingMgr",
        component: EmbeddingMgr,
        meta: { title: "嵌入模型管理", parent: "系统管理" },
      },
      {
        path: "profile-center",
        name: "ProfileCenter",
        component: ProfileCenter,
        meta: { title: "个人中心", parent: "系统管理" },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes,
});

// 全局路由守卫
router.beforeEach((to, from, next) => {
  const token = Cookies.get("token");
  const userInfoStr = localStorage.getItem("userInfo");
  let userInfo = null;
  try {
    userInfo = userInfoStr && userInfoStr !== 'undefined' ? JSON.parse(userInfoStr) : null;
  } catch (e) {
    console.error('解析用户信息失败:', e);
    userInfo = null;
  }

  // 定义需要登录才能访问的路由
  const requiresAuth = to.matched.some(record =>
    !record.meta.noAuth // 允许通过noAuth: true来标记无需认证的路由
  );

  // 检查是否需要管理员权限
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin);

  if (!token && requiresAuth && to.name !== "Login") {
    ElMessage.error("登录状态已过期，请重新登录");
    // 记录用户想要访问的页面，登录后可以直接跳转
    next({
      name: "Login",
      query: { redirect: to.fullPath }
    });
  } else if (requiresAdmin && (!userInfo || userInfo.role_id !== 1)) {
    // 需要管理员权限但用户不是管理员
    ElMessage.error("您没有权限访问此页面");
    next({ name: "Home" });
  } else {
    // 已登录状态下访问登录页，直接跳转到首页
    if (token && to.name === "Login") {
      next({ name: "Home" });
    } else {
      if (to.meta && to.meta.title) {
        document.title = `${to.meta.title} - 知识库管理系统`;
      }
      next();
    }
  }
});

export default router;
