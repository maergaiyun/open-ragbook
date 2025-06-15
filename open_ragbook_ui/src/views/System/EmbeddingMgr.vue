<template>
    <div class="embedding-mgr-page">
        <div class="header">
            <div class="title">嵌入模型管理</div>
            <div class="header-actions">
                <el-button type="primary" @click="showAddDialog">新增模型</el-button>
                <el-button type="primary" @click="refresh">刷新</el-button>
            </div>
        </div>

        <div class="content-container">
            <!-- 搜索和筛选 -->
            <div class="search-bar">
                <el-row :gutter="20">
                    <el-col :span="6">
                        <el-input v-model="searchForm.name" placeholder="搜索模型名称" clearable @input="handleSearch">
                            <template #prefix>
                                <el-icon>
                                    <Search />
                                </el-icon>
                            </template>
                        </el-input>
                    </el-col>
                    <el-col :span="4">
                        <el-select v-model="searchForm.model_type" placeholder="模型类型" clearable @change="handleSearch">
                            <el-option label="OpenAI" value="openai" />
                            <el-option label="Azure OpenAI" value="azure_openai" />
                            <el-option label="智谱AI" value="zhipu" />
                            <el-option label="百度千帆" value="baidu" />
                            <el-option label="通义千问" value="dashscope" />
                            <el-option label="讯飞星火" value="xunfei" />
                            <el-option label="腾讯混元" value="tencent" />
                            <el-option label="Sentence Transformers" value="sentence_transformers" />
                            <el-option label="Ollama" value="ollama" />
                        </el-select>
                    </el-col>
                    <el-col :span="4">
                        <el-select v-model="searchForm.api_type" placeholder="API类型" clearable @change="handleSearch">
                            <el-option label="在线API" value="online" />
                            <el-option label="本地部署" value="local" />
                        </el-select>
                    </el-col>
                    <el-col :span="4">
                        <el-select v-model="searchForm.is_public" placeholder="可见性" clearable @change="handleSearch">
                            <el-option label="公共模型" :value="1" />
                            <el-option label="私有模型" :value="0" />
                        </el-select>
                    </el-col>
                </el-row>
            </div>

            <!-- 数据表格 -->
            <el-table :data="tableData" v-loading="loading" style="width: 100%" @sort-change="handleSortChange">
                <el-table-column prop="name" label="模型名称" min-width="150" sortable="custom" show-overflow-tooltip>
                    <template #default="{ row }">
                        <div class="model-name">
                            <span>{{ row.name }}</span>
                            <el-tag v-if="row.is_preset" type="primary" size="small" style="margin-left: 8px;">
                                预设
                            </el-tag>
                            <el-tag v-if="!row.is_active" type="danger" size="small" style="margin-left: 8px;">
                                已禁用
                            </el-tag>
                        </div>
                    </template>
                </el-table-column>

                <el-table-column prop="model_type" label="模型类型" width="170">
                    <template #default="{ row }">
                        <el-tag :type="getModelTypeColor(row.model_type)">
                            {{ getModelTypeName(row.model_type) }}
                        </el-tag>
                    </template>
                </el-table-column>

                <el-table-column prop="api_type" label="API类型" width="90">
                    <template #default="{ row }">
                        <el-tag :type="row.api_type === 'online' ? 'primary' : 'info'">
                            {{ row.api_type === 'online' ? '在线' : '本地' }}
                        </el-tag>
                    </template>
                </el-table-column>

                <el-table-column prop="model_name" label="具体模型" width="200" show-overflow-tooltip>
                    <template #default="{ row }">
                        <span>{{ row.model_name || '-' }}</span>
                    </template>
                </el-table-column>

                <el-table-column prop="vector_dimension" label="向量维度" width="120" sortable="custom" />

                <el-table-column label="配置状态" width="100">
                    <template #default="{ row }">
                        <div>
                            <el-tag v-if="row.api_type === 'online'" :type="row.api_key ? 'success' : 'danger'"
                                size="small">
                                {{ row.api_key ? '已配置' : '待配置' }}
                            </el-tag>
                            <el-tag v-else :type="row.local_path || row.model_name ? 'success' : 'warning'" size="small">
                                {{ (row.local_path || row.model_name) ? '已配置' : '待配置' }}
                            </el-tag>
                        </div>
                    </template>
                </el-table-column>

                <el-table-column label="可见性" width="80">
                    <template #default="{ row }">
                        <el-tag :type="row.is_public ? 'success' : 'warning'" size="small">
                            {{ row.is_public ? '公共' : '私有' }}
                        </el-tag>
                    </template>
                </el-table-column>

                <el-table-column prop="username" label="创建者" width="100" show-overflow-tooltip />

                <el-table-column prop="create_time" label="创建时间" width="160" sortable="custom">
                    <template #default="{ row }">
                        {{ formatDateTime(row.create_time) }}
                    </template>
                </el-table-column>

                <el-table-column label="本地模型状态" width="130">
                    <template #default="{ row }">
                        <el-tag v-if="row.api_type === 'local'"
                            :type="getLocalModelStatus(row.id) === 'loaded' ? 'success' : 'info'">
                            {{ getLocalModelStatusText(row.id) }}
                        </el-tag>
                        <span v-else>-</span>
                    </template>
                </el-table-column>

                <el-table-column label="操作" width="160" fixed="right">
                    <template #default="{ row }">
                        <div class="operation-buttons">
                            <el-tooltip content="测试模型" placement="top">
                                <el-button type="primary" size="small" @click="testModel(row)"
                                    :loading="testingId === row.id" :disabled="!row.is_active">
                                    <el-icon>
                                        <VideoPlay />
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip v-if="canEditModel(row)" content="编辑模型" placement="top">
                                <el-button type="warning" size="small" @click="editModel(row)">
                                    <el-icon>
                                        <Edit />
                                    </el-icon>
                                </el-button>
                            </el-tooltip>
                            <el-tooltip v-if="canDeleteModel(row)" content="删除模型" placement="top">
                                <el-button type="danger" size="small" @click="deleteModel(row)">
                                    <el-icon>
                                        <Delete />
                                    </el-icon>
                                </el-button>
                            </el-tooltip>

                            <!-- 本地模型加载控制 -->
                            <template v-if="row.api_type === 'local'">
                                <el-tooltip v-if="getLocalModelStatus(row.id) !== 'loaded'"
                                    :content="getLoadButtonTooltip(row)" placement="top">
                                    <el-button size="small" type="success" @click="loadLocalModel(row.id)"
                                        :loading="loadingModels[row.id]" :disabled="!canLoadModel(row)">
                                        <el-icon>
                                            <Upload />
                                        </el-icon>
                                    </el-button>
                                </el-tooltip>
                                <el-tooltip v-else-if="getLocalModelStatus(row.id) === 'loaded'"
                                    :content="getUnloadButtonTooltip(row)" placement="top">
                                    <el-button size="small" type="warning" @click="unloadLocalModel()"
                                        :loading="unloadingModel" :disabled="!canUnloadModel(row)">
                                        <el-icon>
                                            <Download />
                                        </el-icon>
                                    </el-button>
                                </el-tooltip>
                            </template>
                        </div>
                    </template>
                </el-table-column>
            </el-table>

            <!-- 分页 -->
            <div class="pagination">
                <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.size"
                    :page-sizes="[10, 20, 50, 100]" :total="pagination.total"
                    layout="total, sizes, prev, pager, next, jumper" @size-change="handleSizeChange"
                    @current-change="handleCurrentChange" />
            </div>

            <!-- 新增/编辑对话框 -->
            <el-dialog :title="dialogTitle" v-model="dialogVisible" width="700px" @close="resetForm">
                <el-form ref="formRef" :model="form" :rules="formRules" label-width="120px">
                    <el-form-item label="模型名称" prop="name">
                        <el-input v-model="form.name" placeholder="请输入模型名称" />
                    </el-form-item>

                    <el-form-item label="选择模型" prop="preset_model">
                        <el-select v-model="form.preset_model" placeholder="请选择预设模型" style="width: 100%"
                            @change="onPresetModelChange" filterable>
                            <el-option-group label="在线API模型 (需要API密钥)">
                                <el-option label="OpenAI Ada-002 (1536维)" value="openai|text-embedding-ada-002" />
                                <el-option label="OpenAI 3-Small (1536维)" value="openai|text-embedding-3-small" />
                                <el-option label="OpenAI 3-Large (3072维)" value="openai|text-embedding-3-large" />
                                <el-option label="智谱AI Embedding-2 (1024维)" value="zhipu|embedding-2" />
                                <el-option label="百度千帆 Embedding-V1 (384维)" value="baidu|embedding-v1" />
                                <el-option label="通义千问 Text-Embedding-V1 (1536维)" value="dashscope|text-embedding-v1" />
                            </el-option-group>
                            <el-option-group label="本地部署模型 (需要指定路径)">
                                <el-option label="MiniLM-L6-v2 轻量级 (384维)" value="sentence_transformers|all-MiniLM-L6-v2" />
                                <el-option label="MiniLM-L12-v2 标准版 (384维)"
                                    value="sentence_transformers|all-MiniLM-L12-v2" />
                                <el-option label="BGE-Small-ZH 中文轻量 (512维)"
                                    value="sentence_transformers|BAAI/bge-small-zh-v1.5" />
                                <el-option label="BGE-Base-ZH 中文标准 (768维)"
                                    value="sentence_transformers|BAAI/bge-base-zh-v1.5" />
                                <el-option label="BGE-Large-ZH 中文高精度 (1024维)"
                                    value="sentence_transformers|BAAI/bge-large-zh-v1.5" />
                                <el-option label="M3E-Base 多语言 (768维)" value="sentence_transformers|moka-ai/m3e-base" />
                                <el-option label="E5-Base-v2 英文高质量 (768维)"
                                    value="sentence_transformers|intfloat/e5-base-v2" />
                                <el-option label="Ollama Nomic-Embed (768维)" value="ollama|nomic-embed-text" />
                            </el-option-group>
                        </el-select>
                        <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                            选择预设模型可自动配置所有技术参数，避免配置错误
                        </div>
                    </el-form-item>

                    <!-- 在线API配置 -->
                    <template v-if="form.api_type === 'online'">
                        <el-form-item label="API密钥" prop="api_key">
                            <el-input v-model="form.api_key" type="password" placeholder="请输入API密钥" show-password />
                            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                                请输入对应服务商的API密钥，其他参数已自动配置
                            </div>
                        </el-form-item>
                    </template>

                    <!-- 本地模型配置 -->
                    <template v-if="form.api_type === 'local'">
                        <el-form-item label="模型路径" prop="local_path" required
                            v-if="form.model_type === 'sentence_transformers'">
                            <el-input v-model="form.local_path" placeholder="请输入本地模型的完整路径" />
                            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                                请输入模型在服务器上的完整路径，如：/models/bge-large-zh-v1.5
                            </div>
                        </el-form-item>

                        <el-form-item label="服务地址" prop="api_url" v-if="form.model_type === 'ollama'">
                            <el-input v-model="form.api_url" placeholder="如: http://localhost:11434" />
                            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                                Ollama服务的访问地址
                            </div>
                        </el-form-item>

                        <el-form-item label="模型路径" prop="local_path" required v-if="form.model_type === 'ollama'">
                            <el-input v-model="form.local_path" placeholder="请输入Ollama模型路径" />
                            <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                                Ollama模型在服务器上的存储路径
                            </div>
                        </el-form-item>

                        <el-form-item v-if="form.preset_model">
                            <div class="model-params-display">
                                <div class="params-header">
                                    <span class="params-title">模型技术参数</span>
                                    <el-tag size="small" type="info">系统自动配置</el-tag>
                                </div>
                                <div class="params-content">
                                    <div class="param-item">
                                        <span class="param-label">向量维度:</span>
                                        <span class="param-value">{{ form.vector_dimension }}维</span>
                                        <span class="param-desc">由模型架构决定</span>
                                    </div>
                                    <div class="param-item">
                                        <span class="param-label">最大Token:</span>
                                        <span class="param-value">{{ form.max_tokens }}</span>
                                        <span class="param-desc">由模型训练决定</span>
                                    </div>
                                    <div class="param-item">
                                        <span class="param-label">批处理大小:</span>
                                        <span class="param-value">{{ form.batch_size }}</span>
                                        <span class="param-desc">已优化，可根据硬件调整</span>
                                    </div>
                                    <div class="param-item">
                                        <span class="param-label">超时时间:</span>
                                        <span class="param-value">{{ form.timeout }}秒</span>
                                        <span class="param-desc">请求超时设置</span>
                                    </div>
                                </div>
                            </div>
                        </el-form-item>
                    </template>

                    <!-- 显示模型参数（只读） -->
                    <el-form-item label="设置">
                        <div class="model-settings">
                            <div class="checkbox-with-notice">
                                <el-checkbox v-model="form.is_public" :disabled="form.api_type === 'local'">
                                    设为公共模型
                                </el-checkbox>
                                <div v-if="form.api_type === 'local'" class="local-model-notice">
                                    <el-icon class="notice-icon"><InfoFilled /></el-icon>
                                    <span>本地模型为服务器共享资源，自动设为公共</span>
                                </div>
                            </div>
                            <el-checkbox v-model="form.is_active">启用模型</el-checkbox>
                        </div>
                    </el-form-item>

                    <el-form-item label="描述" prop="description">
                        <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入模型描述" />
                    </el-form-item>
                </el-form>

                <template #footer>
                    <span class="dialog-footer">
                        <el-button @click="dialogVisible = false">取消</el-button>
                        <el-button type="primary" @click="submitForm" :loading="submitting">
                            确定
                        </el-button>
                    </span>
                </template>
            </el-dialog>

            <!-- 测试结果对话框 -->
            <el-dialog title="模型测试结果" v-model="testDialogVisible" width="600px">
                <div v-if="testResult">
                    <el-descriptions :column="1" border>
                        <el-descriptions-item label="测试文本">
                            {{ testResult.text }}
                        </el-descriptions-item>
                        <el-descriptions-item label="模型名称">
                            {{ testResult.model_name }}
                        </el-descriptions-item>
                        <el-descriptions-item label="模型类型">
                            {{ testResult.model_type }}
                        </el-descriptions-item>
                        <el-descriptions-item label="API类型">
                            <el-tag :type="testResult.api_type === 'local' ? 'success' : 'primary'" size="small">
                                {{ testResult.api_type === 'local' ? '本地模型' : '远程API' }}
                            </el-tag>
                        </el-descriptions-item>
                        <el-descriptions-item label="向量维度">
                            {{ testResult.vector_dimension }}
                        </el-descriptions-item>
                        <el-descriptions-item label="响应时间">
                            {{ testResult.response_time }}
                        </el-descriptions-item>
                        <el-descriptions-item v-if="testResult.device" label="运行设备">
                            <el-tag :type="testResult.device === 'cuda' ? 'warning' : 'info'" size="small">
                                {{ testResult.device === 'cuda' ? 'GPU' : 'CPU' }}
                            </el-tag>
                        </el-descriptions-item>
                        <el-descriptions-item v-if="testResult.usage" label="Token使用">
                            输入: {{ testResult.usage.prompt_tokens }}, 总计: {{ testResult.usage.total_tokens }}
                        </el-descriptions-item>
                        <el-descriptions-item label="向量示例">
                            <div style="max-height: 100px; overflow-y: auto; font-family: monospace; font-size: 12px;">
                                {{testResult.vector_sample.map(v => v.toFixed(4)).join(', ')}}
                            </div>
                        </el-descriptions-item>
                    </el-descriptions>
                </div>
            </el-dialog>

            <!-- 服务器资源检查对话框 -->
            <el-dialog v-model="resourceDialogVisible" title="服务器资源检查" width="600px" :show-close="false"
                :close-on-click-modal="false" :close-on-press-escape="false" class="resource-check-dialog">
                <div v-html="resourceHtml"></div>
                <template #footer>
                    <span class="dialog-footer">
                        <el-button @click="dialogRef?.handleCancel()">取消</el-button>
                        <el-button type="primary" @click="dialogRef?.handleConfirm()" 
                            :disabled="!dialogRef?.handleConfirm">
                            确定加载
                        </el-button>
                    </span>
                </template>
            </el-dialog>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, VideoPlay, Edit, Delete, Upload, Download, InfoFilled } from '@element-plus/icons-vue'
