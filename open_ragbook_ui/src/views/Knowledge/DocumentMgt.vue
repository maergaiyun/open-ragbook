<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import axios from '@/axios/index.js'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { UploadFilled, View, Document } from '@element-plus/icons-vue'

// 加载状态
const loading = ref(false)
// 当前选中的知识库
const currentDatabase = ref(null)
// 上传对话框可见性
const uploadDialogVisible = ref(false)
// 分块方式选项
const chunkingOptions = [
  { label: 'Token分块 (按Token数量)', value: 'token' },
  { label: '句子分块 (按句子边界)', value: 'sentence' },
  { label: '段落分块 (按段落边界)', value: 'paragraph' },
  { label: '固定长度分块 (按字符数)', value: 'fixed_length' },
  { label: '语义分块 (按语义相似度)', value: 'semantic' },
  { label: '递归分块 (递归分割)', value: 'recursive' }
]
// 知识库列表
const databaseList = ref([])
// 文档列表
const documentList = ref([])
// 文件列表（上传用）
const fileList = ref([])
// 每页显示数量
const pageSize = ref(10)
// 当前页码
const currentPage = ref(1)
// 总记录数
const totalDocuments = ref(0)

// 上传表单
const uploadForm = reactive({
  database_id: '',
  chunking_method: 'token',
  chunk_size: 500,
  similarity_threshold: 0.7,
  overlap_size: 100,
  file: null
})

// 上传表单验证规则
const uploadRules = {
  database_id: [{ required: true, message: '请选择知识库', trigger: 'change' }],
  chunking_method: [{ required: true, message: '请选择分块方式', trigger: 'change' }],
  chunk_size: [{ required: true, message: '请设置分块大小', trigger: 'blur' }]
}

// 上传表单引用
const uploadFormRef = ref(null)

// 是否显示分块大小滑块
const showChunkSizeSlider = computed(() => {
  return ['token', 'fixed_length', 'recursive'].includes(uploadForm.chunking_method)
})

// 分块大小标签
const chunkSizeLabel = computed(() => {
  switch (uploadForm.chunking_method) {
    case 'token':
      return 'Token数量'
    case 'fixed_length':
      return '字符数量'
    case 'recursive':
      return '最大块大小'
    default:
      return '分块大小'
  }
})

// 分块大小范围
const chunkSizeRange = computed(() => {
  switch (uploadForm.chunking_method) {
    case 'token':
      return { min: 100, max: 2000, step: 50 }
    case 'fixed_length':
      return { min: 200, max: 5000, step: 100 }
    case 'recursive':
      return { min: 500, max: 4000, step: 100 }
    default:
      return { min: 100, max: 2000, step: 50 }
  }
})

// 文档分块对话框可见性
const chunksDialogVisible = ref(false)
// 当前查看的文档
const currentDocument = ref(null)
// 文档分块列表
const documentChunks = ref([])
// 分块分页
const chunkCurrentPage = ref(1)
const chunkPageSize = ref(10)
const totalChunks = ref(0)
// 分块加载状态
const chunksLoading = ref(false)

// 获取知识库列表
const fetchDatabaseList = async () => {
  try {
    loading.value = true
    const { data } = await axios.get('knowledge/database/list')
    databaseList.value = data.data
    // 如果有知识库且尚未选择知识库，则默认选择第一个
    if (databaseList.value.length > 0 && !currentDatabase.value) {
      currentDatabase.value = databaseList.value[0]
      await fetchDocumentList() // 等待文档列表加载完成
    } else {
      loading.value = false // 如果没有知识库或已选择，直接取消loading
    }
  } catch (error) {
    ElMessage.error('获取知识库列表失败：' + (error.message || '未知错误'))
    loading.value = false // 发生错误时取消loading
  }
}

