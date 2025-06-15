<template>
  <div class="recall-test-container">
    <!-- 页面标题 -->
    <div class="header">
      <div class="title">召回检索测试</div>
    </div>

    <div class="content-wrapper">
      <div class="content-container" v-loading="loading">
        <!-- 配置区域 -->
        <div class="config-section">
          <el-card class="config-card">
            <template #header>
              <div class="card-header">
                <span>检索配置</span>
              </div>
            </template>
            
            <el-form :model="testForm" :rules="formRules" ref="formRef" label-width="120px">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="选择知识库" prop="knowledge_id">
                    <el-select 
                      v-model="testForm.knowledge_id" 
                      placeholder="请选择知识库" 
                      style="width: 100%"
                      @change="onKnowledgeChange"
                    >
                      <el-option 
                        v-for="kb in knowledgeBases" 
                        :key="kb.id" 
                        :label="kb.name" 
                        :value="kb.id"
                      >
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                          <span>{{ kb.name }}</span>
                          <div>
                            <el-tag size="small" type="info">{{ kb.doc_count || 0 }}文档</el-tag>
                            <el-tag size="small" style="margin-left: 4px;">{{ kb.vector_dimension }}维</el-tag>
                          </div>
                        </div>
                      </el-option>
                    </el-select>
                  </el-form-item>
                </el-col>
                
                <el-col :span="12">
                  <el-form-item label="检索数量" prop="retrieve_count">
                    <el-input-number 
                      v-model="testForm.retrieve_count" 
                      :min="1" 
                      :max="20" 
                      style="width: 100%"
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="相似度阈值">
                    <el-slider 
                      v-model="testForm.similarity_threshold" 
                      :min="0.1" 
                      :max="0.9" 
                      :step="0.05" 
                      show-stops 
                      show-input 
                    />
                    <div class="param-desc">仅返回相似度高于此值的文档片段</div>
                  </el-form-item>
                </el-col>
                
                <el-col :span="12">
                  <el-form-item label="知识库信息">
                    <div v-if="selectedKnowledge" class="knowledge-info">
                      <div class="info-item">
                        <span class="info-label">向量维度:</span>
                        <span class="info-value">{{ selectedKnowledge.vector_dimension }}维</span>
                      </div>
                      <div class="info-item">
                        <span class="info-label">索引类型:</span>
                        <span class="info-value">{{ selectedKnowledge.index_type }}</span>
                      </div>
                      <div class="info-item">
                        <span class="info-label">文档数量:</span>
                        <span class="info-value">{{ selectedKnowledge.doc_count || 0 }}个</span>
                      </div>
                    </div>
                    <div v-else class="no-knowledge">请先选择知识库</div>
                  </el-form-item>
                </el-col>
              </el-row>
            </el-form>
          </el-card>
        </div>

        <!-- 查询区域 -->
        <div class="query-section">
          <el-card class="query-card">
            <template #header>
              <div class="card-header">
                <span>查询测试</span>
              </div>
            </template>
            
            <el-form :model="testForm" ref="queryFormRef">
              <el-form-item label="查询内容" prop="query">
                <el-input 
                  v-model="testForm.query" 
                  type="textarea" 
                  :rows="3" 
                  placeholder="请输入要检索的查询内容..."
                  maxlength="500"
                  show-word-limit
                />
              </el-form-item>
              
              <el-form-item>
                <el-button 
                  type="primary" 
                  @click="handleTest" 
                  :loading="testing"
                  :disabled="!testForm.knowledge_id || !testForm.query.trim()"
                >
                  <el-icon><Search /></el-icon>
                  开始检索测试
                </el-button>
                <el-button @click="handleClear">
                  <el-icon><RefreshLeft /></el-icon>
                  清空结果
                </el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </div>

        <!-- 结果区域 -->
        <div class="results-section" v-if="testResults.length > 0 || hasSearched">
          <el-card class="results-card">
            <template #header>
              <div class="card-header">
                <span>检索结果</span>
                <div class="result-stats" v-if="testResults.length > 0">
                  <el-tag type="success">找到 {{ testResults.length }} 个相关片段</el-tag>
                  <el-tag type="info" style="margin-left: 8px;">
                    平均相似度: {{ averageSimilarity.toFixed(3) }}
                  </el-tag>
                </div>
              </div>
            </template>
            
            <div class="results-content">
              <div v-if="testResults.length === 0 && hasSearched" class="no-results">
                <div class="no-results-icon">🔍</div>
                <div class="no-results-text">未找到相关内容</div>
                <div class="no-results-tip">
                  建议：
                  <ul>
                    <li>降低相似度阈值</li>
                    <li>尝试不同的查询关键词</li>
                    <li>检查知识库是否包含相关文档</li>
                  </ul>
                </div>
              </div>
              
              <div v-else class="results-list">
                <div 
                  v-for="(result, index) in testResults" 
                  :key="index" 
                  class="result-item"
                >
                  <div class="result-header">
                    <div class="result-rank">
                      <el-tag :type="getRankTagType(index)" size="small">
                        #{{ index + 1 }}
                      </el-tag>
                    </div>
                    <div class="result-score">
                      <span class="score-label">相似度:</span>
                      <span class="score-value" :class="getScoreClass(result.similarity)">
                        {{ result.similarity.toFixed(3) }}
                      </span>
                    </div>
                    <div class="result-source">
                      <el-tag size="small" type="info">{{ result.filename }}</el-tag>
                    </div>
                  </div>
                  
                  <div class="result-content">
                    <div class="content-text">{{ result.content }}</div>
                  </div>
                  
                  <div class="result-metadata" v-if="result.metadata">
                    <el-collapse>
                      <el-collapse-item title="查看元数据" name="metadata">
                        <pre class="metadata-content">{{ formatMetadata(result.metadata) }}</pre>
                      </el-collapse-item>
                    </el-collapse>
                  </div>
                </div>
              </div>
            </div>
          </el-card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, RefreshLeft } from '@element-plus/icons-vue'
