<template>
  <div class="users-mgr-container">
    <!-- 页面标题 -->
    <div class="header">
      <h2>用户管理</h2>
    </div>

    <!-- 搜索和操作区域 -->
    <div class="search-bar">
      <div class="search-left">
        <el-input v-model="searchForm.search" placeholder="搜索用户名、姓名或邮箱" style="width: 280px; margin-right: 12px"
          clearable @keyup.enter="handleSearch">
          <template #prefix>
            <el-icon>
              <Search />
            </el-icon>
          </template>
        </el-input>

        <el-select v-model="searchForm.role_id" placeholder="选择角色" style="width: 140px; margin-right: 12px" clearable>
          <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
        </el-select>

        <el-select v-model="searchForm.status" placeholder="选择状态" style="width: 110px; margin-right: 12px" clearable>
          <el-option label="启用" :value="1" />
          <el-option label="禁用" :value="0" />
        </el-select>

        <el-button type="primary" @click="handleSearch">
          <el-icon>
            <Search />
          </el-icon>
          搜索
        </el-button>

        <el-button @click="handleReset">
          <el-icon>
            <Refresh />
          </el-icon>
          重置
        </el-button>
      </div>

      <div class="search-right">
        <el-button type="primary" @click="handleAdd">
          <el-icon>
            <Plus />
          </el-icon>
          新增用户
        </el-button>
      </div>
    </div>

    <!-- 用户列表 -->
    <el-table :data="userList" v-loading="loading" stripe style="width: 100%" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="50" />
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" show-overflow-tooltip />
      <el-table-column prop="real_name" label="真实姓名" show-overflow-tooltip />
      <el-table-column prop="email" label="邮箱" show-overflow-tooltip />
      <el-table-column prop="phone" label="手机号" />
      <el-table-column prop="role_name" label="角色" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.role_id === 1 ? 'danger' : 'primary'" size="small">
            {{ scope.row.role_name }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="scope">
          <el-tag :type="scope.row.status === 1 ? 'success' : 'danger'" size="small">
            {{ scope.row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" show-overflow-tooltip />
      <el-table-column prop="created_at" label="创建时间" show-overflow-tooltip />
      <el-table-column label="操作" width="140" fixed="right">
        <template #default="scope">
          <div class="operation-buttons">
            <el-button type="primary" size="small" @click="handleEdit(scope.row)">
              编辑
            </el-button>
            <el-button type="danger" size="small" @click="handleDelete(scope.row)" :disabled="scope.row.role_id === 1">
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize"
        :page-sizes="[10, 20, 50, 100]" :total="pagination.total" layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange" @current-change="handleCurrentChange" />
    </div>

    <!-- 新增/编辑用户对话框 -->
    <el-dialog :title="dialogTitle" v-model="dialogVisible" width="600px" :close-on-click-modal="false">
      <el-form :model="userForm" :rules="userRules" ref="userFormRef" label-width="100px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userForm.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" :placeholder="isEdit ? '留空则不修改密码' : '请输入密码'"
            show-password />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="userForm.real_name" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item label="手机号" prop="phone">
          <el-input v-model="userForm.phone" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="角色" prop="role_id">
          <el-select v-model="userForm.role_id" placeholder="请选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.id" :label="role.name" :value="role.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="userForm.status">
            <el-radio :label="1">启用</el-radio>
            <el-radio :label="0">禁用</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
            确定
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Search, Refresh, Plus } from "@element-plus/icons-vue";
import axios from "@/axios/index.js";

// 响应式数据
const loading = ref(false);
const submitLoading = ref(false);
const userList = ref([]);
const roles = ref([]);
const selectedUsers = ref([]);

// 搜索表单
const searchForm = reactive({
  search: "",
  role_id: "",
  status: "",
});

// 分页数据
const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0,
});

// 对话框相关
const dialogVisible = ref(false);
const isEdit = ref(false);
const currentUserId = ref(null);

// 用户表单
const userForm = reactive({
  username: "",
  password: "",
  email: "",
  real_name: "",
  phone: "",
  role_id: "",
  status: 1,
});

const userFormRef = ref(null);

// 表单验证规则
const userRules = reactive({
  username: [
    { required: true, message: "请输入用户名", trigger: "blur" },
    { min: 3, message: "用户名长度不能少于3位", trigger: "blur" },
  ],
  password: [
    {
      validator: (rule, value, callback) => {
        if (!isEdit.value && !value) {
          callback(new Error("请输入密码"));
        } else if (value && value.length < 6) {
          callback(new Error("密码长度不能少于6位"));
        } else {
          callback();
        }
      },
      trigger: "blur",
    },
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
  role_id: [{ required: true, message: "请选择角色", trigger: "change" }],
});

// 计算属性
const dialogTitle = computed(() => {
  return isEdit.value ? "编辑用户" : "新增用户";
});

// 方法
const fetchUsers = async () => {
  try {
    loading.value = true;
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm,
    };

    const data = await axios.get("account/users", { params });

    if (data.code === 200) {
      userList.value = data.data.users;
      pagination.total = data.data.total;
    } else {
      ElMessage.error(data.message || "获取用户列表失败");
    }
  } catch (error) {
    console.error("获取用户列表失败", error);
    ElMessage.error("获取用户列表失败");
  } finally {
    loading.value = false;
  }
};

