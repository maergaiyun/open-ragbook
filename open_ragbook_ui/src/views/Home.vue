<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { 
  User, Document, Coin, Box, Setting, Expand, Fold, 
  DataBoard, ChatDotRound, Management, Tools, Files,
  FolderOpened, Search, MessageBox, Cpu, Connection, UserFilled
} from '@element-plus/icons-vue'
import Cookies from 'js-cookie'

const router = useRouter()
const isCollapsed = ref(false)

// 获取用户信息
const userInfo = computed(() => {
  const userInfoStr = localStorage.getItem('userInfo')
  try {
    return userInfoStr && userInfoStr !== 'undefined' ? JSON.parse(userInfoStr) : null
  } catch (e) {
    console.error('解析用户信息失败:', e)
    return null
  }
})

// 检查是否为管理员
const isAdmin = computed(() => {
  return userInfo.value && userInfo.value.role_id === 1
})

// 获取用户名显示
const username = computed(() => {
  return userInfo.value ? userInfo.value.user_name : 'admin'
})

const logout = () => {
  Cookies.remove('token')
  localStorage.removeItem('userInfo')
  router.push('/login')
}

const toggleMenu = () => {
  isCollapsed.value = !isCollapsed.value
}

const navigateTo = (path) => {
  router.push(path)
}

const toHome = () => {
  router.push('/')
}
</script>

<template>
  <div class="home-container">
    <!-- 顶部栏 -->
    <div height="56px" class="home-header">
      <div class="home-header-left">
        <div class="home-logo" @click="toHome">
          <!-- <img
            src="@/assets/logo.png"
            alt=""
            style="width: 24px; margin-right: 10px"
          /> -->
          <span>🧠 Open Rag Book</span>
        </div>
        <el-icon class="home-toggle-menu" @click="toggleMenu">
          <Expand v-if="isCollapsed" />
          <Fold v-else />
        </el-icon>
      </div>
      <div class="home-header-right">
        <el-menu class="home-el-menu-header" mode="horizontal" :ellipsis="false">
          <el-sub-menu index="2">
            <template #title>{{ username }}</template>
            <el-menu-item class="home-profile" style="height: 20px" index="2-0" @click="navigateTo('/system/profile-center')">个人中心</el-menu-item>
            <el-menu-item class="home-logout" style="height: 20px" index="2-1" @click="logout">注销</el-menu-item>
          </el-sub-menu>
        </el-menu>
      </div>
    </div>

    <div class="home-bottom">
      <!-- 左侧菜单栏 -->
      <el-aside :width="isCollapsed ? '60px' : '240px'" :class="{ collapsed: isCollapsed }">
        <el-menu :default-active="$route.path" :collapse="isCollapsed" background-color="#172b4d" text-color="#ffffff"
          active-text-color="#ffd04b" class="menu-with-scrollbar">
          <el-sub-menu index="1">
            <template #title>
              <el-icon>
                <FolderOpened />
              </el-icon>
              <span class="home-menu-text">知识库配置</span>
            </template>
            <el-menu-item index="/knowledge/mgt" @click="navigateTo('/knowledge/mgt')">
              <el-icon class="submenu-icon">
                <DataBoard />
              </el-icon>
              <span class="home-menu-text">知识库管理</span>
            </el-menu-item>
            <el-menu-item index="/knowledge/document" @click="navigateTo('/knowledge/document')">
              <el-icon class="submenu-icon">
                <Document />
              </el-icon>
              <span class="home-menu-text">文档管理</span>
            </el-menu-item>
            <el-menu-item index="/knowledge/recall-test" @click="navigateTo('/knowledge/recall-test')">
              <el-icon class="submenu-icon">
                <Search />
              </el-icon>
              <span class="home-menu-text">召回检索测试</span>
            </el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="2">
            <template #title>
              <el-icon>
                <MessageBox />
              </el-icon>
              <span class="home-menu-text">对话管理</span>
            </template>
            <el-menu-item index="/chat/single" @click="navigateTo('/chat/single')">
              <el-icon class="submenu-icon">
                <ChatDotRound />
              </el-icon>
              <span class="home-menu-text">单知识库检索对话</span>
            </el-menu-item>
          </el-sub-menu>

          <el-sub-menu index="5">
            <template #title>
              <el-icon>
                <Setting />
              </el-icon>
              <span class="home-menu-text">系统设置</span>
            </template>
            <el-menu-item v-if="isAdmin" index="/system/users-mgr" @click="navigateTo('/system/users-mgr')">
              <el-icon class="submenu-icon">
                <UserFilled />
              </el-icon>
              <span class="home-menu-text">用户设置</span>
            </el-menu-item>

            <el-menu-item index="/system/models-mgr" @click="navigateTo('/system/models-mgr')">
              <el-icon class="submenu-icon">
                <Cpu />
              </el-icon>
              <span class="home-menu-text">大模型管理</span>
            </el-menu-item>

            <el-menu-item index="/system/embedding-mgr" @click="navigateTo('/system/embedding-mgr')">
              <el-icon class="submenu-icon">
                <Connection />
              </el-icon>
              <span class="home-menu-text">嵌入模型管理</span>
            </el-menu-item>

            <el-menu-item index="/system/profile-center" @click="navigateTo('/system/profile-center')">
              <el-icon class="submenu-icon">
                <User />
              </el-icon>
              <span class="home-menu-text">个人中心</span>
            </el-menu-item>
          </el-sub-menu>
        </el-menu>

        <!-- 收起/展开按钮 -->
        <!-- <div class="collapse-toggle" @click="toggleCollapse">
          <el-icon v-if="isCollapsed"><ArrowRight /></el-icon>
          <el-icon v-else><ArrowLeft /></el-icon>
        </div> -->
      </el-aside>

      <!-- 主内容区域 -->
      <div class="home-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped lang="less">