import axios from '@/axios/index.js'

// 响应式数据
const loading = ref(false)
const testing = ref(false)
const hasSearched = ref(false)
const formRef = ref(null)
const queryFormRef = ref(null)

// 知识库列表
const knowledgeBases = ref([])

// 测试表单
const testForm = reactive({
  knowledge_id: null,
  query: '',
  retrieve_count: 5,
  similarity_threshold: 0.3
})

// 表单验证规则
const formRules = {
  knowledge_id: [
    { required: true, message: '请选择知识库', trigger: 'change' }
  ],
  retrieve_count: [
    { required: true, message: '请设置检索数量', trigger: 'blur' }
  ]
}

// 测试结果
const testResults = ref([])

// 计算属性
const selectedKnowledge = computed(() => {
  if (!testForm.knowledge_id) return null
  return knowledgeBases.value.find(kb => kb.id === testForm.knowledge_id)
})

const averageSimilarity = computed(() => {
  if (testResults.value.length === 0) return 0
  const sum = testResults.value.reduce((acc, result) => acc + result.similarity, 0)
  return sum / testResults.value.length
})

// 方法
const loadKnowledgeBases = async () => {
  try {
    loading.value = true
    const response = await axios.get('/knowledge/database/list')
    
    if (response.code === 200) {
      knowledgeBases.value = response.data.data || []
    } else {
      ElMessage.error('获取知识库列表失败')
    }
  } catch (error) {
    console.error('加载知识库列表失败:', error)
    ElMessage.error('获取知识库列表失败')
  } finally {
    loading.value = false
  }
}

const onKnowledgeChange = (knowledgeId) => {
  // 清空之前的结果
  testResults.value = []
  hasSearched.value = false
}

const handleTest = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
    
    if (!testForm.query.trim()) {
      ElMessage.warning('请输入查询内容')
      return
    }
    
    testing.value = true
    hasSearched.value = true
    
    // 调用检索测试API
    const response = await axios.post('/knowledge/recall/test', {
      knowledge_id: testForm.knowledge_id,
      query: testForm.query.trim(),
      retrieve_count: testForm.retrieve_count,
      similarity_threshold: testForm.similarity_threshold
    })
    
    if (response.code === 200) {
      testResults.value = response.data.results || []
      
      if (testResults.value.length > 0) {
        ElMessage.success(`检索完成，找到 ${testResults.value.length} 个相关片段`)
      } else {
        ElMessage.info('未找到相关内容，建议调整检索参数')
      }
    } else {
      ElMessage.error(response.message || '检索测试失败')
      testResults.value = []
    }
  } catch (error) {
    console.error('检索测试失败:', error)
    ElMessage.error('检索测试失败: ' + (error.message || '未知错误'))
    testResults.value = []
  } finally {
    testing.value = false
  }
}

