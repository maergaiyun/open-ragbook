<script setup>
import { ref, reactive, onMounted } from "vue";
import axios from "@/axios/index.js";
import { ElMessage, ElMessageBox } from "element-plus";
import { WarningFilled, Cpu, Link, Monitor, InfoFilled, Tools, Share } from '@element-plus/icons-vue';

const loading = ref(false);
const dialogVisible = ref(false);
const dialogTitle = ref("新建知识库");
const isEdit = ref(false);

const tableData = reactive({
  data: [],
  total_records: 0,
});

const currentPage = ref(1);

const searchForm = reactive({
  page: 1,
  page_size: 20,
});

const formData = reactive({
  id: "",
  name: "",
  embedding_model_id: null,
  vector_dimension: 1536,
  index_type: "HNSW",
  description: "",
});

// 自定义验证：检查知识库名称在当前用户下的唯一性
const validateKnowledgeName = async (rule, value, callback) => {
  if (!value || value.trim() === '') {
    callback(new Error('请输入知识库名称'));
    return;
  }
  
  // 编辑模式下，如果名称没有改变，则不需要验证
  if (isEdit.value && tableData.data.find(item => item.id === formData.id)?.name === value) {
    callback();
    return;
  }
  
  try {
    // 检查当前用户是否已有同名知识库
    const response = await axios.get('knowledge/database/check-name', {
      params: { name: value.trim() }
    });
    
    if (response.code === 200) {
      if (response.data.exists) {
        callback(new Error('您已有同名的知识库，请使用其他名称'));
      } else {
        callback();
      }
    } else {
      callback();
    }
  } catch (error) {
    // 如果检查接口出错，允许通过验证，由后端最终处理
    console.warn('检查知识库名称唯一性失败:', error);
    callback();
  }
};

const formRules = {
  name: [
    { required: true, message: "请输入知识库名称", trigger: "blur" },
    { validator: validateKnowledgeName, trigger: "blur" }
  ],
  embedding_model_id: [{ required: true, message: "请选择嵌入模型", trigger: "change" }],
  index_type: [{ required: true, message: "请选择索引类型", trigger: "change" }],
};

const formRef = ref(null);
const embeddingModels = ref([]);
const localModelStatus = ref(null); // 本地模型状态

const search = async () => {
  searchForm.page = 1;
  currentPage.value = 1;
  loading.value = true;
  try {
    await fetchList();
  } finally {
    loading.value = false;
  }
};

const fetchList = async () => {
  const { data } = await axios.get("knowledge/database/list", {
    params: searchForm,
  });

  tableData.data = data.data;
  tableData.total_records = data.total_records;
};

const handleCurrentChange = async (page) => {
  searchForm.page = page;
  currentPage.value = page;
  loading.value = true;
  try {
    await fetchList();
  } finally {
    loading.value = false;
  }
};