import api from '@/axios/index.js'

// 响应式数据
const loading = ref(false)
const submitting = ref(false)
const testingId = ref(null)
const tableData = ref([])
const dialogVisible = ref(false)
const testDialogVisible = ref(false)
const testResult = ref(null)
const formRef = ref()
const localModelStatus = ref({}) // 本地模型状态
const loadingModels = ref({}) // 正在加载的模型
const unloadingModel = ref(false) // 正在卸载模型
const currentLoadedModelId = ref(null) // 当前加载的模型ID
const resourceDialogVisible = ref(false) // 资源检查对话框
const dialogRef = ref(null) // 对话框引用
const resourceHtml = ref('') // 资源信息HTML

// 搜索表单
const searchForm = reactive({
    name: '',
    model_type: '',
    api_type: '',
    is_public: ''
})

// 分页
const pagination = reactive({
    page: 1,
    size: 20,
    total: 0
})

// 排序
const sortInfo = reactive({
    prop: '',
    order: ''
})

// 表单数据
const form = reactive({
    id: null,
    name: '',
    model_type: '',
    api_type: '',
    api_key: '',
    api_url: '',
    model_name: '',
    local_path: '',
    preset_model: '',
    vector_dimension: 1536,
    max_tokens: 8192,
    batch_size: 32,
    timeout: 30,
    is_public: false,
    is_active: true,
    description: ''
})

