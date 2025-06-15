<template>
    <div class="register-container">
        <el-card class="register-box">
            <h2 class="register-title">用户注册</h2>
            <el-form :model="registerForm" :rules="rules" ref="registerFormRef" label-width="80px">
                <el-form-item label="用户名" prop="username">
                    <el-input v-model="registerForm.username" placeholder="请输入用户名（至少3位）" class="input-field" />
                </el-form-item>
                <el-form-item label="密码" prop="password">
                    <el-input v-model="registerForm.password" placeholder="请输入密码（至少6位）" show-password
                        class="input-field" />
                </el-form-item>
                <el-form-item label="确认密码" prop="confirmPassword">
                    <el-input v-model="registerForm.confirmPassword" placeholder="请再次输入密码" show-password
                        class="input-field" />
                </el-form-item>
                <el-form-item label="邮箱" prop="email">
                    <el-input v-model="registerForm.email" placeholder="请输入邮箱（可选）" class="input-field" />
                </el-form-item>
                <el-form-item label="真实姓名" prop="real_name">
                    <el-input v-model="registerForm.real_name" placeholder="请输入真实姓名（可选）" class="input-field" />
                </el-form-item>
                <el-form-item label="手机号" prop="phone">
                    <el-input v-model="registerForm.phone" placeholder="请输入手机号（可选）" class="input-field" />
                </el-form-item>
                <el-form-item>
                    <el-button type="primary" @click="handleRegister" class="register-button" :loading="loading">
                        注册
                    </el-button>
                </el-form-item>
                <el-form-item>
                    <el-button @click="goToLogin" class="login-button">
                        已有账号？去登录
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
const registerFormRef = ref(null);

const registerForm = reactive({
    username: "",
    password: "",
    confirmPassword: "",
    email: "",
    real_name: "",
    phone: "",
});

// 自定义验证规则
const validateConfirmPassword = (rule, value, callback) => {
    if (value !== registerForm.password) {
        callback(new Error('两次输入的密码不一致'));
    } else {
        callback();
    }
};

const validateEmail = (rule, value, callback) => {
    if (value && !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value)) {
        callback(new Error('邮箱格式不正确'));
    } else {
        callback();
    }
};

const validatePhone = (rule, value, callback) => {
    if (value && !/^1[3-9]\d{9}$/.test(value)) {
        callback(new Error('手机号格式不正确'));
    } else {
        callback();
    }
};

const rules = reactive({
    username: [
        { required: true, message: "用户名不能为空", trigger: "blur" },
        { min: 3, message: "用户名长度不能少于3位", trigger: "blur" }
    ],
    password: [
        { required: true, message: "密码不能为空", trigger: "blur" },
        { min: 6, message: "密码长度不能少于6位", trigger: "blur" }
    ],
    confirmPassword: [
        { required: true, message: "请确认密码", trigger: "blur" },
        { validator: validateConfirmPassword, trigger: "blur" }
    ],
    email: [
        { validator: validateEmail, trigger: "blur" }
    ],
    phone: [
        { validator: validatePhone, trigger: "blur" }
    ]
});

const loading = ref(false);

const handleRegister = async () => {
    registerFormRef.value.validate(async (valid) => {
        if (valid) {
            try {
                loading.value = true;
                
                // 注册请求
                const registerData = await axios.post("account/register", {
                    username: registerForm.username,
                    password: registerForm.password,
                    email: registerForm.email || null,
                    real_name: registerForm.real_name || null,
                    phone: registerForm.phone || null,
                });

                console.log('Register response:', registerData);

                // 检查注册是否成功
                if (registerData.status === 'success' || registerData.code === 200) {
                    ElMessage.success("注册成功，正在自动登录...");
                    
                    // 注册成功后自动登录
                    try {
                        const loginData = await axios.post("account/login", {
                            username: registerForm.username,
                            password: registerForm.password,
                        });

                        console.log('Auto login response:', loginData);

                        // 检查登录是否成功
                        if (loginData.status === 'success' || loginData.code === 200) {
                            // 保存token和用户信息
                            const token = loginData.data?.token || loginData.token;
                            const userInfo = loginData.data?.user || loginData.user;
                            
                            if (token) {
                                Cookies.set("token", token);
                            }
                            
                            if (userInfo) {
                                localStorage.setItem("userInfo", JSON.stringify(userInfo));
                            }

                            ElMessage.success("注册并登录成功，欢迎使用！");
                            
                            // 跳转到首页
                            router.push({ name: "Home" });
                        } else {
                            ElMessage.warning("注册成功，但自动登录失败，请手动登录");
                            router.push({ name: "Login" });
                        }
                    } catch (loginError) {
                        console.error("自动登录失败", loginError);
                        ElMessage.warning("注册成功，但自动登录失败，请手动登录");
                        router.push({ name: "Login" });
                    }
                } else {
                    ElMessage.error(registerData.message || "注册失败");
                }
            } catch (error) {
                console.error("注册失败", error);
                const errorMessage = error.response?.data?.message || error.message || "注册失败，请稍后重试";
                ElMessage.error(errorMessage);
            } finally {
                loading.value = false;
            }
        } else {
            ElMessage.error("请填写完整的注册信息");
        }
    });
};

const goToLogin = () => {
    router.push({ name: "Login" });
};
</script>

<style scoped>
.register-container {
    display: flex;
    justify-content: center;
    height: 100vh;
    position: relative;
    padding-top: 50px;
}

.register-box {
    margin-top: 50px;
    width: 450px;
    height: 600px;
    padding: 30px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    z-index: 10;
}

.register-title {
    text-align: center;
    margin-bottom: 30px;
    font-size: 24px;
    color: #0052cc;
}

.input-field {
    width: 100%;
}

.register-button {
    width: 100%;
    background-color: #0052cc;
}

.login-button {
    width: 100%;
    /* 按钮宽度与输入框一致 */
    background-color: #e4e7ec;
}

.corner-image {
    position: absolute;
    width: 420px;
    z-index: 1;
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