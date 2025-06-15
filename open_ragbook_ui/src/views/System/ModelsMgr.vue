<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from '@/axios/index.js'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Edit, Connection, RefreshRight, MoreFilled } from '@element-plus/icons-vue'

// 加载状态
const loading = ref(false)
// 服务商列表
const providers = ref([])
// 当前选中的服务商
const currentProvider = ref(null)
// 分页相关
const pagination = reactive({
  currentPage: 1,
  pageSize: 4, // 每页显示4个服务商（2行，每行2个）
  total: 0
})
// 当前页显示的服务商
const currentPageProviders = ref([])
// 模型配置分组
const modelsByProvider = ref({})
// 当前选中的模型配置
const currentModel = ref(null)

// 服务商弹窗
const providerDialogVisible = ref(false)
const providerDialogTitle = ref('')
const providerForm = reactive({
  id: '',
  name: '',
  code: '',
  desc: ''
})
const providerFormRef = ref(null)
const providerFormRules = {
  name: [{ required: true, message: '请输入服务商名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入服务商标识', trigger: 'blur' }]
}

// 模型配置弹窗
const modelDialogVisible = ref(false)
const modelDialogTitle = ref('')
const modelForm = reactive({
  id: '',
  provider_id: '',
  name: '',
  model_type: '',
  api_key: '',
  base_url: '',
  max_tokens: 4096,
  temperature: 0.7,
  is_default: false
})
const modelFormRef = ref(null)
const modelFormRules = {
  name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  model_type: [{ required: true, message: '请选择模型类型', trigger: 'change' }],
  api_key: [{ required: true, message: '请输入API Key', trigger: 'blur' }],
  base_url: [
    { required: true, message: '请输入Base URL', trigger: 'blur' },
    { 
      pattern: /^https?:\/\/.+/, 
      message: '请输入有效的URL地址（以http://或https://开头）', 
      trigger: 'blur' 
    }
  ],
  max_tokens: [
    { required: true, message: '请设置最大Token数', trigger: 'blur' },
    { type: 'number', message: '请输入数字', trigger: 'blur' }
  ],
  temperature: [
    { required: true, message: '请设置温度参数', trigger: 'blur' },
    { type: 'number', min: 0, max: 2, message: '温度应在0-2之间', trigger: 'blur' }
  ]
}

// 测试连接弹窗
const testDialogVisible = ref(false)
const testingConnection = ref(false)
const testPrompt = ref('你好，请简单介绍一下你自己。')
const testResult = ref({ status: '', message: '', data: null })
const testResponse = ref('')

// 预设模型类型（可根据实际情况扩展）
const modelTypeOptions = [
  { label: 'GPT-4', value: 'gpt-4' },
  { label: 'GPT-3.5 Turbo', value: 'gpt-3.5-turbo' },
  { label: 'DeepSeek Chat', value: 'deepseek-chat' },
  { label: 'DeepSeek Coder', value: 'deepseek-coder' },
  { label: 'ERNIE Bot 4.0', value: 'ernie-bot-4' },
  { label: 'ERNIE Bot', value: 'ernie-bot' },
  { label: 'Claude 3 Opus', value: 'claude-3-opus-20240229' },
  { label: 'Gemini Pro', value: 'gemini-pro' },
  { label: '自定义模型', value: 'custom' }
]