// 表单验证规则
const formRules = {
    name: [
        { required: true, message: '请输入模型名称', trigger: 'blur' }
    ],
    preset_model: [
        { required: true, message: '请选择预设模型', trigger: 'change' }
    ],
    api_key: [
        {
            validator: (rule, value, callback) => {
                if (form.api_type === 'online' && !value) {
                    callback(new Error('在线API类型需要提供API密钥'))
                } else {
                    callback()
                }
            },
            trigger: 'blur'
        }
    ],
    local_path: [
        {
            validator: (rule, value, callback) => {
                if (form.api_type === 'local' && !value) {
                    callback(new Error('本地模型需要提供模型路径'))
                } else {
                    callback()
                }
            },
            trigger: 'blur'
        }
    ]
}

// 计算属性
const dialogTitle = computed(() => {
    return form.id ? '编辑嵌入模型' : '新增嵌入模型'
})

const hasLocalModels = computed(() => {
    return tableData.value.some(item => item.api_type === 'local')
})

// 预设模型配置
const presetModelConfigs = {
    // 在线API模型
    'openai|text-embedding-ada-002': {
        name: 'OpenAI Ada-002',
        model_type: 'openai',
        api_type: 'online',
        api_url: 'https://api.openai.com/v1/embeddings',
        model_name: 'text-embedding-ada-002',
        vector_dimension: 1536,
        max_tokens: 8192,
        batch_size: 100,
        timeout: 30,
        description: 'OpenAI的经典嵌入模型，性能稳定，适合大多数场景'
    },
    'openai|text-embedding-3-small': {
        name: 'OpenAI 3-Small',
        model_type: 'openai',
        api_type: 'online',
        api_url: 'https://api.openai.com/v1/embeddings',
        model_name: 'text-embedding-3-small',
        vector_dimension: 1536,
        max_tokens: 8192,
        batch_size: 100,
        timeout: 30,
        description: 'OpenAI最新小型嵌入模型，速度快，成本低'
    },
    'openai|text-embedding-3-large': {
        name: 'OpenAI 3-Large',
        model_type: 'openai',
        api_type: 'online',
        api_url: 'https://api.openai.com/v1/embeddings',
        model_name: 'text-embedding-3-large',
        vector_dimension: 3072,
        max_tokens: 8192,
        batch_size: 50,
        timeout: 30,
        description: 'OpenAI最新大型嵌入模型，精度最高'
    },
    'zhipu|embedding-2': {
        name: '智谱AI Embedding-2',
        model_type: 'zhipu',
        api_type: 'online',
        api_url: 'https://open.bigmodel.cn/api/paas/v4/embeddings',
        model_name: 'embedding-2',
        vector_dimension: 1024,
        max_tokens: 8192,
        batch_size: 50,
        timeout: 30,
        description: '智谱AI嵌入模型，支持中英文，国内访问稳定'
    },
    'baidu|embedding-v1': {
        name: '百度千帆 Embedding-V1',
        model_type: 'baidu',
        api_type: 'online',
        api_url: 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/embeddings/embedding-v1',
        model_name: 'embedding-v1',
        vector_dimension: 384,
        max_tokens: 1000,
        batch_size: 16,
        timeout: 30,
        description: '百度千帆嵌入模型，适合中文场景'
    },
    'dashscope|text-embedding-v1': {
        name: '通义千问 Text-Embedding-V1',
        model_type: 'dashscope',
        api_type: 'online',
        api_url: 'https://dashscope.aliyuncs.com/api/v1/services/embeddings/text-embedding/text-embedding',
        model_name: 'text-embedding-v1',
        vector_dimension: 1536,
        max_tokens: 2048,
        batch_size: 25,
        timeout: 30,
        description: '阿里云通义千问嵌入模型，支持中英文'
    },

    // 本地模型
    'sentence_transformers|all-MiniLM-L6-v2': {
        name: 'MiniLM-L6-v2 (轻量级)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'all-MiniLM-L6-v2',
        vector_dimension: 384,
        max_tokens: 256,
        batch_size: 64,
        timeout: 60,
        description: '轻量级英文嵌入模型，384维，适合快速原型和资源受限环境，需要指定本地路径'
    },
    'sentence_transformers|all-MiniLM-L12-v2': {
        name: 'MiniLM-L12-v2 (标准版)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'all-MiniLM-L12-v2',
        vector_dimension: 384,
        max_tokens: 256,
        batch_size: 32,
        timeout: 60,
        description: '标准英文嵌入模型，384维，性能与效果平衡，需要指定本地路径'
    },
    'sentence_transformers|BAAI/bge-small-zh-v1.5': {
        name: 'BGE-Small-ZH (中文轻量)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'BAAI/bge-small-zh-v1.5',
        vector_dimension: 512,
        max_tokens: 512,
        batch_size: 32,
        timeout: 60,
        description: 'BGE中文轻量级模型，512维，适合中文文本处理，需要指定本地路径'
    },
    'sentence_transformers|BAAI/bge-base-zh-v1.5': {
        name: 'BGE-Base-ZH (中文标准)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'BAAI/bge-base-zh-v1.5',
        vector_dimension: 768,
        max_tokens: 512,
        batch_size: 32,
        timeout: 60,
        description: 'BGE中文标准模型，768维，中文理解能力强，需要指定本地路径'
    },
    'sentence_transformers|BAAI/bge-large-zh-v1.5': {
        name: 'BGE-Large-ZH (中文高精度)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'BAAI/bge-large-zh-v1.5',
        vector_dimension: 1024,
        max_tokens: 512,
        batch_size: 16,
        timeout: 120,
        description: 'BGE中文高精度模型，1024维，最佳中文理解效果，需要指定本地路径'
    },
    'sentence_transformers|moka-ai/m3e-base': {
        name: 'M3E-Base (多语言)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'moka-ai/m3e-base',
        vector_dimension: 768,
        max_tokens: 512,
        batch_size: 32,
        timeout: 60,
        description: 'M3E多语言模型，768维，支持中英文混合文本，需要指定本地路径'
    },
    'sentence_transformers|intfloat/e5-base-v2': {
        name: 'E5-Base-v2 (英文高质量)',
        model_type: 'sentence_transformers',
        api_type: 'local',
        model_name: 'intfloat/e5-base-v2',
        vector_dimension: 768,
        max_tokens: 512,
        batch_size: 32,
        timeout: 60,
        description: 'E5英文高质量模型，768维，英文理解能力优秀，需要指定本地路径'
    },
    'ollama|nomic-embed-text': {
        name: 'Ollama Nomic-Embed',
        model_type: 'ollama',
        api_type: 'local',
        api_url: 'http://localhost:11434',
        model_name: 'nomic-embed-text',
        vector_dimension: 768,
        max_tokens: 2048,
        batch_size: 16,
        timeout: 120,
        description: 'Ollama本地嵌入服务，需要先安装Ollama并指定模型路径'
    }
}