const fetchRoles = async () => {
  try {
    const data = await axios.get("account/roles");
    if (data.code === 200) {
      roles.value = data.data.roles;
    }
  } catch (error) {
    console.error("获取角色列表失败", error);
  }
};

const handleSearch = () => {
  pagination.page = 1;
  fetchUsers();
};

const handleReset = () => {
  Object.assign(searchForm, {
    search: "",
    role_id: "",
    status: "",
  });
  pagination.page = 1;
  fetchUsers();
};

const handleAdd = () => {
  isEdit.value = false;
  currentUserId.value = null;
  resetUserForm();
  dialogVisible.value = true;
};

const handleEdit = (row) => {
  isEdit.value = true;
  currentUserId.value = row.id;
  Object.assign(userForm, {
    username: row.username,
    password: "",
    email: row.email || "",
    real_name: row.real_name || "",
    phone: row.phone || "",
    role_id: row.role_id,
    status: row.status,
  });
  dialogVisible.value = true;
};

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除用户 "${row.username}" 吗？`,
      "确认删除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      }
    );

    const data = await axios.delete(`account/users/${row.id}/delete`);

    if (data.code === 200) {
      ElMessage.success("删除成功");
      fetchUsers();
    } else {
      ElMessage.error(data.message || "删除失败");
    }
  } catch (error) {
    if (error !== "cancel") {
      console.error("删除用户失败", error);
      ElMessage.error("删除失败");
    }
  }
};

const handleSubmit = async () => {
  userFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        submitLoading.value = true;

        const submitData = { ...userForm };
        if (isEdit.value && !submitData.password) {
          delete submitData.password;
        }

        let data;
        if (isEdit.value) {
          data = await axios.put(`account/users/${currentUserId.value}/update`, submitData);
        } else {
          data = await axios.post("account/users/create", submitData);
        }

        if (data.code === 200) {
          ElMessage.success(isEdit.value ? "更新成功" : "创建成功");
          dialogVisible.value = false;
          fetchUsers();
        } else {
          ElMessage.error(data.message || "操作失败");
        }
      } catch (error) {
        console.error("提交失败", error);
        ElMessage.error("操作失败");
      } finally {
        submitLoading.value = false;
      }
    }
  });
};

const resetUserForm = () => {
  Object.assign(userForm, {
    username: "",
    password: "",
    email: "",
    real_name: "",
    phone: "",
    role_id: "",
    status: 1,
  });
  if (userFormRef.value) {
    userFormRef.value.clearValidate();
  }
};

const handleSelectionChange = (selection) => {
  selectedUsers.value = selection;
};

const handleSizeChange = (size) => {
  pagination.pageSize = size;
  pagination.page = 1;
  fetchUsers();
};

const handleCurrentChange = (page) => {
  pagination.page = page;
  fetchUsers();
};

// 生命周期
onMounted(() => {
  fetchRoles();
  fetchUsers();
});
</script>

<style scoped>
.users-mgr-container {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  color: #303133;
}

.search-bar {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-left {
  display: flex;
  align-items: center;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.operation-buttons {
  display: flex;
  gap: 8px;
}

/* 表格样式优化 */
:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table__header) {
  background-color: #fafafa;
}

:deep(.el-table th) {
  background-color: #fafafa !important;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table td) {
  border-bottom: 1px solid #f0f0f0;
}

:deep(.el-table__row:hover > td) {
  background-color: #f5f7fa !important;
}

/* 按钮样式优化 */
:deep(.el-button--primary) {
  background-color: #409eff;
  border-color: #409eff;
}

:deep(.el-button--primary:hover) {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

:deep(.el-button--danger) {
  background-color: #f56c6c;
  border-color: #f56c6c;
}

:deep(.el-button--danger:hover) {
  background-color: #f78989;
  border-color: #f78989;
}

/* 标签样式优化 */
:deep(.el-tag) {
  border-radius: 4px;
  font-size: 12px;
}

/* 对话框样式优化 */
:deep(.el-dialog) {
  border-radius: 8px;
}

:deep(.el-dialog__header) {
  padding: 20px 20px 10px;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-dialog__footer) {
  padding: 10px 20px 20px;
  border-top: 1px solid #f0f0f0;
}

/* 表单样式优化 */
:deep(.el-form-item__label) {
  color: #606266;
  font-weight: 500;
}

:deep(.el-input__wrapper) {
  border-radius: 6px;
}

:deep(.el-select .el-input__wrapper) {
  border-radius: 6px;
}

/* 分页样式优化 */
:deep(.el-pagination) {
  --el-pagination-font-size: 14px;
}

:deep(.el-pagination .el-pager li) {
  border-radius: 4px;
  margin: 0 2px;
}

:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next) {
  border-radius: 4px;
}
</style>