// 获取服务商和模型配置
const fetchProvidersAndModels = async () => {
  loading.value = true
  try {
    // 获取服务商
    const providerRes = await axios.get('/system/llm/providers')
    console.log(providerRes);

    // 处理后端统一响应格式
    providers.value = Array.isArray(providerRes.data) ? providerRes.data : []
    
    // 更新分页信息
    pagination.total = providers.value.length
    updateCurrentPageProviders()

    // 获取所有模型配置
    const modelRes = await axios.get('/system/llm/models')
    const allModels = Array.isArray(modelRes.data) ? modelRes.data : []

    // 分组
    const group = {}
    providers.value.forEach(p => {
      group[p.id] = []
    })

    allModels.forEach(m => {
      if (!group[m.provider_id]) group[m.provider_id] = []
      group[m.provider_id].push(m)
    })

    modelsByProvider.value = group
  } catch (e) {
    ElMessage.error('获取服务商或模型配置失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 服务商操作
const openAddProvider = () => {
  providerDialogTitle.value = '添加服务商'
  Object.assign(providerForm, { id: '', name: '', code: '', desc: '' })
  providerDialogVisible.value = true
}

const openEditProvider = (provider) => {
  providerDialogTitle.value = '编辑服务商'
  Object.assign(providerForm, provider)
  providerDialogVisible.value = true
}

const submitProvider = async () => {
  if (!providerFormRef.value) return
  await providerFormRef.value.validate()

  loading.value = true
  try {
    if (providerForm.id) {
      await axios.put(`/system/llm/providers/${providerForm.id}`, providerForm)
      ElMessage.success('服务商更新成功')
    } else {
      await axios.post('/system/llm/providers', providerForm)
      ElMessage.success('服务商添加成功')
    }
    providerDialogVisible.value = false
    await fetchProvidersAndModels()
  } catch (e) {
    ElMessage.error('操作失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

const deleteProvider = (provider) => {
  ElMessageBox.confirm(`确定要删除服务商"${provider.name}"？此操作不可恢复！`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    loading.value = true
    try {
      await axios.delete(`/system/llm/providers/${provider.id}`)
      ElMessage.success('服务商删除成功')
      await fetchProvidersAndModels()
    } catch (e) {
      ElMessage.error('删除失败')
      console.error(e)
    } finally {
      loading.value = false
    }
  })
}

// 模型配置操作
const openAddModel = (provider) => {
  modelDialogTitle.value = '添加模型配置'
  Object.assign(modelForm, {
    id: '',
    provider_id: provider.id,
    name: '',
    model_type: '',
    api_key: '',
    base_url: '',
    max_tokens: 4096,
    temperature: 0.7,
    is_default: false
  })
  modelDialogVisible.value = true
}

const openEditModel = (model) => {
  modelDialogTitle.value = '编辑模型配置'
  Object.assign(modelForm, model)
  modelDialogVisible.value = true
}

const submitModel = async () => {
  if (!modelFormRef.value) return
  await modelFormRef.value.validate()

  loading.value = true
  try {
    if (modelForm.id) {
      await axios.put(`/system/llm/models/${modelForm.id}`, modelForm)
      ElMessage.success('模型配置更新成功')
    } else {
      await axios.post('/system/llm/models', modelForm)
      ElMessage.success('模型配置添加成功')
    }
    modelDialogVisible.value = false
    fetchProvidersAndModels()
  } catch (e) {
    ElMessage.error('操作失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

const deleteModel = (model) => {
  ElMessageBox.confirm(`确定要删除模型"${model.name}"？此操作不可恢复！`, '警告', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(async () => {
    loading.value = true
    try {
      await axios.delete(`/system/llm/models/${model.id}`)
      ElMessage.success('模型配置删除成功')
      fetchProvidersAndModels()
    } catch (e) {
      ElMessage.error('删除失败')
      console.error(e)
    } finally {
      loading.value = false
    }
  })
}

const setAsDefault = async (model) => {
  if (model.is_default) return

  loading.value = true
  try {
    await axios.patch(`/system/llm/models/${model.id}/default`)
    ElMessage.success('已设为默认模型')
    fetchProvidersAndModels()
  } catch (e) {
    ElMessage.error('设置失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

// 测试模型连接
const openTestDialog = (model) => {
  currentModel.value = model
  testPrompt.value = '你好，请简单介绍一下你自己。'
  testResponse.value = ''
  testResult.value = { status: '', message: '', data: null }
  testDialogVisible.value = true
}

// 将数组分成每组n个元素的二维数组
const chunkArray = (array, size) => {
  if (!array) return []
  const result = []
  for (let i = 0; i < array.length; i += size) {
    result.push(array.slice(i, i + size))
  }
  return result
}

// 更新当前页显示的服务商
const updateCurrentPageProviders = () => {
  const start = (pagination.currentPage - 1) * pagination.pageSize
  const end = start + pagination.pageSize
  currentPageProviders.value = providers.value.slice(start, end)
}

// 分页改变处理
const handlePageChange = (page) => {
  pagination.currentPage = page
  updateCurrentPageProviders()
}

// 每页大小改变处理
const handleSizeChange = (size) => {
  pagination.pageSize = size
  pagination.currentPage = 1
  updateCurrentPageProviders()
}

const testModelConnection = async () => {
  if (!currentModel.value) return

  testingConnection.value = true
  testResponse.value = ''
  testResult.value = { status: '', message: '', data: null }

  try {
    // 确保prompt不为空，为空时使用默认值
    const promptToSend = testPrompt.value.trim() || '你好，请简单介绍一下你自己。'
    
    console.log('发送的prompt:', promptToSend) // 添加调试日志
    
    const response = await axios.post(`/system/llm/models/${currentModel.value.id}/test`, {
      prompt: promptToSend
    })

    testResult.value = {
      status: 'success',
      message: '连接成功',
      data: response.data
    }

    // 更智能的响应内容解析
    let responseContent = ''
    
    if (response.data) {
      // 尝试不同的响应格式
      if (response.data.response) {
        // 自定义格式: { response: "...", usage: {...} }
        responseContent = response.data.response
      } else if (response.data.content) {
        // OpenAI格式: { content: "..." }
        responseContent = response.data.content
      } else if (response.data.message) {
        // 通用格式: { message: "..." }
        responseContent = response.data.message
      } else if (response.data.choices && response.data.choices.length > 0) {
        // OpenAI API格式: { choices: [{ message: { content: "..." } }] }
        const choice = response.data.choices[0]
        if (choice.message && choice.message.content) {
          responseContent = choice.message.content
        } else if (choice.text) {
          responseContent = choice.text
        }
      } else if (response.data.result) {
        // 百度等格式: { result: "..." }
        responseContent = response.data.result
      } else if (response.data.text) {
        // 简单文本格式: { text: "..." }
        responseContent = response.data.text
      } else if (typeof response.data === 'string') {
        // 直接返回字符串
        responseContent = response.data
      } else {
        // 其他格式，显示完整JSON
        responseContent = JSON.stringify(response.data, null, 2)
      }
    }

    testResponse.value = responseContent || '模型返回了空响应'
  } catch (error) {
    testResult.value = {
      status: 'error',
      message: '连接失败: ' + (error.response?.data?.message || error.message || '未知错误'),
      data: error.response?.data
    }

    testResponse.value = error.response?.data?.message || error.message || '未知错误'
  } finally {
    testingConnection.value = false
  }
}

onMounted(() => {
  fetchProvidersAndModels()
})
</script>

<template>
  <div class="model-mgr-page" v-loading="loading">
    <div class="header">
      <div class="title">大模型管理</div>
      <el-button type="primary" :icon="Plus" @click="openAddProvider" class="header-button">添加服务商</el-button>
    </div>

    <div class="content-container">
      <!-- 服务商列表容器 -->
      <div class="providers-container">
        <el-row :gutter="24" class="provider-group-row">
          <el-col v-for="provider in currentPageProviders" :key="provider.id" :span="12" class="provider-group-col">
          <el-card shadow="hover" class="provider-card">
            <div class="provider-card-header">
              <div class="provider-info">
                <div class="provider-name">{{ provider.name }}</div>
                <div class="provider-desc">{{ provider.desc || '暂无描述' }}</div>
              </div>
              <div class="provider-actions">
                <el-button :icon="Edit" size="small" circle @click.stop="openEditProvider(provider)" />
                <el-button :icon="Delete" size="small" circle @click.stop="deleteProvider(provider)" />
              </div>
            </div>

            <div class="model-list">
              <el-empty v-if="!modelsByProvider[provider.id] || modelsByProvider[provider.id].length === 0"
                description="暂无模型配置" class="custom-empty">
                <div class="empty-hint">点击下方按钮添加第一个模型配置</div>
              </el-empty>

              <template v-else>
                <!-- 将模型分成一组组的行，每行两个模型 -->
                <div v-for="(chunk, index) in chunkArray(modelsByProvider[provider.id], 2)" :key="index"
                  class="model-row">
                  <el-row :gutter="16">
                    <el-col v-for="model in chunk" :key="model.id" :span="12">
                      <el-card shadow="never" class="model-card">
                        <div class="model-card-header">
                          <div class="model-name">{{ model.name }}</div>
                          <el-tag v-if="model.is_default" type="success" size="small">默认</el-tag>
                        </div>

                        <div class="model-meta">{{ model.model_type }}</div>
                        <div class="model-meta">API Key: <span class="sensitive-info">••••••{{ model.api_key?.slice(-4)
                        }}</span></div>

                        <div class="model-actions">
                          <el-button :icon="Connection" size="small" @click.stop="openTestDialog(model)">测试</el-button>
                          <el-button :icon="Edit" size="small" @click.stop="openEditModel(model)">编辑</el-button>
                          <el-button :icon="Delete" size="small" @click.stop="deleteModel(model)">删除</el-button>
                          <el-button v-if="!model.is_default" type="success" size="small" link
                            @click.stop="setAsDefault(model)">设为默认</el-button>
                        </div>
                      </el-card>
                    </el-col>
                  </el-row>
                </div>
              </template>

              <!-- 添加模型的按钮，无论有无模型都显示 -->
              <div class="add-model-btn-container">
                <el-button type="primary" @click="openAddModel(provider)" class="add-model-fixed-btn">
                  <el-icon>
                    <Plus />
                  </el-icon> 添加模型配置
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
      
      <!-- 分页组件 -->
      <div class="pagination-container" v-if="pagination.total > pagination.pageSize">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[2, 4, 6, 8]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
          background
        />
      </div>
    </div>

      <!-- 服务商弹窗 -->
      <el-dialog v-model="providerDialogVisible" :title="providerDialogTitle" width="580px" destroy-on-close>
        <el-form ref="providerFormRef" :model="providerForm" :rules="providerFormRules" label-width="120px">
          <el-form-item label="服务商名称" prop="name">
            <el-input v-model="providerForm.name" placeholder="如 OpenAI、百度等" />
          </el-form-item>
          <el-form-item label="标识" prop="code">
            <el-input v-model="providerForm.code" placeholder="如 openai、baidu，唯一英文标识" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="providerForm.desc" placeholder="可选，服务商描述" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="providerDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitProvider" :loading="loading">确定</el-button>
        </template>
      </el-dialog>

      <!-- 模型配置弹窗 -->
      <el-dialog v-model="modelDialogVisible" :title="modelDialogTitle" width="580px" destroy-on-close>
        <el-form ref="modelFormRef" :model="modelForm" :rules="modelFormRules" label-width="120px">
          <el-form-item label="模型名称" prop="name">
            <el-input v-model="modelForm.name" placeholder="请输入模型名称" />
          </el-form-item>
          <el-form-item label="模型类型" prop="model_type">
            <el-select v-model="modelForm.model_type" placeholder="请选择模型类型" style="width: 100%">
              <el-option v-for="item in modelTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="API Key" prop="api_key">
            <el-input v-model="modelForm.api_key" type="password" show-password placeholder="请输入API Key" />
          </el-form-item>
          <el-form-item label="Base URL" prop="base_url" required>
            <el-input v-model="modelForm.base_url" placeholder="请输入API端点地址，如：https://api.openai.com/v1" />
          </el-form-item>
          <el-form-item label="最大Token数" prop="max_tokens">
            <el-input-number v-model="modelForm.max_tokens" :min="1" :max="100000" :step="1024" style="width: 180px" />
          </el-form-item>
          <el-form-item label="温度参数" prop="temperature">
            <el-slider v-model="modelForm.temperature" :min="0" :max="2" :step="0.1" show-input />
            <div class="form-tip">较低的值使输出更确定，较高的值使输出更多样化</div>
          </el-form-item>
          <el-form-item label="设为默认">
            <el-switch v-model="modelForm.is_default" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="modelDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitModel" :loading="loading">确定</el-button>
        </template>
      </el-dialog>

      <!-- 测试连接弹窗 -->
      <el-dialog v-model="testDialogVisible" title="测试模型连接" width="600px" destroy-on-close>
        <div v-if="currentModel" class="test-dialog-content" v-loading="testingConnection">
          <div class="test-model-info">
            <div class="test-model-name">{{ currentModel.name }}</div>
            <div class="test-model-type">
              <el-tag size="small">{{ currentModel.model_type }}</el-tag>
            </div>
          </div>
          <div class="test-form">
            <el-form label-position="top">
              <el-form-item label="测试提示词">
                <el-input v-model="testPrompt" type="textarea" :rows="3" placeholder="输入测试提示词..."
                  :disabled="testingConnection" />
              </el-form-item>
            </el-form>
            <div class="test-actions">
              <el-button type="primary" :icon="Connection" @click="testModelConnection"
                :loading="testingConnection">测试连接</el-button>
              <el-button :icon="RefreshRight" @click="testPrompt = '你好，请简单介绍一下你自己。'">重置提示词</el-button>
            </div>
            <div v-if="testResult.status" :class="['test-result', testResult.status]">
              <div class="test-result-header">
                <el-tag :type="testResult.status === 'success' ? 'success' : 'danger'">
                  {{ testResult.status === 'success' ? '连接成功' : '连接失败' }}
                </el-tag>
              </div>
              <div v-if="testResponse" class="test-response">
                <div class="response-label">模型响应:</div>
                <div class="response-content">{{ testResponse }}</div>
              </div>
            </div>
          </div>
        </div>
        <template #footer>
          <el-button @click="testDialogVisible = false">关闭</el-button>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style scoped>
.model-mgr-page {
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

.providers-container {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden; /* 隐藏横向滚动条 */
  padding: 0 12px; /* 添加左右对称的padding */
  scrollbar-width: thin;
  scrollbar-color: #c1c1c1 #f1f1f1;
}

.providers-container::-webkit-scrollbar {
  width: 8px;
}

.providers-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.providers-container::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 10px;
}

.providers-container::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.pagination-container {
  display: flex;
  justify-content: flex-end; /* 改为右对齐 */
  padding: 0 0 5px 0;
}

/* 分页组件样式优化 */
:deep(.el-pagination) {
  --el-pagination-font-size: 14px;
  --el-pagination-bg-color: #f5f7fa;
  --el-pagination-text-color: #606266;
  --el-pagination-border-radius: 6px;
}

:deep(.el-pagination .btn-next),
:deep(.el-pagination .btn-prev) {
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  transition: all 0.3s;
}

:deep(.el-pagination .btn-next:hover),
:deep(.el-pagination .btn-prev:hover) {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

:deep(.el-pagination .el-pager li) {
  background: #f5f7fa;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  margin: 0 4px;
  transition: all 0.3s;
}

:deep(.el-pagination .el-pager li:hover) {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

:deep(.el-pagination .el-pager li.is-active) {
  background: #409eff;
  color: #fff;
  border-color: #409eff;
}

.header-button {
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
  flex-shrink: 0;
}

.header-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.provider-group-row {
  margin-top: 0;
}

.provider-group-col {
  margin-bottom: 36px;
}

.provider-card {
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  padding: 0;
  background: #fff;
  overflow: hidden;
  border: none;
  height: 520px;
  display: flex;
  flex-direction: column;
}

.provider-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border-bottom: 1px solid #f0f0f0;
  padding: 24px 28px 16px 28px;
  background: linear-gradient(to right, #f8f9ff, #ffffff);
  flex-shrink: 0;
  height: 90px;
  /* 固定头部高度 */
  box-sizing: border-box;
}

.provider-info {
  flex: 1;
}

.provider-name {
  font-size: 22px;
  font-weight: 600;
  color: #222;
}

.provider-desc {
  font-size: 13px;
  color: #888;
  margin-top: 6px;
}

.provider-actions {
  display: flex;
  gap: 12px;
}

.model-list {
  padding: 20px 28px 0 28px;
  flex: 1;
  overflow-y: auto;
  scrollbar-width: thin;
  height: calc(100% - 90px);
  /* 减去头部高度 */
  box-sizing: border-box;
  position: relative;
  /* 添加相对定位，作为添加按钮的参考 */
  display: flex;
  flex-direction: column;
}

.model-list::-webkit-scrollbar {
  width: 6px;
}

.model-list::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 10px;
}

.model-list::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 10px;
}

.model-list::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.model-card {
  border-radius: 12px;
  margin-bottom: 20px;
  background: #f8fafc;
  border: 1px solid #e6e8eb;
  transition: all 0.25s;
  padding: 16px;
  height: 100%;
}

.model-card:hover {
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08);
  transform: translateY(-4px);
  border-color: #d0e1fd;
}

.model-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 17px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.model-meta {
  font-size: 13px;
  color: #666;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.sensitive-info {
  font-family: monospace;
  letter-spacing: 1px;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
}

.add-model-btn-container {
  position: sticky;
  bottom: 0;
  background: linear-gradient(to bottom, rgba(255, 255, 255, 0), rgba(255, 255, 255, 1) 30%);
  padding: 20px 0 10px 0;
  margin-top: auto;
  /* 改为auto，确保按钮总是在底部 */
  text-align: center;
  width: 100%;
  z-index: 10;
  /* 确保按钮在最上层 */
}

.add-model-fixed-btn {
  margin: 0 auto;
  font-size: 15px;
  padding: 12px 20px;
  font-weight: 500;
  box-shadow: 0 4px 12px rgba(26, 115, 232, 0.25);
  transition: all 0.3s ease;
}

.add-model-fixed-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(26, 115, 232, 0.35);
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.test-dialog-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.test-model-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.test-model-name {
  font-size: 22px;
  font-weight: 600;
  color: #1a73e8;
  margin-bottom: 6px;
}

.test-model-type {
  display: flex;
  gap: 8px;
}

.test-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.test-actions {
  display: flex;
  gap: 16px;
}

.test-result {
  margin-top: 20px;
  padding: 20px;
  border-radius: 12px;
  background-color: #f8f8f8;
  border: 1px solid #e4e7ed;
}

.test-result.success {
  background-color: #f0f9eb;
  border-color: #e1f3d8;
}

.test-result.error {
  background-color: #fef0f0;
  border-color: #fde2e2;
}

.test-result-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.test-response {
  margin-top: 16px;
}

.response-label {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
  font-size: 15px;
}

.response-content {
  background-color: white;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #dcdfe6;
  font-family: monospace;
  white-space: pre-wrap;
  max-height: 220px;
  overflow-y: auto;
  line-height: 1.6;
  font-size: 14px;
  box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
  text-align: left;
}

/* 动画效果 */
.provider-card,
.model-card {
  transition: all 0.3s ease;
}

/* 空状态优化 */
:deep(.el-empty) {
  margin-bottom: 30px;
  padding: 30px 0;
}

:deep(.el-empty__image) {
  width: 90px;
  height: 90px;
}

:deep(.el-empty__description) {
  margin-top: 16px;
  color: #909399;
}

.custom-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 40px 0;
}

.empty-hint {
  font-size: 14px;
  color: #909399;
  margin-top: 10px;
  padding: 5px 15px;
  background-color: #f5f7fa;
  border-radius: 20px;
  border: 1px dashed #dcdfe6;
}

/* 添加响应式布局优化 */
@media (max-width: 1200px) {
  .provider-group-col {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .model-mgr-page {
    padding: 16px;
  }

  .provider-card-header {
    padding: 18px 20px 18px 20px;
  }

  .model-list {
    padding: 16px 20px 0 20px;
  }
}

/* 对话框样式优化 */
:deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
}

:deep(.el-dialog__header) {
  padding: 20px 24px;
  border-bottom: 1px solid #ebeef5;
  background: linear-gradient(to right, #f8f9ff, #ffffff);
}

:deep(.el-dialog__title) {
  font-weight: 700;
  font-size: 18px;
  color: #1a73e8;
}

:deep(.el-dialog__body) {
  padding: 28px;
}

:deep(.el-dialog__footer) {
  padding: 16px 24px;
  border-top: 1px solid #ebeef5;
  background: #f9fafc;
}

/* 按钮样式增强 */
:deep(.el-button--primary:hover) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}



:deep(.el-input-number) {
  border-radius: 4px;
}

/* 调整el-card的内部容器样式 */
:deep(.el-card__body) {
  padding: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 调整模型卡片行间距 */
.model-row {
  margin-bottom: 24px;
  /* 增加行间距 */
}

.model-row:last-child {
  margin-bottom: 30px;
  /* 底部留更多空间 */
}
</style>