// 方法
const loadData = async () => {
    loading.value = true
    try {
        // 构建查询参数
        const params = {
            page: pagination.page,
            page_size: pagination.size
        }

        // 添加搜索条件
        if (searchForm.name) {
            params.name = searchForm.name
        }
        if (searchForm.model_type) {
            params.model_type = searchForm.model_type
        }
        if (searchForm.api_type) {
            params.api_type = searchForm.api_type
        }
        if (searchForm.is_public !== '') {
            params.is_public = searchForm.is_public
        }

        // 添加排序参数
        if (sortInfo.prop) {
            params.sort_field = sortInfo.prop
            params.sort_order = sortInfo.order === 'ascending' ? 'asc' : 'desc'
        }

        const response = await api.get('/system/embedding/models', { params })
        console.log('嵌入模型API响应:', response);

        if (response.code === 200) {
            const data = response.data

            // 处理新的分页数据结构
            if (data.items && Array.isArray(data.items)) {
                tableData.value = data.items
                pagination.total = data.total || 0
                pagination.page = data.page || 1
                pagination.size = data.page_size || 20
            } else if (Array.isArray(data)) {
                // 兼容旧的数据结构
                tableData.value = data
                pagination.total = data.length
            } else {
                console.warn('API返回的data格式不正确:', data)
                tableData.value = []
                pagination.total = 0
            }

            console.log('加载的嵌入模型数据:', tableData.value)

            // 加载本地模型状态
            await loadLocalModelStatus()
        } else {
            ElMessage.error(response.message || '获取数据失败')
            tableData.value = []
            pagination.total = 0
        }
    } catch (error) {
        console.error('获取嵌入模型列表失败:', error)
        ElMessage.error('获取数据失败')
        tableData.value = []
        pagination.total = 0
    } finally {
        loading.value = false
    }
}