const refresh = async () => {
  ElMessageBox.confirm("刷新知识库列表, 确认刷新？", "提示", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(async () => {
      loading.value = true;
      await fetchList();
      ElMessage.success("刷新成功!");
    })
    .catch(() => { })
    .finally(() => {
      loading.value = false;
    });
};

const openDialog = (type, row = null) => {
  if (type === "add") {
    dialogTitle.value = "新建知识库";
    isEdit.value = false;
    // 重置表单
    Object.assign(formData, {
      id: "",
      name: "",
      embedding_model_id: null,
      vector_dimension: 1536,
      index_type: "HNSW",
      description: "",
    });
  } else {
    dialogTitle.value = "编辑知识库";
    isEdit.value = true;
    console.log("编辑知识库数据:", row);
    Object.assign(formData, {
      id: row.id,
      name: row.name,
      embedding_model_id: row.embedding_model_id,
      vector_dimension: row.vector_dimension,
      index_type: row.index_type,
      description: row.desc || "",
    });
    console.log("表单数据:", formData);
    console.log("可用嵌入模型:", embeddingModels.value);
    
    // 确保嵌入模型ID是数字类型
    if (formData.embedding_model_id) {
      formData.embedding_model_id = parseInt(formData.embedding_model_id);
    }
  }
  dialogVisible.value = true;
};

const handleEdit = (row) => {
  openDialog("edit", row);
};

const handleSubmit = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();

    loading.value = true;

    if (isEdit.value) {
      // 更新知识库
      // 编辑模式下只允许修改名称和描述，不允许修改嵌入模型
      const updateData = {
        name: formData.name,
        description: formData.description
      };
      console.log("更新知识库数据:", updateData);
      await axios.put(`knowledge/database/${formData.id}`, updateData);
      ElMessage.success("更新成功");
    } else {
      // 创建知识库 - 传递完整的表单数据
      const createData = {
        name: formData.name,
        description: formData.description,
        embedding_model_id: formData.embedding_model_id,
        vector_dimension: formData.vector_dimension,
        index_type: formData.index_type
      };
      console.log("=== 创建知识库调试信息 ===");
      console.log("表单数据 formData:", JSON.stringify(formData, null, 2));
      console.log("发送数据 createData:", JSON.stringify(createData, null, 2));
      console.log("embedding_model_id 类型:", typeof createData.embedding_model_id);
      console.log("embedding_model_id 值:", createData.embedding_model_id);
      console.log("========================");
      
      const response = await axios.post("knowledge/database", createData);
      console.log("后端响应:", response);
      ElMessage.success("创建成功");
    }

    dialogVisible.value = false;
    await fetchList();
  } catch (error) {
    console.error("提交失败:", error);
    if (error?.response?.data?.message) {
      ElMessage.error(error.response.data.message);
    } else if (error?.message) {
      ElMessage.error(error.message);
    } else {
      ElMessage.error("操作失败");
    }
  } finally {
    loading.value = false;
  }
};

const handleDelete = (row) => {
  ElMessageBox.confirm(`确认删除知识库 "${row.name}"？删除后不可恢复！`, "警告", {
    confirmButtonText: "确定删除",
    cancelButtonText: "取消",
    type: "error",
  })
    .then(async () => {
      loading.value = true;
      try {
        await axios.delete(`knowledge/database/${row.id}`);
        ElMessage.success("删除成功");
        await fetchList();
      } catch (error) {
        ElMessage.error("删除失败：" + (error.message || "未知错误"));
      } finally {
        loading.value = false;
      }
    })
    .catch(() => { });
};

// 加载嵌入模型列表
const loadEmbeddingModels = async () => {
  try {
    const response = await axios.get("system/embedding/models");
    console.log("嵌入模型响应:", response);
    if (response.code === 200) {
      // 处理新的分页数据结构
      let models = [];
      if (response.data && response.data.items) {
        // 新的分页格式
        models = response.data.items;
      } else if (Array.isArray(response.data)) {
        // 兼容旧的数组格式
        models = response.data;
      }
      
      // 只显示激活的模型
      embeddingModels.value = models.filter(model => model.is_active);
      console.log("可用的嵌入模型:", embeddingModels.value);
    }
  } catch (error) {
    console.error("加载嵌入模型失败:", error);
  }
};

// 加载本地模型状态
const loadLocalModelStatus = async () => {
  try {
    const response = await axios.get('/system/embedding/local/status');
    if (response.code === 200) {
      localModelStatus.value = response.data;
    }
  } catch (error) {
    console.error('获取本地模型状态失败:', error);
  }
};

// 检查本地模型是否已加载
const isLocalModelLoaded = (model) => {
  if (model.api_type !== 'local') return true; // 在线模型总是可用
  if (!localModelStatus.value || !localModelStatus.value.has_loaded_model) return false;
  return localModelStatus.value.current_model && localModelStatus.value.current_model.model_id === model.id;
};

// 获取当前用户ID
const getCurrentUserId = () => {
  const userInfo = localStorage.getItem('userInfo');
  return userInfo ? JSON.parse(userInfo).user_id : null;
};

