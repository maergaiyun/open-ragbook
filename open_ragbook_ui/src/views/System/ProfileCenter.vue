<template>
  <div class="profile-center-page">
    <div class="header">
      <div class="title">个人中心</div>
    </div>

    <div class="content-container">
      <!-- 个人信息内容 -->
      <div class="profile-content">
        <!-- 个人信息卡片 -->
        <el-card class="profile-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">基本信息</span>
              <el-button type="primary" size="small" @click="handleEdit">
                <el-icon><Edit /></el-icon>
                编辑信息
              </el-button>
            </div>
          </template>
          
          <div class="profile-info" v-loading="loading">
            <div class="info-row">
              <div class="info-item">
                <span class="info-label">用户名：</span>
                <span class="info-value">{{ userInfo.username || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">角色：</span>
                <el-tag :type="userInfo.role_id === 1 ? 'danger' : 'primary'">
                  {{ userInfo.role_name || '-' }}
                </el-tag>
              </div>
            </div>
            
            <div class="info-row">
              <div class="info-item">
                <span class="info-label">真实姓名：</span>
                <span class="info-value">{{ userInfo.real_name || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">状态：</span>
                <el-tag :type="userInfo.status === 1 ? 'success' : 'danger'">
                  {{ userInfo.status === 1 ? '启用' : '禁用' }}
                </el-tag>
              </div>
            </div>
            
            <div class="info-row">
              <div class="info-item">
                <span class="info-label">邮箱：</span>
                <span class="info-value">{{ userInfo.email || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">手机号：</span>
                <span class="info-value">{{ userInfo.phone || '-' }}</span>
              </div>
            </div>
            
            <div class="info-row">
              <div class="info-item">
                <span class="info-label">最后登录：</span>
                <span class="info-value">{{ userInfo.last_login_at || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">注册时间：</span>
                <span class="info-value">{{ userInfo.created_at || '-' }}</span>
              </div>
            </div>
          </div>
        </el-card>

        <!-- 密码修改卡片 -->
        <el-card class="password-card" shadow="hover">
          <template #header>
            <div class="card-header">
              <span class="card-title">密码管理</span>
              <el-button type="warning" size="small" @click="handleChangePassword">
                <el-icon><Lock /></el-icon>
                修改密码
              </el-button>
            </div>
          </template>
          
          <div class="password-info">
            <p class="password-tip">
              <el-icon><InfoFilled /></el-icon>
              为了您的账户安全，建议定期更换密码
            </p>
            <p class="password-rule">
              密码要求：至少6位字符，建议包含字母、数字和特殊字符
            </p>
          </div>
        </el-card>
      </div>
    </div>

    <!-- 编辑个人信息对话框 -->
    <el-dialog title="编辑个人信息" v-model="editDialogVisible" width="600px" :close-on-click-modal="false">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="editForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="editForm.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmitEdit" :loading="submitLoading">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog title="修改密码" v-model="passwordDialogVisible" width="500px" :close-on-click-modal="false">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="100px">
        <el-form-item label="当前密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" placeholder="请输入当前密码" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" placeholder="请再次输入新密码" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="passwordDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmitPassword" :loading="passwordLoading">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { Edit, Lock, InfoFilled } from "@element-plus/icons-vue";
import axios from "@/axios/index.js";

// 响应式数据
const loading = ref(false);
const submitLoading = ref(false);
const passwordLoading = ref(false);
const userInfo = ref({});

// 对话框控制
const editDialogVisible = ref(false);
const passwordDialogVisible = ref(false);

// 编辑表单
const editForm = reactive({
  username: "",
  real_name: "",
  email: "",
  phone: "",
});

const editFormRef = ref(null);

// 密码表单
const passwordForm = reactive({
  old_password: "",
  new_password: "",
  confirm_password: "",
});

const passwordFormRef = ref(null);

// 表单验证规则
const editRules = reactive({
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, message: "用户名长度不能少于3位", trigger: "blur" },
  ],
  email: [
    {
      validator: (rule, value, callback) => {
        if (value && !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value)) {
          callback(new Error("邮箱格式不正确"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
  phone: [
    {
      validator: (rule, value, callback) => {
        if (value && !/^1[3-9]\d{9}$/.test(value)) {
          callback(new Error("手机号格式不正确"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
});

const passwordRules = reactive({
  old_password: [
    { required: true, message: "请输入当前密码", trigger: "blur" },
  ],
  new_password: [
    { required: true, message: "请输入新密码", trigger: "blur" },
    { min: 6, message: "密码长度不能少于6位", trigger: "blur" },
  ],
  confirm_password: [
    { required: true, message: "请确认新密码", trigger: "blur" },
    {
      validator: (rule, value, callback) => {
        if (value !== passwordForm.new_password) {
          callback(new Error("两次输入的密码不一致"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
  ],
});

// 方法
const fetchProfile = async () => {
  try {
    loading.value = true;
    const data = await axios.get("account/profile");

    if (data.code === 200) {
      userInfo.value = data.data;
    } else {
      ElMessage.error(data.message || "获取个人信息失败");
    }
  } catch (error) {
    console.error("获取个人信息失败", error);
    ElMessage.error("获取个人信息失败");
  } finally {
    loading.value = false;
  }
};

const handleEdit = () => {
  Object.assign(editForm, {
    username: userInfo.value.username || "",
    real_name: userInfo.value.real_name || "",
    email: userInfo.value.email || "",
    phone: userInfo.value.phone || "",
  });
  editDialogVisible.value = true;
};

const handleChangePassword = () => {
  Object.assign(passwordForm, {
    old_password: "",
    new_password: "",
    confirm_password: "",
  });
  passwordDialogVisible.value = true;
};

const handleSubmitEdit = async () => {
  editFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        submitLoading.value = true;

        const data = await axios.put("account/profile/update", editForm);

        if (data.code === 200) {
          ElMessage.success("个人信息更新成功");
          editDialogVisible.value = false;
          
          // 如果用户名发生变化，需要更新本地存储的用户信息
          if (editForm.username !== userInfo.value.username) {
            const userInfoStr = localStorage.getItem("userInfo");
            if (userInfoStr) {
              try {
                const localUserInfo = JSON.parse(userInfoStr);
                localUserInfo.username = editForm.username;
                localStorage.setItem("userInfo", JSON.stringify(localUserInfo));
              } catch (e) {
                console.error("更新本地用户信息失败:", e);
              }
            }
          }
          
          fetchProfile();
        } else {
          ElMessage.error(data.message || "更新失败");
        }
      } catch (error) {
        console.error("更新个人信息失败", error);
        ElMessage.error("更新失败");
      } finally {
        submitLoading.value = false;
      }
    }
  });
};

const handleSubmitPassword = async () => {
  passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        passwordLoading.value = true;

        const data = await axios.put("account/profile/update", {
          username: userInfo.value.username,
          real_name: userInfo.value.real_name,
          email: userInfo.value.email,
          phone: userInfo.value.phone,
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password,
        });

        if (data.code === 200) {
          ElMessage.success("密码修改成功");
          passwordDialogVisible.value = false;
          Object.assign(passwordForm, {
            old_password: "",
            new_password: "",
            confirm_password: "",
          });
        } else {
          ElMessage.error(data.message || "密码修改失败");
        }
      } catch (error) {
        console.error("修改密码失败", error);
        ElMessage.error("密码修改失败");
      } finally {
        passwordLoading.value = false;
      }
    }
  });
};

// 生命周期
onMounted(() => {
  fetchProfile();
});
</script>

<style scoped>
.profile-center-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f9fafc;
  padding: 16px;
  border-radius: 8px;
}

.header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  border-bottom: 2px solid #ebeef5;
  padding-bottom: 16px;
}

.title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  position: relative;
  padding-left: 12px;
  margin: 0;
}

.title::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8%;
  height: 84%;
  width: 4px;
  background-color: #409eff;
  border-radius: 2px;
}

.content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-card,
.password-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.profile-info {
  min-height: 200px;
}

.info-row {
  display: flex;
  margin-bottom: 20px;
  gap: 40px;
}

.info-item {
  flex: 1;
  display: flex;
  align-items: center;
}

.info-label {
  font-weight: 500;
  color: #606266;
  min-width: 80px;
}

.info-value {
  color: #303133;
  margin-left: 10px;
}

.password-info {
  padding: 20px 0;
}

.password-tip {
  display: flex;
  align-items: center;
  color: #409eff;
  margin-bottom: 10px;
  font-size: 14px;
}

.password-tip .el-icon {
  margin-right: 8px;
}

.password-rule {
  color: #909399;
  font-size: 13px;
  margin: 0;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 768px) {
  .profile-center-page {
    padding: 10px;
  }
  
  .info-row {
    flex-direction: column;
    gap: 15px;
  }
  
  .info-item {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .info-value {
    margin-left: 0;
    margin-top: 5px;
  }
}
</style> 