const handleSearch = () => {
    // 重置到第一页
    pagination.page = 1
    // 重新加载数据
    loadData()
}

const handleSortChange = ({ prop, order }) => {
    sortInfo.prop = prop
    sortInfo.order = order
    // 重置到第一页
    pagination.page = 1
    loadData()
}

const handleSizeChange = (size) => {
    pagination.size = size
    loadData()
}

const handleCurrentChange = (page) => {
    pagination.page = page
    loadData()
}

const showAddDialog = () => {
    resetForm()
    dialogVisible.value = true
}

const editModel = async (row) => {
    try {
        // 先获取完整的模型详情
        const response = await api.get(`/system/embedding/models/${row.id}`)
        if (response.code !== 200) {
            ElMessage.error('获取模型详情失败')
            return
        }

        const modelData = response.data

        // 先重置表单
        resetForm()

        // 然后设置编辑数据
        Object.assign(form, {
            id: modelData.id,
            name: modelData.name || '',
            model_type: modelData.model_type || '',
            api_type: modelData.api_type || '',
            api_key: modelData.api_key || '',
            api_url: modelData.api_url || '',
            model_name: modelData.model_name || '',
            local_path: modelData.local_path || '',
            vector_dimension: modelData.vector_dimension || 1536,
            max_tokens: modelData.max_tokens || 8192,
            batch_size: modelData.batch_size || 32,
            timeout: modelData.timeout || 30,
            is_public: Boolean(modelData.is_public),
            is_active: Boolean(modelData.is_active),
            description: modelData.description || ''
        })

        // 设置预设模型选择器的值
        if (modelData.model_type && modelData.model_name) {
            form.preset_model = `${modelData.model_type}|${modelData.model_name}`
        }

        console.log('编辑模型数据:', form)
        dialogVisible.value = true
    } catch (error) {
        console.error('获取模型详情失败:', error)
        ElMessage.error('获取模型详情失败')
    }
}

const resetForm = () => {
    Object.assign(form, {
        id: null,
        name: '',
        model_type: '',
        api_type: '',
        api_key: '',
        api_url: '',
        model_name: '',
        local_path: '',
        preset_model: '',
        vector_dimension: 1536,
        max_tokens: 8192,
        batch_size: 32,
        timeout: 30,
        is_public: false,
        is_active: true,
        description: ''
    })
    if (formRef.value) {
        formRef.value.clearValidate()
    }
}

const onPresetModelChange = (value) => {
    if (!value) return

    const config = presetModelConfigs[value]
    if (config) {
        // 自动填充所有配置
        Object.assign(form, {
            name: config.name,
            model_type: config.model_type,
            api_type: config.api_type,
            api_url: config.api_url || '',
            model_name: config.model_name,
            vector_dimension: config.vector_dimension,
            max_tokens: config.max_tokens,
            batch_size: config.batch_size,
            timeout: config.timeout,
            description: config.description
        })
        
        // 本地模型强制设置为公开
        if (config.api_type === 'local') {
            form.is_public = true
        }
    }
}

const submitForm = async () => {
    if (!formRef.value) return

    try {
        await formRef.value.validate()
        
        // 本地模型必须设置为公开
        if (form.api_type === 'local' && !form.is_public) {
            form.is_public = true
            ElMessage.warning('本地模型已自动设置为公共模型')
        }
        
        submitting.value = true

        const url = form.id
            ? `/system/embedding/models/${form.id}`
            : '/system/embedding/models'
        const method = form.id ? 'put' : 'post'

        console.log('提交表单数据:', form)
        const response = await api[method](url, form)
        console.log('提交响应:', response)

        if (response.code === 200 || response.code === 201) {
            ElMessage.success(form.id ? '更新成功' : '创建成功')
            dialogVisible.value = false
            loadData()
        } else {
            ElMessage.error(response.message || '操作失败')
        }
    } catch (error) {
        console.error('提交表单失败:', error)
        ElMessage.error('操作失败')
    } finally {
        submitting.value = false
    }
}

const testModel = async (row) => {
    testingId.value = row.id
    try {
        const response = await api.post(`/system/embedding/models/${row.id}/test`, {
            text: '这是一个测试文本，用于验证嵌入模型是否正常工作。'
        })

        if (response.code === 200) {
            testResult.value = response.data
            testDialogVisible.value = true
        } else {
            ElMessage.error(response.message || '测试失败')
        }
    } catch (error) {
        console.error('测试模型失败:', error)
        ElMessage.error('测试失败')
    } finally {
        testingId.value = null
    }
}