// 获取当前选中的嵌入模型
const getCurrentEmbeddingModel = () => {
  if (!formData.embedding_model_id || !embeddingModels.value.length) return null;
  return embeddingModels.value.find(model => model.id === formData.embedding_model_id);
};

// 嵌入模型改变时的处理
const onEmbeddingModelChange = (modelId) => {
  const selectedModel = embeddingModels.value.find(model => model.id === modelId);
  if (selectedModel) {
    // 自动设置向量维度
    formData.vector_dimension = selectedModel.vector_dimension;
    
    // 根据模型类型和维度推荐索引类型
    if (selectedModel.vector_dimension <= 768) {
      formData.index_type = "FLAT"; // 小维度用精确检索
    } else if (selectedModel.vector_dimension <= 1536) {
      formData.index_type = "HNSW"; // 中等维度用HNSW
    } else {
      formData.index_type = "IVFFLAT"; // 大维度用IVFFLAT
    }
  }
};

onMounted(async () => {
  await Promise.all([
    search(),
    loadEmbeddingModels(),
    loadLocalModelStatus()
  ]);
});
</script>

<template>
  <div class="knowledge-manager-container">
    <div class="header">
      <div class="title">知识库管理</div>
    </div>

    <div class="container" v-loading="loading">
      <div class="filter">
        <div class="filter-buttons">
          <el-button type="primary" @click="openDialog('add')">新建知识库</el-button>
          <el-button type="primary" @click="refresh">刷新</el-button>
        </div>
        <div class="filter-pagination">
          <el-pagination size="small" layout="slot, prev, pager, next" :total="tableData.total_records"
            :current-page="currentPage" :page-size="20" @current-change="handleCurrentChange">
            <template #default>
              <span class="el-pagination__total is-first">
                共 {{ tableData.total_records }} 条
              </span>
            </template>
          </el-pagination>
        </div>
      </div>
      <el-table :data="tableData.data" border>
        <el-table-column type="index" label="#" width="80" />
        <el-table-column prop="name" label="知识库名称" />
        <el-table-column prop="desc" label="知识库描述" />
        <el-table-column prop="vector_dimension" label="向量维度" width="100" />
        <el-table-column prop="index_type" label="索引类型" width="120" />
        <el-table-column prop="doc_count" label="文档数量" width="100" />
        <el-table-column prop="username" label="创建人" width="120" />
        <el-table-column prop="create_time" label="创建时间" width="160" />
        <el-table-column prop="update_time" label="更新时间" width="160" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 新建/编辑知识库弹窗 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" destroy-on-close>
      <el-form ref="formRef" :model="formData" :rules="formRules" label-width="100px">
        <el-form-item label="知识库名称" prop="name">
          <el-input v-model="formData.name" placeholder="请输入知识库名称"></el-input>
          <div class="name-tip">
            <el-icon><InfoFilled /></el-icon>
            <span>知识库名称在您的账户下需要唯一，其他用户可以创建同名知识库</span>
          </div>
        </el-form-item>
        <el-form-item label="嵌入模型" prop="embedding_model_id">
          <template v-if="isEdit">
            <!-- 编辑模式下显示当前模型信息 -->
            <div class="current-model-display">
              <template v-if="getCurrentEmbeddingModel()">
                <div class="model-info-card">
                  <div class="model-header">
                    <div class="model-name-section">
                      <el-icon class="model-icon"><Cpu /></el-icon>
                      <span class="model-name">{{ getCurrentEmbeddingModel().name }}</span>
                    </div>
                    <div class="model-status">
                      <el-tag 
                        size="small" 
                        :type="getCurrentEmbeddingModel().api_type === 'online' ? 'primary' : 'success'"
                        effect="light"
                      >
                        <el-icon>
                          <Link v-if="getCurrentEmbeddingModel().api_type === 'online'" />
                          <Monitor v-else />
                        </el-icon>
                        {{ getCurrentEmbeddingModel().api_type === 'online' ? '在线模型' : '本地模型' }}
                      </el-tag>
                    </div>
                  </div>
                  <div class="model-details">
                    <div class="detail-item">
                      <span class="detail-label">向量维度</span>
                      <el-tag size="small" type="info" effect="plain">
                        {{ getCurrentEmbeddingModel().vector_dimension }}维
                      </el-tag>
                    </div>
                    <div class="detail-item" v-if="getCurrentEmbeddingModel().is_public && getCurrentEmbeddingModel().user_id !== getCurrentUserId()">
                      <span class="detail-label">模型类型</span>
                      <el-tag size="small" type="warning" effect="plain">
                        <el-icon><Share /></el-icon>
                        公共模型
                      </el-tag>
                    </div>
                  </div>
                  <div class="model-note">
                    <el-icon class="note-icon"><InfoFilled /></el-icon>
                    <span class="note-text">编辑模式下不允许修改嵌入模型</span>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="no-model-warning">
                  <div class="warning-header">
                    <el-icon class="warning-icon"><WarningFilled /></el-icon>
                    <span class="warning-title">嵌入模型不可用</span>
                  </div>
                  <div class="warning-content">
                    <p class="warning-desc">
                      当前知识库关联的嵌入模型 (ID: {{ formData.embedding_model_id }}) 可能已被删除或禁用
                    </p>
                    <p class="warning-suggestion">
                      <el-icon><Tools /></el-icon>
                      建议联系管理员检查模型状态
                    </p>
                  </div>
                </div>
              </template>
            </div>
          </template>
          <template v-else>
            <!-- 新建模式下的选择器 -->
            <el-select 
              v-model="formData.embedding_model_id" 
              placeholder="请选择嵌入模型" 
              @change="onEmbeddingModelChange"
              style="width: 100%"
            >
              <el-option 
                v-for="model in embeddingModels" 
                :key="model.id" 
                :label="`${model.name} (${model.vector_dimension}维)`" 
                :value="model.id"
                :disabled="model.api_type === 'local' && !isLocalModelLoaded(model)"
              >
                <div style="display: flex; justify-content: space-between; align-items: center;">
                  <span>{{ model.name }}</span>
                  <div>
                    <el-tag size="small" :type="model.api_type === 'online' ? 'primary' : 'info'">
                      {{ model.api_type === 'online' ? '在线' : '本地' }}
                    </el-tag>
                    <el-tag size="small" style="margin-left: 4px;">{{ model.vector_dimension }}维</el-tag>
                    <el-tag v-if="model.is_public && model.user_id !== getCurrentUserId()" 
                            size="small" type="warning" style="margin-left: 4px;">
                      公共
                    </el-tag>
                  </div>
                </div>
              </el-option>
            </el-select>
            <div class="dimension-tip">
              选择嵌入模型后，向量维度将自动设置
            </div>
          </template>
        </el-form-item>
        <el-form-item label="向量维度">
          <el-input-number 
            v-model="formData.vector_dimension" 
            :min="1" 
            :max="10000" 
            :disabled="true"
            style="width: 100%"
          />
          <span class="dimension-tip">向量维度由选择的嵌入模型自动确定</span>
        </el-form-item>
        <el-form-item label="索引类型">
          <el-input 
            v-model="formData.index_type" 
            disabled 
            style="width: 100%"
          />
          <span class="dimension-tip">
            <template v-if="formData.index_type === 'FLAT'">
              使用精确检索（FLAT），适合小维度向量（≤768维），检索精度最高但速度较慢
            </template>
            <template v-else-if="formData.index_type === 'HNSW'">
              使用HNSW索引，适合中等维度向量（≤1536维），平衡检索速度和精度
            </template>
            <template v-else-if="formData.index_type === 'IVFFLAT'">
              使用IVFFLAT索引，适合大维度向量（>1536维），检索速度快但精度略低
            </template>
          </span>
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="formData.description" type="textarea" placeholder="请输入知识库描述" :rows="6"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.knowledge-manager-container {
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

.filter {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  margin-bottom: 8px;
  padding: 8px;
  background-color: white;
}

.filter-buttons {
  display: flex;
  gap: 12px;
}

.filter-buttons .el-button {
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
}

.filter-buttons .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.filter-pagination {
  display: flex;
  justify-content: flex-end;
}

.filter-condition {
  display: flex;
  justify-content: start;
  align-items: center;
}

.title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  position: relative;
  padding-left: 12px;
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

.dimension-tip {
  display: block;
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
  margin-left: 0;
  font-weight: 500;
}

.select-filter {
  margin-left: 8px;
}

.year-form {
  display: flex;
  justify-content: start;
}

.container {
  position: relative;
  width: 100%;
  max-height: calc(100vh) !important;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background-color: white;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.container .el-table {
  height: calc(100vh - 240px);
  border-radius: 8px;
  overflow: hidden;
}

:deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}

:deep(.el-table th) {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #2c3e50;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background-color: #fafafa;
}

:deep(.el-table--enable-row-hover .el-table__body tr:hover > td) {
  background-color: #ecf5ff;
}

:deep(.el-button--danger) {
  transition: all 0.3s;
}

:deep(.el-button--danger:hover) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
}