/* 全局样式 */
.home-container {
  width: 100%;
  height: 100vh;
}

/* 顶部栏样式 */
.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: #fff;
  box-shadow: 0 1px 2px #dbdbdb;
}

.home-header-left {
  margin-left: 10px;
  display: flex;
  align-items: center;

  .home-logo {
    font-size: 20px;
    font-weight: bold;
    margin-right: 20px;
    display: flex;
    align-items: center;
    cursor: pointer;
  }

  .home-toggle-menu {
    cursor: pointer;
  }
}

.home-header-right {
  display: flex;
  align-items: center;
  height: 50%;

  /* 基本菜单项样式 */
  .home-menu-text {
    opacity: 1;
    transition: opacity 0.3s ease, visibility 0.3s ease;
    /* 控制透明度和可见性 */
    visibility: visible;
  }
}

.home-bottom {
  display: flex;
  justify-content: start;
  height: calc(100vh - 58px);

  /* 主内容区域 */
  .home-content {
    height: calc(100vh - 58px);
    width: 100%;
    padding: 12px 24px 0;
    overflow-x: auto;
    overflow-y: auto;
  }
}

/* 覆盖 el-menu 的默认样式 */
.el-menu {
  width: 100%;
  /* 确保菜单占满整个 aside */
  border-right: none;
  /* 移除边框 */
}

.el-menu-item,
.el-sub-menu__title {
  padding: 0 20px;
  /* 调整内边距，确保项占满宽度 */
  width: 100%;
  box-sizing: border-box;
}

/* 菜单栏样式 */
.el-aside {
  transition: max-width 0.3s ease, width 0.3s ease;
  display: flex;
  flex-direction: column;
  background-color: #172b4d !important;
}

.aside.collapsed {
  max-width: 64px;
  /* 收缩时宽度 */
}

/* 收缩状态下的菜单项 */
.collapsed .home-menu-text {
  opacity: 0;
  visibility: hidden;
}

.el-menu-item {
  position: relative;
  box-sizing: border-box;
  /* 将盒模型设置为 border-box，让内边距和边框包含在元素宽度内 */
  width: calc(100% - 10px);
  /* 宽度减少一定数值，示例减少10px，可按需调整 */
  height: calc(100% - 20px);
  /* 高度同理减少一定数值 */
  margin: 5px;
  /* 设置外边距，让元素整体在父容器中有一定间隔，也可根据需要调整 */
}

/* 悬浮状态背景颜色 */
.el-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  /* 悬浮背景颜色 */
  border-radius: 6px;
  margin: 4px 8px;
  transition: all 0.3s ease;

  .submenu-icon {
    color: #ffd04b !important;
    transform: scale(1.1);
  }
}

.el-menu--horizontal.el-menu {
  height: 50% !important;
  border-bottom: 0 !important;
}

/* 激活状态背景颜色 */
.el-menu-item.is-active {
  background: linear-gradient(90deg, #0052cc 0%, #0066ff 100%) !important;
  /* 激活背景颜色 */
  color: #ffffff !important;
  /* 激活文本颜色 */
  border-radius: 6px;
  margin: 4px 8px;
  box-shadow: 0 2px 8px rgba(0, 82, 204, 0.3);
  position: relative;

  &::after {
    content: '';
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    width: 4px;
    height: 4px;
    background: #ffffff;
    border-radius: 50%;
  }

  .submenu-icon {
    color: #ffffff !important;
  }
}

/* 二级菜单悬浮背景 */
.el-sub-menu__title:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border-radius: 6px;
  margin: 4px 8px;
  transition: all 0.3s ease;

  .el-icon {
    color: #ffd04b !important;
    transform: scale(1.1);
  }
}

/* 确保菜单容器有足够的高度来启用滚动 */
.home-bottom el-aside {
  height: 100vh;
  /* 设置菜单栏的高度为100vh，确保它占满整个屏幕高度 */
  overflow-y: auto;
  /* 使菜单可以垂直滚动 */
}

/* 使 el-menu 滚动条样式可用 */
.menu-with-scrollbar {
  max-height: 100vh;
  /* 最大高度为 90vh，避免菜单过长 */
  overflow-y: auto;
  /* 使菜单可以垂直滚动 */
}

/* 自定义滚动条样式 */
.menu-with-scrollbar::-webkit-scrollbar {
  width: 6px;
  /* 设置滚动条的宽度 */
}

/* 滚动条轨道 */
.menu-with-scrollbar::-webkit-scrollbar-track {
  background-color: #f1f1f1;
  /* 设置轨道颜色 */
}

/* 滚动条滑块 */
.menu-with-scrollbar::-webkit-scrollbar-thumb {
  background-color: #888;
  /* 滑块颜色 */
}

/* 滑块悬停时的样式 */
.menu-with-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #555;
  /* 滑块悬停时的颜色 */
}

/* 图标样式 */
.submenu-icon {
  font-size: 16px;
  margin-right: 8px;
  transition: all 0.3s ease;
  color: #ffffff;
}

/* 主菜单图标样式 */
.el-sub-menu__title .el-icon {
  font-size: 18px;
  margin-right: 8px;
  transition: all 0.3s ease;
  color: #ffffff;
}

/* 收缩状态下的图标调整 */
.collapsed .submenu-icon,
.collapsed .el-sub-menu__title .el-icon {
  margin-right: 0;
  font-size: 20px;
}

/* 菜单项整体样式优化 */
.el-menu-item {
  display: flex;
  align-items: center;
  transition: all 0.3s ease;
}

.el-sub-menu__title {
  display: flex;
  align-items: center;
  transition: all 0.3s ease;
}
</style>
