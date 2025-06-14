<template>
  <div class="login-container">
    <el-card class="login-box">
      <h2 class="login-title">Open Rag Book</h2>
      <el-form :model="loginForm" :rules="rules" ref="loginFormRef">
        <el-form-item prop="username">
          <el-input v-model="loginForm.username" placeholder="请输入用户名" class="input-field" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="loginForm.password" placeholder="请输入密码" show-password class="input-field" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleLogin" class="login-button" :loading="loading">
            登录
          </el-button>
        </el-form-item>
        <el-form-item>
          <el-button @click="goToRegister" class="register-button">
            没有账号？去注册
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 左下角图片 -->
    <img src="@/assets/login.left.png" alt="Left Image" class="corner-image left-corner" />

    <!-- 右下角图片 -->
    <img src="@/assets/login.right.png" alt="Right Image" class="corner-image right-corner" />
  </div>
</template>

<script setup>
import { ref, reactive } from "vue";
import { ElMessage } from "element-plus";
import { useRouter } from "vue-router";
import axios from "@/axios/index.js";
import Cookies from "js-cookie";

const router = useRouter();
const loginFormRef = ref(null);

const loginForm = reactive({
  username: "",
  password: "",
});

const rules = reactive({
  username: [{ required: true, message: "用户名不能为空", trigger: "blur" }],
  password: [{ required: true, message: "密码不能为空", trigger: "blur" }],
});

const loading = ref(false);

const handleLogin = async () => {
  loginFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        loading.value = true;
        const data = await axios.post("account/login", {
          username: loginForm.username,
          password: loginForm.password,
        });

        const token = data.data.token;
        const userInfo = data.data.user;

        if (token && userInfo) {
          Cookies.set("token", token, { expires: 7 }); // 设置token在Cookies中有效期为7天
          // 存储用户信息到localStorage
          localStorage.setItem("userInfo", JSON.stringify(userInfo));
          ElMessage.success("登录成功");
          router.push({ name: "Home" }); // 跳转到首页
        } else {
          ElMessage.error(data.message || "登录失败");
        }
      } catch (error) {
        console.error("登录失败", error);
      } finally {
        loading.value = false;
      }
    } else {
      ElMessage.error("请填写完整的登录信息");
    }
  });
};

const goToRegister = () => {
  router.push({ name: "Register" });
};
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  height: 100vh;
  position: relative;
}

.login-box {
  margin-top: 200px;
  width: 380px;
  /* 控制登录框的宽度 */
  height: 300px;
  /* 固定高度 */
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  /* 垂直居中内容 */
}

.login-title {
  text-align: center;
  margin-bottom: 20px;
  font-size: 24px;
  color: #0052cc;
}

.input-field {
  width: 100%;
  /* 输入框宽度占满父容器 */
}

.login-button {
  width: 100%;
  /* 按钮宽度与输入框一致 */
  background-color: #0052cc;
}

.register-button {
  width: 100%;
  /* 按钮宽度与输入框一致 */
  background-color: #e4e7ec;
}

.corner-image {
  position: absolute;
  width: 420px;
}

.left-corner {
  bottom: 0;
  left: 0;
}

.right-corner {
  bottom: 0;
  right: 0;
}
</style>