const deleteModel = async (row) => {
    try {
        await ElMessageBox.confirm(
            `确定要删除模型 "${row.name}" 吗？此操作不可恢复。`,
            '确认删除',
            {
                confirmButtonText: '确定',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )

        const response = await api.delete(`/system/embedding/models/${row.id}`)
        if (response.code === 200) {
            ElMessage.success('删除成功')
            loadData()
        } else {
            ElMessage.error(response.message || '删除失败')
        }
    } catch (error) {
        if (error !== 'cancel') {
            console.error('删除模型失败:', error)
            ElMessage.error('删除失败')
        }
    }
}

const loadLocalModelStatus = async () => {
    try {
        const response = await api.get('/system/embedding/local/status')
        if (response.code === 200) {
            const data = response.data
            if (data.has_loaded_model) {
                currentLoadedModelId.value = data.current_model.model_id
                localModelStatus.value = {
                    [data.current_model.model_id]: 'loaded'
                }
            } else {
                currentLoadedModelId.value = null
                localModelStatus.value = {}
            }
        }
    } catch (error) {
        console.error('获取本地模型状态失败:', error)
    }
}

const getLocalModelStatus = (modelId) => {
    return localModelStatus.value[modelId] || 'unloaded'
}

const getLocalModelStatusText = (modelId) => {
    const status = getLocalModelStatus(modelId)
    return status === 'loaded' ? '已加载' : '未加载'
}

// 获取加载按钮的提示信息
const getLoadButtonTooltip = (row) => {
    const user = getCurrentUser()
    if (!user) return '请先登录'

    // 管理员可以加载所有模型
    if (user.role_id === 1) return '加载模型'

    // 不是自己创建的模型
    if (row.user_id !== user.user_id) {
        return '只能加载自己创建的模型'
    }

    // 检查是否有其他用户的模型已加载
    if (currentLoadedModelId.value && currentLoadedModelId.value !== row.id) {
        const currentLoadedModel = tableData.value.find(model => model.id === currentLoadedModelId.value)
        if (currentLoadedModel && currentLoadedModel.user_id !== user.user_id) {
            return `当前已加载其他用户的模型，无法加载`
        }
    }

    return '加载模型'
}

// 获取卸载按钮的提示信息
const getUnloadButtonTooltip = (row) => {
    const user = getCurrentUser()
    if (!user) return '请先登录'

    // 管理员可以卸载所有模型
    if (user.role_id === 1) return '卸载模型'

    // 不是自己创建的模型
    if (row.user_id !== user.user_id) {
        return '只能卸载自己创建的模型'
    }

    // 检查当前加载的模型是否是这个模型
    if (currentLoadedModelId.value !== row.id) {
        return '只能卸载当前加载的模型'
    }

    return '卸载模型'
}

// 权限检查函数
const getCurrentUser = () => {
    const userInfo = localStorage.getItem('userInfo')
    return userInfo ? JSON.parse(userInfo) : null
}

const canEditModel = (row) => {
    const user = getCurrentUser()
    if (!user) return false

    // 管理员可以编辑所有模型
    if (user.role_id === 1) return true

    // 普通用户只能编辑自己创建的模型
    return row.user_id === user.user_id
}

const canDeleteModel = (row) => {
    const user = getCurrentUser()
    if (!user) return false

    // 预设模型不允许删除
    if (row.is_preset) return false

    // 管理员可以删除所有非预设模型
    if (user.role_id === 1) return true

    // 普通用户只能删除自己创建的模型
    return row.user_id === user.user_id
}

const canLoadModel = (row) => {
    const user = getCurrentUser()
    if (!user) return false

    // 管理员可以加载所有本地模型
    if (user.role_id === 1) return true

    // 普通用户权限检查
    if (row.user_id !== user.user_id) {
        // 不是自己创建的模型，不能加载
        return false
    }

    // 检查当前是否有其他用户的模型已加载
    if (currentLoadedModelId.value && currentLoadedModelId.value !== row.id) {
        // 找到当前加载的模型信息
        const currentLoadedModel = tableData.value.find(model => model.id === currentLoadedModelId.value)
        if (currentLoadedModel && currentLoadedModel.user_id !== user.user_id) {
            // 当前加载的是别人的模型，不允许加载自己的模型
            return false
        }
    }

    return true
}

const canUnloadModel = (row) => {
    const user = getCurrentUser()
    if (!user) return false

    // 管理员可以卸载所有模型
    if (user.role_id === 1) return true

    // 普通用户只能卸载自己创建的模型
    if (row.user_id !== user.user_id) {
        return false
    }

    // 检查当前加载的模型是否是这个模型
    if (currentLoadedModelId.value !== row.id) {
        return false
    }

    return true
}

const loadLocalModel = async (modelId) => {
    try {
        // 检查权限
        const targetModel = tableData.value.find(model => model.id === modelId)
        if (!canLoadModel(targetModel)) {
            ElMessage.error('无权限加载此模型')
            return
        }

        // 立即显示资源检查对话框，先显示loading状态
        resourceHtml.value = `
            <div style="text-align: center; padding: 40px;">
                <div style="margin-bottom: 20px;">
                    <i class="el-icon-loading" style="font-size: 32px; color: #409eff;"></i>
                </div>
                <div style="font-size: 16px; color: #606266; margin-bottom: 8px;">
                    正在检查服务器资源状态...
                </div>
                <div style="font-size: 14px; color: #909399;">
                    请稍候，正在获取GPU、内存和CPU信息
                </div>
            </div>
        `
        
        // 显示对话框
        resourceDialogVisible.value = true
        
        // 设置对话框引用，此时只有取消按钮可用
        dialogRef.value = {
            handleConfirm: null, // 暂时禁用确认按钮
            handleCancel: () => {
                resourceDialogVisible.value = false
            }
        }

        // 首先验证模型配置
        const validateResponse = await api.post(`/system/embedding/models/${modelId}/validate`)
        if (validateResponse.code !== 200) {
            resourceDialogVisible.value = false
            ElMessage.error(validateResponse.message || '模型配置验证失败')
            return
        }

        const validationResult = validateResponse.data
        if (!validationResult.is_valid) {
            resourceDialogVisible.value = false
            // 显示配置不匹配的详细信息，并提供跳过验证的选项
            try {
                await ElMessageBox.confirm(
                    `模型配置验证失败：\n\n` +
                    `期望模型：${validationResult.expected_model}\n` +
                    `实际路径：${validationResult.actual_path}\n` +
                    `错误信息：${validationResult.error_message}\n\n` +
                    `是否要跳过验证继续加载模型？`,
                    '配置验证失败',
                    {
                        confirmButtonText: '跳过验证并加载',
                        cancelButtonText: '取消',
                        type: 'warning'
                    }
                )
                // 用户选择跳过验证，重新显示资源检查对话框
                resourceDialogVisible.value = true
            } catch (error) {
                // 用户选择取消
                return
            }
        }

        // 获取服务器资源状态
        const resourceResponse = await api.get('/system/embedding/server/resources')
        if (resourceResponse.code !== 200) {
            resourceDialogVisible.value = false
            ElMessage.error('获取服务器资源信息失败')
            return
        }

        const resources = resourceResponse.data

        // 构建资源信息HTML
        let resourceContent = ``

        if (resources.has_gpu) {
            resourceContent += `
                <div style="margin-bottom: 16px; padding: 16px; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
                    <div style="font-weight: 600; color: #166534; margin-bottom: 12px; font-size: 15px;">
                        GPU信息
                    </div>
            `
            resources.gpu_info.forEach((gpu, index) => {
                const memoryColor = gpu.memory_percent > 80 ? '#dc2626' : gpu.memory_percent > 60 ? '#ea580c' : '#16a34a'
                const utilizationColor = gpu.utilization > 80 ? '#dc2626' : gpu.utilization > 60 ? '#ea580c' : '#16a34a'

                resourceContent += `
                    <div style="margin-left: 20px; margin-bottom: 8px; padding: 8px; background: white; border-radius: 4px; border-left: 3px solid #22c55e;">
                        <div style="color: #374151; font-weight: 500; margin-bottom: 4px;">GPU ${index}: ${gpu.name}</div>
                        <div style="display: flex; justify-content: space-between; font-size: 13px;">
                            <span style="color: #6b7280;">
                                显存: <span style="color: ${memoryColor}; font-weight: 600;">${gpu.memory_used}MB / ${gpu.memory_total}MB (${gpu.memory_percent.toFixed(2)}%)</span>
                            </span>
                            <span style="color: #6b7280;">
                                利用率: <span style="color: ${utilizationColor}; font-weight: 600;">${gpu.utilization.toFixed(2)}%</span>
                            </span>
                        </div>
                    </div>
                `
            })
            resourceContent += `</div>`
        } else {
            resourceContent += `
                <div style="margin-bottom: 16px; padding: 16px; background: #fef3c7; border-radius: 8px; border: 1px solid #fbbf24;">
                    <div style="font-weight: 600; color: #92400e; margin-bottom: 8px; font-size: 15px;">
                        GPU状态
                    </div>
                    <div style="margin-left: 20px; color: #92400e;">未检测到GPU，将使用CPU运行</div>
                </div>
            `
        }

        const memoryColor = resources.memory.percent > 80 ? '#dc2626' : resources.memory.percent > 60 ? '#ea580c' : '#16a34a'
        const cpuColor = resources.cpu.percent > 80 ? '#dc2626' : resources.cpu.percent > 60 ? '#ea580c' : '#16a34a'

        resourceContent += `
            <div style="margin-bottom: 10px; padding: 16px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="font-weight: 600; color: #475569; margin-bottom: 12px; font-size: 15px;">
                    内存信息
                </div>
                <div style="margin-left: 20px; display: flex; justify-content: space-between; font-size: 13px; color: #64748b;">
                    <span>已用: <span style="color: ${memoryColor}; font-weight: 600;">${resources.memory.used}GB / ${resources.memory.total}GB (${resources.memory.percent}%)</span></span>
                    <span>可用: <span style="color: #16a34a; font-weight: 600;">${resources.memory.available}GB</span></span>
                </div>
            </div>
            
            <div style="margin-bottom: 10px; padding: 16px; background: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0;">
                <div style="font-weight: 600; color: #475569; margin-bottom: 12px; font-size: 15px;">
                    CPU信息
                </div>
                <div style="margin-left: 20px; display: flex; justify-content: space-between; font-size: 13px; color: #64748b;">
                    <span>核心数: <span style="color: #374151; font-weight: 600;">${resources.cpu.cores}</span></span>
                    <span>使用率: <span style="color: ${cpuColor}; font-weight: 600;">${resources.cpu.percent}%</span></span>
                </div>
            </div>
        `

        if (!resources.has_gpu) {
            resourceContent += `
                <div style="margin-bottom: 20px; padding: 16px; background: #fef2f2; border-radius: 8px; border: 1px solid #fecaca;">
                    <div style="color: #dc2626; font-weight: 600; margin-bottom: 8px; font-size: 15px;">
                        重要提醒
                    </div>
                    <div style="color: #991b1b; font-size: 13px; margin-left: 20px; line-height: 1.5;">
                        由于没有GPU，模型将在CPU上运行，这会显著增加内存使用和处理时间。
                    </div>
                </div>
            `
        }

        // 添加配置验证成功的提示
        resourceContent += `
            <div style="margin-bottom: 10px; padding: 12px; background: #f0fdf4; border-radius: 8px; border: 1px solid #bbf7d0;">
                <div style="color: #166534; font-weight: 500; font-size: 13px; line-height: 1.5;">
                    模型配置验证通过：${validationResult.model_info}
                </div>
            </div>
        `

        resourceContent += `
            <div style="margin-top: 2px; padding: 12px; background: #fff; border-radius: 8px;">
                <div style="color: #dc2626; font-weight: 500; font-size: 14px; line-height: 1.5;">
                    加载本地嵌入模型会消耗大量系统资源，确定要继续吗？
                </div>
            </div>
        `

        // 更新资源信息到对话框，并启用确认按钮
        resourceHtml.value = resourceContent
        
        // 显示确认对话框，现在确认按钮可用
        await new Promise((resolve, reject) => {
            dialogRef.value = {
                handleConfirm: () => {
                    resourceDialogVisible.value = false
                    resolve()
                },
                handleCancel: () => {
                    resourceDialogVisible.value = false
                    reject('cancel')
                }
            }
        })

        // 用户确认后开始加载
        loadingModels.value[modelId] = true
        const response = await api.post(`/system/embedding/models/${modelId}/load`)

        if (response.code === 200) {
            ElMessage.success(response.data.message)
            // 更新状态
            localModelStatus.value = { [modelId]: 'loaded' }
            currentLoadedModelId.value = modelId
            // 清除其他模型的加载状态
            Object.keys(localModelStatus.value).forEach(id => {
                if (parseInt(id) !== modelId) {
                    delete localModelStatus.value[id]
                }
            })
        } else {
            ElMessage.error(response.message || '加载模型失败')
        }
    } catch (error) {
        if (error !== 'cancel') {
            console.error('加载本地模型失败:', error)
            ElMessage.error('加载模型失败')
        }
    } finally {
        loadingModels.value[modelId] = false
    }
}

const unloadLocalModel = async () => {
    try {
        // 先弹出确认框
        await ElMessageBox.confirm(
            '确定要卸载当前加载的模型吗？\n\n卸载后需要重新加载才能使用。',
            '确认卸载模型',
            {
                confirmButtonText: '确定卸载',
                cancelButtonText: '取消',
                type: 'warning'
            }
        )
    } catch (error) {
        // 用户取消
        return
    }

    // 用户确认后开始卸载
    unloadingModel.value = true
    try {
        const response = await api.post('/system/embedding/local/unload')
        if (response.code === 200) {
            ElMessage.success(response.data.message)
            // 清除状态
            localModelStatus.value = {}
            currentLoadedModelId.value = null
        } else {
            ElMessage.error(response.message || '卸载模型失败')
        }
    } catch (error) {
        console.error('卸载本地模型失败:', error)
        ElMessage.error('卸载模型失败')
    } finally {
        unloadingModel.value = false
    }
}

const getModelTypeName = (type) => {
    // 处理空值、null、undefined等情况
    if (!type || type === null || type === undefined || type === '') {
        return '未知类型'
    }

    const typeMap = {
        'openai': 'OpenAI',
        'azure_openai': 'Azure OpenAI',
        'zhipu': '智谱AI',
        'baidu': '百度千帆',
        'dashscope': '通义千问',
        'xunfei': '讯飞星火',
        'tencent': '腾讯混元',
        'sentence_transformers': 'Sentence Transformers',
        'ollama': 'Ollama',
        'local': '本地模型'
    }

    // 清理字符串，移除可能的特殊字符
    const cleanType = String(type).trim()

    return typeMap[cleanType] || cleanType || '未知类型'
}

const getModelTypeColor = (type) => {
    // 处理空值、null、undefined等情况
    if (!type || type === null || type === undefined || type === '') {
        return 'info'
    }

    const colorMap = {
        'openai': 'success',
        'azure_openai': 'primary',
        'zhipu': 'warning',
        'baidu': 'info',
        'dashscope': 'success',
        'xunfei': 'warning',
        'tencent': 'primary',
        'sentence_transformers': 'info',
        'ollama': 'warning',
        'local': 'danger'
    }

    // 清理字符串，移除可能的特殊字符
    const cleanType = String(type).trim()

    return colorMap[cleanType] || 'info'
}

const formatDateTime = (dateTime) => {
    if (!dateTime) return ''
    return new Date(dateTime).toLocaleString('zh-CN')
}

// 刷新数据
const refresh = async () => {
    await loadData();
    ElMessage.success('刷新成功');
};

// 生命周期
onMounted(() => {
    loadData()
})
</script>

<style scoped>
.embedding-mgr-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f9fafc;
  padding: 16px;
  border-radius: 8px;
}