// 获取文档列表
const fetchDocumentList = async () => {
  if (!currentDatabase.value) return

  try {
    loading.value = true
    const { data } = await axios.get(`knowledge/document/list`, {
      params: {
        database_id: currentDatabase.value.id,
        page: currentPage.value,
        page_size: pageSize.value
      }
    })
    documentList.value = data.data
    totalDocuments.value = data.total_records
  } catch (error) {
    ElMessage.error('获取文档列表失败：' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

// 处理知识库选择变化
const handleDatabaseChange = async (database) => {
  currentDatabase.value = database
  currentPage.value = 1
  await fetchDocumentList()
}

// 处理页码变化
const handleCurrentChange = async (page) => {
  currentPage.value = page
  await fetchDocumentList()
}

// 打开上传对话框
const openUploadDialog = () => {
  if (!currentDatabase.value) {
    ElMessage.warning('请先选择一个知识库')
    return
  }

  // 重置上传表单
  uploadForm.database_id = currentDatabase.value.id
  uploadForm.chunking_method = 'token'
  uploadForm.chunk_size = 500
  uploadForm.similarity_threshold = 0.7
  uploadForm.overlap_size = 100
  uploadForm.file = null
  fileList.value = []

  uploadDialogVisible.value = true
}

// 处理文件变化
const handleFileChange = (uploadFile, uploadFiles) => {
  // 检查文件类型
  const allowedTypes = ['txt']
  const fileExtension = uploadFile.name.split('.').pop().toLowerCase()
  
  if (!allowedTypes.includes(fileExtension)) {
    ElMessage.error('只支持上传 .txt 格式的文件')
    return false
  }
  
  // 检查文件大小 (5MB = 5 * 1024 * 1024 bytes)
  const maxSize = 5 * 1024 * 1024
  if (uploadFile.size > maxSize) {
    ElMessage.error('文件大小不能超过 5MB')
    return false
  }
  
  fileList.value = uploadFiles
  uploadForm.file = uploadFile.raw
}

// 移除文件
const handleFileRemove = () => {
  fileList.value = []
  uploadForm.file = null
}

// 上传文档
const handleUpload = async () => {
  if (!uploadFormRef.value) return

  try {
    await uploadFormRef.value.validate()

    if (!uploadForm.file) {
      ElMessage.warning('请选择要上传的文件')
      return
    }

    // 创建FormData对象
    const formData = new FormData()
    formData.append('database_id', uploadForm.database_id)
    formData.append('chunking_method', uploadForm.chunking_method)
    formData.append('chunk_size', uploadForm.chunk_size)
    
    // 根据分块方式添加特殊参数
    if (uploadForm.chunking_method === 'semantic') {
      formData.append('similarity_threshold', uploadForm.similarity_threshold)
    }
    if (uploadForm.chunking_method === 'recursive') {
      formData.append('overlap_size', uploadForm.overlap_size)
    }
    
    formData.append('file', uploadForm.file)

    // 显示全屏加载中
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '文档上传并处理中...',
      background: 'rgba(0, 0, 0, 0.7)'
    })

    try {
      await axios.post('knowledge/document/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      ElMessage.success('文档上传成功')
      uploadDialogVisible.value = false

      // 刷新知识库列表，更新文档数量
      await fetchDatabaseList()

      // 刷新文档列表
      fetchDocumentList()
    } finally {
      loadingInstance.close()
    }
  } catch (error) {
    ElMessage.error('上传失败：' + (error.message || '未知错误'))
  }
}

// 删除文档
const handleDeleteDocument = (document) => {
  ElMessageBox.confirm(
    `确认删除文档 "${document.title || document.filename}"？删除后不可恢复！`,
    '警告',
    {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'error'
    }
  )
    .then(async () => {
      loading.value = true
      try {
        await axios.delete(`knowledge/document/${document.id}`)
        ElMessage.success('删除成功')

        // 刷新知识库列表，更新文档数量
        await fetchDatabaseList()

        // 刷新文档列表
        fetchDocumentList()
      } catch (error) {
        ElMessage.error('删除失败：' + (error.message || '未知错误'))
      } finally {
        loading.value = false
      }
    })
    .catch(() => { })
}

// 格式化文件大小
const formatFileSize = (size) => {
  if (size < 1024) {
    return size + ' B'
  } else if (size < 1024 * 1024) {
    return (size / 1024).toFixed(2) + ' KB'
  } else if (size < 1024 * 1024 * 1024) {
    return (size / (1024 * 1024)).toFixed(2) + ' MB'
  } else {
    return (size / (1024 * 1024 * 1024)).toFixed(2) + ' GB'
  }
}

// 查看文档分块
const viewDocumentChunks = async (document) => {
  currentDocument.value = document
  chunkCurrentPage.value = 1
  chunksDialogVisible.value = true
  documentChunks.value = []
  await fetchDocumentChunks()
}

// 获取文档分块
const fetchDocumentChunks = async () => {
  if (!currentDocument.value) return

  try {
    chunksLoading.value = true
    const { data } = await axios.get(`knowledge/document/${currentDocument.value.id}/chunks`, {
      params: {
        page: chunkCurrentPage.value,
        page_size: chunkPageSize.value
      }
    })
    console.log(data)
    documentChunks.value = data?.chunks || []
    totalChunks.value = data?.total_records || currentDocument.value?.chunk_count || 0
  } catch (error) {
    documentChunks.value = []
    ElMessage.error('获取文档分块失败：' + (error.message || '未知错误'))
  } finally {
    chunksLoading.value = false
  }
}

// 处理分块页码变化
const handleChunkPageChange = (page) => {
  chunkCurrentPage.value = page
  fetchDocumentChunks()
}

onMounted(async () => {
  await fetchDatabaseList()
})
</script>

<template>
  <div class="document-manager-container">
    <div class="header">
      <div class="title">文档管理</div>
    </div>

    <div class="content-container" v-loading="loading">
      <!-- 左侧知识库列表 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>知识库列表</h3>
        </div>
        <div class="database-list">
          <div v-if="databaseList.length === 0" class="empty-state">
            <div class="empty-icon">📚</div>
            <div class="empty-text">暂无知识库</div>
          </div>
          <el-card v-for="db in databaseList" :key="db.id" class="database-card"
            :class="{ active: currentDatabase && currentDatabase.id === db.id }" @click="handleDatabaseChange(db)">
            <div class="database-info">
              <h4>{{ db.name }}</h4>
              <div class="database-detail">
                <span>文档数: {{ db.doc_count || 0 }}</span>
                <span>向量维度: {{ db.vector_dimension }}</span>
              </div>
            </div>
          </el-card>
        </div>
      </div>

      <!-- 右侧文档列表和上传区域 -->
      <div class="main-content">
        <div class="documents-header">
          <h3>{{ currentDatabase ? currentDatabase.name : '请选择知识库' }} - 文档列表</h3>
          <el-button type="primary" :icon="UploadFilled" @click="openUploadDialog" :disabled="!currentDatabase">
            上传文档
          </el-button>
        </div>

        <div class="documents-list">
          <div v-if="documentList.length === 0" class="empty-state">
            <div class="empty-icon">📄</div>
            <div class="empty-text">暂无文档</div>
            <div class="empty-hint">点击右上角"上传文档"按钮添加文档</div>
          </div>
          <el-table v-else :data="documentList" style="width: 100%">
            <el-table-column prop="filename" label="文件名" min-width="200"></el-table-column>
            <el-table-column prop="file_type" label="文件类型" width="120"></el-table-column>
            <el-table-column label="文件大小" width="120">
              <template #default="{ row }">
                {{ formatFileSize(row.file_size) }}
              </template>
            </el-table-column>
            <el-table-column prop="chunk_count" label="分块数量" width="120">
              <template #default="{ row }">
                <el-tag type="success" effect="plain" class="chunk-count-tag">
                  {{ row.chunk_count || 0 }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="create_time" label="上传时间" width="180"></el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{ row }">
                <div class="table-actions">
                  <el-button size="small" type="primary" plain :icon="View" @click="viewDocumentChunks(row)"
                    :disabled="!row.chunk_count" class="action-button">
                    查看分块
                  </el-button>
                  <el-button size="small" type="danger" :icon="Document" @click="handleDeleteDocument(row)"
                    class="action-button">
                    删除
                  </el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination" v-if="documentList.length > 0">
            <el-pagination layout="total, prev, pager, next" :total="totalDocuments" :current-page="currentPage"
              :page-size="pageSize" @current-change="handleCurrentChange" />
          </div>
        </div>
      </div>
    </div>

    <!-- 上传文档对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传文档" width="600px" destroy-on-close>
      <el-form ref="uploadFormRef" :model="uploadForm" :rules="uploadRules" label-width="100px">
        <el-form-item label="选择知识库" prop="database_id">
          <el-select v-model="uploadForm.database_id" placeholder="请选择知识库">
            <el-option v-for="db in databaseList" :key="db.id" :label="db.name" :value="db.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="分块方式" prop="chunking_method">
          <el-select v-model="uploadForm.chunking_method" placeholder="请选择分块方式">
            <el-option v-for="option in chunkingOptions" :key="option.value" :label="option.label"
              :value="option.value" />
          </el-select>
        </el-form-item>

        <el-form-item v-if="showChunkSizeSlider" :label="chunkSizeLabel" prop="chunk_size">
          <el-slider 
            v-model="uploadForm.chunk_size" 
            :min="chunkSizeRange.min" 
            :max="chunkSizeRange.max" 
            :step="chunkSizeRange.step" 
            show-input 
            show-stops 
          />
          <span class="chunk-size-tip">{{ chunkSizeLabel }}: {{ uploadForm.chunk_size }}</span>
        </el-form-item>

        <!-- 语义分块特殊参数 -->
        <el-form-item v-if="uploadForm.chunking_method === 'semantic'" label="相似度阈值">
          <el-slider 
            v-model="uploadForm.similarity_threshold" 
            :min="0.1" 
            :max="0.9" 
            :step="0.1" 
            show-input 
          />
          <span class="chunk-size-tip">相似度阈值: {{ uploadForm.similarity_threshold }}</span>
        </el-form-item>

        <!-- 递归分块特殊参数 -->
        <el-form-item v-if="uploadForm.chunking_method === 'recursive'" label="重叠大小">
          <el-slider 
            v-model="uploadForm.overlap_size" 
            :min="0" 
            :max="500" 
            :step="50" 
            show-input 
          />
          <span class="chunk-size-tip">重叠字符数: {{ uploadForm.overlap_size }}</span>
        </el-form-item>

        <el-form-item label="选择文件">
          <el-upload class="upload-file" :auto-upload="false" :limit="1" :on-change="handleFileChange"
            :on-remove="handleFileRemove" :file-list="fileList" accept=".txt">
            <el-button type="primary">选择文件</el-button>
            <template #tip>
              <div class="el-upload__tip">仅支持上传 .txt 格式文件，大小不超过 5MB</div>
            </template>
          </el-upload>
        </el-form-item>
      </el-form>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="uploadDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleUpload">上传</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 文档分块查看对话框 -->
    <el-dialog v-model="chunksDialogVisible" :title="currentDocument ? `${currentDocument.filename} - 分块详情` : '分块详情'"
      width="60%" destroy-on-close class="chunks-dialog">
      <div v-if="currentDocument" class="chunks-dialog-header">
        <div class="chunks-info">
          <div class="info-item">
            <span class="info-label">文件类型:</span>
            <el-tag size="small" effect="plain">{{ currentDocument.file_type || '-' }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">文件大小:</span>
            <span>{{ formatFileSize(currentDocument.file_size || 0) }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">分块数量:</span>
            <el-tag type="success" size="small">{{ currentDocument.chunk_count || 0 }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">上传时间:</span>
            <span>{{ currentDocument.create_time || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="chunks-content" v-loading="chunksLoading">
        <template v-if="documentChunks && documentChunks.length > 0">
          <div v-for="(chunk, index) in documentChunks" :key="chunk.id || index" class="chunk-card">
            <div class="chunk-header">
              <div class="chunk-index">
                分块 #{{ (chunkCurrentPage - 1) * chunkPageSize + index + 1 }}
              </div>
              <div class="chunk-id">ID: {{ chunk.id || '-' }}</div>
            </div>
            <div class="chunk-text">{{ chunk.content || '(无文本内容)' }}</div>
            <div class="chunk-meta">
              <span class="meta-item">
                <span class="meta-label">Token数:</span>
                <span>{{ chunk.token_count || '-' }}</span>
              </span>
              <span class="meta-item">
                <span class="meta-label">位置:</span>
                <span>{{ chunk.position || '-' }}</span>
              </span>
            </div>
          </div>
        </template>
        <div v-else class="empty-state">
          <div class="empty-icon">🧩</div>
          <div class="empty-text">暂无分块数据</div>
        </div>

        <!-- 分块分页 -->
        <div class="pagination chunks-pagination" v-if="totalChunks > 0">
          <el-pagination layout="total, sizes, prev, pager, next" :total="totalChunks" :current-page="chunkCurrentPage"
            :page-size="chunkPageSize" :page-sizes="[5, 10, 20, 50]" @current-change="handleChunkPageChange"
            @size-change="
              (size) => {
                chunkPageSize = size
                fetchDocumentChunks()
              }
            " />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.document-manager-container {
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
  display: flex;
  flex: 1;
  gap: 24px;
  height: calc(100vh - 140px);
  overflow: hidden;
}

.sidebar {
  width: 300px;
  min-width: 300px;
  background-color: white;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 100%;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  transition: all 0.3s ease;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #ebeef5;
  background-color: #f5f7fa;
  border-radius: 8px 8px 0 0;
}

.sidebar-header h3 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 16px;
}

.database-list {
  padding: 16px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  scrollbar-width: thin;
  /* 细滚动条 */
}

.database-card {
  margin-bottom: 16px;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
  overflow: hidden;
  border-radius: 6px;
}

.database-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.database-card.active {
  border-left: 4px solid #409eff;
  background-color: #ecf5ff;
}

.database-info h4 {
  margin: 0 0 10px 0;
  color: #303133;
  font-size: 15px;
}

.database-detail {
  display: flex;
  justify-content: space-between;
  color: #606266;
  font-size: 13px;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.documents-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 16px;
}

.documents-header h3 {
  margin: 0;
  color: #2c3e50;
  font-weight: 600;
  font-size: 18px;
}

.documents-header .el-button {
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
}

.documents-header .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.documents-list {
  margin-top: 16px;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  scrollbar-width: thin;
  /* 细滚动条 */
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.upload-file {
  width: 100%;
  border: 2px dashed #e4e7ed;
  border-radius: 8px;
  padding: 10px;
  transition: all 0.3s;
}

.upload-file:hover {
  border-color: #409eff;
}

.chunk-size-tip {
  display: block;
  margin-top: 8px;
  color: #606266;
  font-size: 13px;
  font-weight: 500;
}

:deep(.el-table) {
  flex: 1;
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

:deep(.el-pagination) {
  margin-top: auto;
  padding-top: 16px;
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

:deep(.el-button--danger) {
  transition: all 0.3s;
}

:deep(.el-button--danger:hover) {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(245, 108, 108, 0.2);
}

:deep(.el-select) {
  width: 100%;
}

/* 自定义空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-text {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
  color: #606266;
}

.empty-hint {
  font-size: 14px;
  color: #909399;
  text-align: center;
}

:deep(.el-empty) {
  padding: 40px 0;
}

.chunks-dialog {
  margin-top: 5vh;
}

.chunks-dialog-header {
  background-color: #f9fafc;
  padding: 16px;
  border-radius: 8px;
  margin-bottom: 20px;
  border: 1px solid #ebeef5;
}

.chunks-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  margin-right: 16px;
}

.info-label {
  color: #606266;
  font-weight: 500;
  margin-right: 8px;
}

.chunks-content {
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 4px;
}

.chunk-card {
  background-color: white;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  transition: all 0.3s;
}

.chunk-card:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
}

.chunk-index {
  font-weight: 600;
  color: #303133;
  font-size: 15px;
}

.chunk-id {
  color: #909399;
  font-size: 13px;
}

.chunk-text {
  padding: 12px;
  background-color: #f9fafc;
  border-radius: 4px;
  color: #303133;
  font-size: 14px;
  line-height: 1.6;
  margin-bottom: 12px;
  max-height: 200px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  border: 1px solid #ebeef5;
}

.chunk-meta {
  display: flex;
  justify-content: space-between;
  color: #606266;
  font-size: 13px;
}

.meta-item {
  display: flex;
  align-items: center;
}

.meta-label {
  font-weight: 500;
  margin-right: 4px;
  color: #909399;
}

.table-actions {
  display: flex;
  gap: 8px;
}

.action-button {
  padding: 6px 12px;
}

.chunk-count-tag {
  min-width: 50px;
  text-align: center;
  font-weight: 500;
}

.chunks-pagination {
  margin-top: 24px;
  border-top: 1px solid #ebeef5;
  padding-top: 16px;
}

:deep(.chunks-dialog .el-dialog__body) {
  padding: 16px 24px 24px;
}

:deep(.el-dialog__header) {
  padding: 16px 24px;
}

:deep(.el-tag) {
  border-radius: 4px;
}

:deep(.el-empty) {
  padding: 32px 0;
}

:deep(.el-loading-mask) {
  position: absolute;
  z-index: 100;
  border-radius: 8px;
  margin: 0;
  box-sizing: border-box;
}

/* 添加或修改分块内容相关的样式 */
.chunks-content {
  margin-top: 16px;
}

.chunk-card {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 16px;
  border: 1px solid #ebeef5;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  transition: all 0.3s;
}

.chunk-card:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.chunk-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  border-bottom: 1px dashed #e0e0e0;
  padding-bottom: 8px;
}

.chunk-index {
  font-weight: 600;
  color: #409eff;
  font-size: 14px;
}

.chunk-id {
  color: #909399;
  font-size: 13px;
}

.chunk-text {
  font-size: 14px;
  line-height: 1.6;
  color: #303133;
  margin: 12px 0;
  padding: 10px;
  background-color: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
  text-align: left;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: monospace;
  overflow-x: auto;
}

.chunk-meta {
  display: flex;
  margin-top: 8px;
  font-size: 13px;
  color: #606266;
}

.meta-item {
  margin-right: 16px;
  display: flex;
  align-items: center;
}

.meta-label {
  margin-right: 4px;
  font-weight: 500;
  color: #909399;
}

/* 对话框样式优化 */
.chunks-dialog {
  max-width: 90vw;
}

.chunks-dialog-header {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #ebeef5;
}

.chunks-info {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-label {
  margin-right: 8px;
  color: #909399;
  font-weight: 500;
}

.chunks-pagination {
  margin-top: 20px;
}

/* 响应式调整 */
@media (max-width: 768px) {
  .chunks-info {
    flex-direction: column;
    gap: 8px;
  }

  .chunk-header {
    flex-direction: column;
    gap: 4px;
  }
}

/* 滚动条样式统一 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}
</style>