const handleClear = () => {
  testResults.value = []
  hasSearched.value = false
  testForm.query = ''
}

const getRankTagType = (index) => {
  if (index === 0) return 'danger'  // 第一名用红色
  if (index === 1) return 'warning' // 第二名用橙色
  if (index === 2) return 'success' // 第三名用绿色
  return 'info' // 其他用蓝色
}

const getScoreClass = (similarity) => {
  if (similarity >= 0.8) return 'score-excellent'
  if (similarity >= 0.6) return 'score-good'
  if (similarity >= 0.4) return 'score-fair'
  return 'score-poor'
}

const formatMetadata = (metadata) => {
  if (typeof metadata === 'string') {
    try {
      return JSON.stringify(JSON.parse(metadata), null, 2)
    } catch {
      return metadata
    }
  }
  return JSON.stringify(metadata, null, 2)
}

// 生命周期
onMounted(() => {
  loadKnowledgeBases()
})
</script>

<style scoped>
.recall-test-container {
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

.content-wrapper {
  flex: 1;
  overflow: hidden;
}

.content-container {
  height: 100%;
  overflow-y: auto;
  padding-right: 4px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.config-section,
.query-section,
.results-section {
  width: 100%;
}

.config-card,
.query-card,
.results-card {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-radius: 8px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: #2c3e50;
}

.result-stats {
  display: flex;
  align-items: center;
}

.param-desc {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.knowledge-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
}

.info-label {
  font-weight: 500;
  color: #606266;
  margin-right: 6px;
}

.info-value {
  color: #303133;
}

.no-knowledge {
  color: #909399;
  font-style: italic;
}

.results-content {
  max-height: 500px;
  overflow-y: auto;
  padding-right: 4px;
}

.no-results {
  text-align: center;
  padding: 40px 20px;
}

.no-results-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.no-results-text {
  font-size: 16px;
  color: #606266;
  margin-bottom: 16px;
}

.no-results-tip {
  color: #909399;
  font-size: 14px;
  text-align: left;
  display: inline-block;
}

.no-results-tip ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.no-results-tip li {
  margin-bottom: 4px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.result-item {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  background-color: #fff;
  transition: all 0.3s ease;
}

.result-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  border-color: #409eff;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.result-rank {
  flex-shrink: 0;
}

.result-score {
  display: flex;
  align-items: center;
  gap: 4px;
}

.score-label {
  font-size: 12px;
  color: #909399;
}

.score-value {
  font-weight: 600;
  font-size: 14px;
}

.score-excellent {
  color: #67c23a;
}

.score-good {
  color: #409eff;
}

.score-fair {
  color: #e6a23c;
}

.score-poor {
  color: #f56c6c;
}

.result-source {
  margin-left: auto;
}

.result-content {
  margin-bottom: 12px;
}

.content-text {
  line-height: 1.6;
  color: #303133;
  background-color: #f8f9fa;
  padding: 12px;
  border-radius: 6px;
  border-left: 4px solid #409eff;
}

.result-metadata {
  margin-top: 8px;
}

.metadata-content {
  background-color: #f5f5f5;
  padding: 12px;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
  white-space: pre-wrap;
  word-break: break-all;
}

/* 滚动条样式 */
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

/* Element Plus 样式覆盖 */
:deep(.el-card__header) {
  background-color: #f5f7fa;
  padding: 16px 20px;
  border-bottom: 1px solid #ebeef5;
}

:deep(.el-card__body) {
  padding: 20px;
}

:deep(.el-form-item__label) {
  font-weight: 500;
  color: #606266;
}

:deep(.el-button) {
  transition: all 0.3s;
}

:deep(.el-button:hover) {
  transform: translateY(-1px);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .recall-test-container {
    padding: 10px;
  }
  
  .result-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  
  .result-source {
    margin-left: 0;
  }
  
  .content-container {
    gap: 16px;
  }
}
</style>