:deep(.el-button--primary) {
  transition: all 0.3s;
}

:deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

:deep(.el-dialog) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-dialog__header) {
  background-color: #f5f7fa;
  padding: 16px 20px;
  margin: 0;
}

:deep(.el-dialog__body) {
  padding: 24px;
}

:deep(.el-dialog__footer) {
  border-top: 1px solid #ebeef5;
  padding: 16px 20px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
}

:deep(.el-pagination) {
  margin-top: auto;
  padding-top: 16px;
}

:deep(.el-select) {
  width: 100%;
}

.dialog-custom-title {
  position: absolute;
  top: 10px;
  left: 20px;
  font-size: 18px;
  font-weight: bold;
}

.dialog-form {
  margin-top: 58px;
}

.current-model-display {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.model-info-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 16px;
  background-color: #fafbfc;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
}

.model-info-card:hover {
  background-color: #f5f7fa;
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.model-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  margin-bottom: 12px;
}

.model-name-section {
  display: flex;
  align-items: center;
}

.model-icon {
  margin-right: 8px;
  color: #409eff;
  font-size: 18px;
}

.model-name {
  font-weight: 600;
  color: #2c3e50;
  font-size: 16px;
}

.model-status {
  display: flex;
  align-items: center;
}

.model-details {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  margin-bottom: 12px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-label {
  font-weight: 500;
  color: #606266;
  font-size: 13px;
}

.model-note {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: #f0f9ff;
  border: 1px solid #bfdbfe;
  border-radius: 4px;
  margin-top: 4px;
}

.note-icon {
  margin-right: 8px;
  color: #409eff;
}

.note-text {
  color: #409eff;
  font-size: 13px;
  font-weight: 500;
}

.no-model-warning {
  display: flex;
  flex-direction: column;
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
  border: 1px solid #fbc4c4;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(245, 108, 108, 0.1);
}

.warning-header {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.warning-icon {
  margin-right: 8px;
  color: #f56c6c;
  font-size: 18px;
}

.warning-title {
  font-weight: 600;
  color: #f56c6c;
  font-size: 16px;
}

.warning-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.warning-desc {
  color: #909399;
  font-size: 14px;
  margin: 0;
  line-height: 1.5;
}

.warning-suggestion {
  display: flex;
  align-items: center;
  color: #f56c6c;
  font-size: 13px;
  font-weight: 500;
  margin: 0;
}

.warning-suggestion .el-icon {
  margin-right: 6px;
}

.name-tip {
  display: flex;
  align-items: center;
  margin-top: 6px;
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
}

.name-tip .el-icon {
  margin-right: 6px;
  color: #909399;
  font-size: 14px;
}
</style>