.content-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
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

.header-actions {
  display: flex;
  gap: 12px;
}

.header-actions .el-button {
  padding: 10px 20px;
  font-weight: 500;
  transition: all 0.3s;
}

.header-actions .el-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.2);
}

.search-bar {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.model-name {
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

.model-params-display {
  margin-bottom: 20px;
  padding: 12px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  width: 100%;
}

.params-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px solid #e9ecef;
}

.params-title {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}

.params-content {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.param-item {
  display: flex;
  flex-direction: column;
  padding: 6px 10px;
  background: white;
  border-radius: 4px;
  border: 1px solid #f0f0f0;
}

.param-label {
  font-weight: 500;
  color: #606266;
  font-size: 11px;
  margin-bottom: 2px;
}

.param-value {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
  margin-bottom: 1px;
}

.param-desc {
  color: #909399;
  font-size: 10px;
  line-height: 1.2;
}

/* 资源检查对话框样式 */
:deep(.resource-check-dialog) {
  .el-message-box {
    width: 900px !important;
    border-radius: 12px;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }
}

.operation-buttons {
  display: flex;
  gap: 0;
  justify-content: center;
}

.operation-buttons .el-button {
  padding: 6px 8px;
  border-radius: 0;
  margin-left: -1px;
}

.operation-buttons .el-button:first-child {
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
  margin-left: 0;
}

.operation-buttons .el-button:last-child {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.operation-buttons .el-button .el-icon {
  font-size: 14px;
}

.operation-buttons .el-button:hover,
.operation-buttons .el-button:focus,
.operation-buttons .el-button:active {
  z-index: 1;
}

.model-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-with-notice {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.local-model-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 24px;
  padding: 6px 10px;
  background-color: #fef3c7;
  border: 1px solid #fbbf24;
  border-radius: 4px;
  color: #92400e;
  font-size: 11px;
  line-height: 1.3;
  max-width: fit-content;
}

.notice-icon {
  color: #f59e0b;
  font-size: 12px;
  flex-shrink: 0;
}

/* 测试结果对话框样式 */
:deep(.el-descriptions .el-descriptions__label) {
  width: 120px !important;
  min-width: 120px !important;
  font-weight: 600 !important;
  color: #303133 !important;
}

:deep(.el-descriptions .el-descriptions__content) {
  width: auto !important;
  color: #606266 !important;
}
</style>