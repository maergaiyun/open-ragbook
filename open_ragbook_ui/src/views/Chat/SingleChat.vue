<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from '@/axios/index.js'
import { ElMessage, ElLoading } from 'element-plus'
import {
    ChatRound,
    Search,
    Setting,
    Edit,
    Delete,
    Refresh,
    Plus,
    Document,
    Connection,
    Histogram,
    Loading
} from '@element-plus/icons-vue'
import { formatDate } from '@/utils/date'
import MarkdownIt from 'markdown-it'
import highlight from 'highlight.js'
import 'highlight.js/styles/github.css'

const md = new MarkdownIt({
    html: true,
    linkify: true,
    typographer: true,
    highlight: function (str, lang) {
        if (lang && highlight.getLanguage(lang)) {
            try {
                return '<pre class="hljs"><code>' +
                    highlight.highlight(str, { language: lang, ignoreIllegals: true }).value +
                    '</code></pre>'
            } catch (err) {
                // 发生错误时返回未高亮的代码
                console.error('Code highlighting error:', err);
            }
        }
        return '<pre class="hljs"><code>' + md.utils.escapeHtml(str) + '</code></pre>'
    }
})

// 路由
const route = useRoute()
const router = useRouter()

// 加载状态
const loading = ref(false)
const sendingMessage = ref(false)
const pageLoading = ref(true)  // 新增页面整体加载状态
const kbLoading = ref(false)   // 知识库加载状态
const modelLoading = ref(false) // 模型加载状态

// 知识库列表
const knowledgeBases = ref([])
const selectedKB = ref(null)

// 模型服务商和模型列表
const providers = ref([])
const models = ref([])
const selectedModel = ref(null)

// 检索设置
const retrievalSettingsVisible = ref(false)
const retrievalSettings = reactive({
    retrieve_count: 3,        // 检索结果数量
    similarity_threshold: 0.5, // 相似度阈值 (降低默认值)
    diversity: 0.7,          // 生成多样性
})

// 会话ID
const conversationId = ref(null)

// 消息列表
const messages = ref([])
const currentMessage = ref('')
const messagesContainer = ref(null)

// 引用消息来源
const showCitations = ref(false)
const citationIndex = ref(0)
const currentCitations = ref([])

// 获取当前选中的引用
const currentCitation = computed(() => {
    if (!currentCitations.value.length || citationIndex.value >= currentCitations.value.length) {
        return null
    }
    return currentCitations.value[citationIndex.value]
})

// 获取知识库列表
const fetchKnowledgeBases = async () => {
    try {
        kbLoading.value = true
        const response = await axios.get('/knowledge/database/list')
        console.log('Knowledge base response:', response);

        // 处理嵌套的数据结构
        const knowledgeBaseData = response.data && response.data.data ? response.data.data : [];
        knowledgeBases.value = knowledgeBaseData;

        // 自动选择第一个或之前选择的
        if (knowledgeBases.value.length > 0) {
            const kbId = localStorage.getItem('selected_kb_id')
            if (kbId) {
                const found = knowledgeBases.value.find(kb => kb.id === parseInt(kbId))
                if (found) {
                    selectedKB.value = found
                } else {
                    selectedKB.value = knowledgeBases.value[0]
                }
            } else {
                selectedKB.value = knowledgeBases.value[0]
            }
        }
    } catch (error) {
        ElMessage.error('获取知识库列表失败')
        console.error(error)
    } finally {
        kbLoading.value = false
        checkPageLoading() // 检查整体加载状态
    }
}

// 获取模型服务商和模型列表
const fetchModelsAndProviders = async () => {
    try {
        modelLoading.value = true

        // 获取服务商
        const providerResponse = await axios.get('/system/llm/providers')
        console.log('Provider response:', providerResponse);

        // 处理嵌套的数据结构
        const providerData = providerResponse.data && providerResponse.data.data
            ? providerResponse.data.data
            : (Array.isArray(providerResponse.data) ? providerResponse.data : []);
        providers.value = providerData;

        // 获取用户自己创建的模型
        const modelResponse = await axios.get('/system/llm/models')
        console.log('Model response:', modelResponse);

        // 处理嵌套的数据结构
        const modelData = modelResponse.data && modelResponse.data.data
            ? modelResponse.data.data
            : (Array.isArray(modelResponse.data) ? modelResponse.data : []);
        models.value = modelData;

        // 找到默认模型或第一个模型
        const defaultModel = models.value.find(m => m.is_default)
        if (defaultModel) {
            selectedModel.value = defaultModel
        } else if (models.value.length > 0) {
            selectedModel.value = models.value[0]
        }

        // 恢复上次选择的模型
        const modelId = localStorage.getItem('selected_model_id')
        if (modelId) {
            const found = models.value.find(m => m.id === parseInt(modelId))
            if (found) {
                selectedModel.value = found
            }
        }
    } catch (error) {
        ElMessage.error('获取模型列表失败')
        console.error(error)
    } finally {
        modelLoading.value = false
        checkPageLoading() // 检查整体加载状态
    }
}

// 检查页面是否加载完成
const checkPageLoading = () => {
    // 当两个数据源都加载完成后，关闭页面加载状态
    if (!kbLoading.value && !modelLoading.value) {
        pageLoading.value = false
    }
}

// 计算当前模型所属的服务商
const currentProvider = computed(() => {
    if (!selectedModel.value || !providers.value.length) return null
    return providers.value.find(p => p.id === selectedModel.value.provider_id)
})

// 选择知识库
const selectKnowledgeBase = (kb) => {
    selectedKB.value = kb
    localStorage.setItem('selected_kb_id', kb.id)
}

// 选择模型
const selectModel = (model) => {
    selectedModel.value = model
    localStorage.setItem('selected_model_id', model.id)
}

// 发送消息
const sendMessage = async () => {
    if (!currentMessage.value.trim() || sendingMessage.value) return
    if (!selectedKB.value) {
        ElMessage.warning('请先选择知识库')
        return
    }
    if (!selectedModel.value) {
        ElMessage.warning('请先选择模型')
        return
    }

    const userMessage = currentMessage.value.trim()

    // 添加用户消息到列表
    messages.value.push({
        id: Date.now(),
        role: 'user',
        content: userMessage,
        timestamp: new Date()
    })

    currentMessage.value = ''
    sendingMessage.value = true

    // 滚动到底部
    await nextTick()
    if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }

    try {
        // 添加一个空的AI消息作为占位符
        const aiMessageId = Date.now()
        messages.value.push({
            id: aiMessageId,
            role: 'assistant',
            content: '',
            status: 'loading',
            timestamp: new Date(),
            citations: []
        })

        // 构建请求参数
        const requestParams = {
            query: userMessage,
            knowledge_id: selectedKB.value.id,
            model_id: selectedModel.value.id,
            retrieve_count: retrievalSettings.retrieve_count,
            similarity_threshold: retrievalSettings.similarity_threshold,
            diversity: retrievalSettings.diversity,
            conversation_id: conversationId.value
        }
        
        console.log('发送检索请求，参数:', requestParams);

        // 请求后端进行知识库检索+模型回答
        const response = await axios.post('/chat/retrieve-and-chat', requestParams)

        console.log('Chat response:', response);

        // 处理响应数据 - axios拦截器已经返回了response.data
        // response 就是后端的响应体
        console.log('Response type:', typeof response, 'Response:', response);

        // 检查响应状态
        if (response.status === 'error') {
            // 后端返回业务错误，抛出错误让catch块处理
            throw new Error(response.message || '未知错误')
        }

        // 成功响应，数据在data字段中
        const data = response.data || {};

        // 更新会话ID
        if (data.conversation_id) {
            conversationId.value = data.conversation_id;
        }

        // 更新AI消息
        const aiMessageIndex = messages.value.findIndex(msg => msg.id === aiMessageId)
        if (aiMessageIndex !== -1) {
            messages.value[aiMessageIndex] = {
                id: aiMessageId,
                role: 'assistant',
                content: data.answer || '',
                citations: data.retrieved_docs || [],  // 使用retrieved_docs字段
                status: 'success',
                timestamp: new Date()
            }
        }
    } catch (error) {
        // 根据错误类型显示不同的提示
        const errorMessage = error.response?.data?.message || error.message || '未知错误'
        
        // 处理相似度阈值相关的错误
        if (errorMessage.includes('相似度高于') || errorMessage.includes('没有找到相关的知识')) {
            // 移除加载中的消息
            const loadingIndex = messages.value.findIndex(msg => msg.status === 'loading')
            if (loadingIndex !== -1) {
                messages.value.splice(loadingIndex, 1)
            }
            
            // 只显示友好的提示，不在消息气泡中显示错误
            ElMessage.warning({
                message: '未找到足够相似的内容，建议降低相似度阈值或换个问法',
                duration: 4000
            })
        } else {
            // 其他错误：在消息气泡中显示错误信息
            const aiMessageIndex = messages.value.findIndex(msg => msg.status === 'loading')
            if (aiMessageIndex !== -1) {
                messages.value[aiMessageIndex] = {
                    id: Date.now(),
                    role: 'assistant',
                    content: `发生错误: ${errorMessage}`,
                    status: 'error',
                    timestamp: new Date()
                }
            }
            ElMessage.error('发送消息失败')
        }
        console.error('发送消息失败:', error);
    } finally {
        sendingMessage.value = false

        // 滚动到底部
        await nextTick()
        if (messagesContainer.value) {
            messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
    }
}

// 保存对话历史
const saveChat = async () => {
    if (messages.value.length < 2) return // 至少有一问一答才保存

    try {
        const chatHistory = {
            title: messages.value[0].content.substring(0, 50) + (messages.value[0].content.length > 50 ? '...' : ''),
            knowledge_base_id: selectedKB.value.id,
            knowledge_base_name: selectedKB.value.name,
            model_id: selectedModel.value.id,
            model_name: selectedModel.value.name,
            messages: messages.value
        }

        console.log('Saving chat history:', chatHistory);
        const response = await axios.post('/chat/history', chatHistory)
        console.log('Save chat response:', response);
    } catch (error) {
        console.error('保存对话历史失败', error)
    }
}

// 查看引用消息
const viewCitations = (message) => {
    if (!message.citations || message.citations.length === 0) return

    currentCitations.value = message.citations
    citationIndex.value = 0  // 重置为第一个引用
    showCitations.value = true
    
    // 在控制台打印引用内容，帮助调试
    console.log('Citations:', currentCitations.value)
}

// 清空当前对话
const clearChat = () => {
    messages.value = []
    conversationId.value = null
}

// 重置检索设置
const resetRetrievalSettings = () => {
    Object.assign(retrievalSettings, {
        retrieve_count: 3,
        similarity_threshold: 0.5,
        diversity: 0.7
    })
}

// 渲染markdown内容
const renderMarkdown = (content) => {
    if (!content) return ''
    return md.render(content)
}

// 格式化文件路径，超长时显示省略号
const formatSourcePath = (path) => {
    if (!path) return '未知来源'
    
    // 如果路径长度小于50个字符，直接返回
    if (path.length <= 50) {
        return path
    }
    
    // 尝试提取文件名
    const fileName = path.split(/[/\\]/).pop() || path
    
    // 如果文件名本身就很长，截取前20个字符 + ... + 后15个字符
    if (fileName.length > 35) {
        return fileName.substring(0, 20) + '...' + fileName.substring(fileName.length - 15)
    }
    
    // 如果路径很长但文件名不长，显示 ...文件名
    return '...' + fileName
}

// 格式化相似度分数
const formatSimilarity = (score) => {
    if (typeof score !== 'number') return '未知'
    
    // 转换为百分比显示
    const percentage = (score * 100).toFixed(1)
    return `${percentage}%`
}

onMounted(() => {
    pageLoading.value = true // 进入页面时设置加载状态
    fetchKnowledgeBases()
    fetchModelsAndProviders()
})
</script>

<template>
    <div class="single-chat-container">
        <!-- 全屏加载效果 -->
        <div v-if="pageLoading" class="page-loading">
            <el-icon class="loading-icon">
                <Loading />
            </el-icon>
            <div class="loading-text">正在加载资源...</div>
        </div>

        <!-- 侧边栏 -->
        <div class="sidebar">
            <div class="sidebar-content">
            <div class="sidebar-section">
                <h3 class="sidebar-title">知识库选择</h3>
                <div class="knowledge-base-list">
                    <div v-if="kbLoading" class="loading-placeholder">
                        <el-skeleton :rows="3" animated />
                    </div>
                    <div v-else-if="knowledgeBases.length === 0" class="empty-state">
                        <div class="empty-icon">📚</div>
                        <div class="empty-text">暂无知识库</div>
                    </div>
                    <div v-else v-for="kb in knowledgeBases" :key="kb.id" class="knowledge-base-item"
                        :class="{ active: selectedKB?.id === kb.id }" @click="selectKnowledgeBase(kb)">
                        <el-icon>
                            <Document />
                        </el-icon>
                        <div class="knowledge-base-info">
                            <div class="knowledge-base-name">{{ kb.name }}</div>
                            <div class="knowledge-base-desc">{{ kb.description || '无描述' }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="sidebar-section">
                <h3 class="sidebar-title">模型选择</h3>
                <div class="model-list">
                    <div v-if="modelLoading" class="loading-placeholder">
                        <el-skeleton :rows="3" animated />
                    </div>
                    <div v-else-if="models.length === 0" class="empty-state">
                        <div class="empty-icon">🤖</div>
                        <div class="empty-text">暂无模型</div>
                    </div>
                    <div v-else v-for="model in models" :key="model.id" class="model-item"
                        :class="{ active: selectedModel?.id === model.id }" @click="selectModel(model)">
                        <el-icon>
                            <Connection />
                        </el-icon>
                        <div class="model-info">
                            <div class="model-name">{{ model.name }}</div>
                            <div class="model-provider" v-if="providers.find(p => p.id === model.provider_id)">
                                {{providers.find(p => p.id === model.provider_id).name}}
                            </div>
                        </div>
                        <el-tag v-if="model.is_default" type="success" size="small">默认</el-tag>
                    </div>
                </div>
            </div>

            <div class="sidebar-section">
                <h3 class="sidebar-title">检索设置</h3>
                <el-button type="primary" class="settings-button" @click="retrievalSettingsVisible = true"
                    :disabled="kbLoading || modelLoading">
                    <el-icon class="button-icon">
                        <Setting />
                    </el-icon>
                    <span>调整检索参数</span>
                </el-button>
                </div>
            </div>
        </div>

        <!-- 主对话区域 -->
        <div class="chat-container">
            <div class="chat-header">
                <div class="chat-info">
                    <h2 v-if="selectedKB" class="chat-title">与 {{ selectedKB.name }} 对话</h2>
                    <h2 v-else class="chat-title">请选择知识库</h2>
                    <div class="model-info" v-if="selectedModel">
                        使用模型: {{ selectedModel.name }}
                        <el-tag size="small" v-if="currentProvider">{{ currentProvider.name }}</el-tag>
                    </div>
                    <div class="retrieval-info">
                        <el-tag size="small" type="info">Top-K: {{ retrievalSettings.retrieve_count }}</el-tag>
                        <el-tag size="small" type="warning">相似度: {{ (retrievalSettings.similarity_threshold * 100).toFixed(0) }}%</el-tag>
                        <el-tag size="small" type="success">多样性: {{ retrievalSettings.diversity }}</el-tag>
                    </div>
                </div>
                <div class="chat-actions">
                    <el-button class="action-button" @click="clearChat" :disabled="messages.length === 0">
                        <el-icon class="button-icon">
                            <Delete />
                        </el-icon>
                        <span>清空对话</span>
                    </el-button>
                    <el-button class="action-button" type="primary" @click="retrievalSettingsVisible = true">
                        <el-icon class="button-icon">
                            <Setting />
                        </el-icon>
                        <span>检索设置</span>
                    </el-button>
                </div>
            </div>

            <div class="messages-container" ref="messagesContainer">
                <div v-if="messages.length === 0" class="chat-empty-state">
                    <div class="chat-empty-icon">💬</div>
                    <div class="chat-empty-text">开始提问吧</div>
                    <div class="chat-empty-hint">选择知识库和模型后，输入您的问题</div>
                </div>

                <div v-for="message in messages" :key="message.id" :class="['message', message.role]">
                    <div class="message-header">
                        <div class="avatar">
                            <el-icon v-if="message.role === 'user'">
                                <ChatRound />
                            </el-icon>
                            <el-icon v-else>
                                <ChatRound />
                            </el-icon>
                        </div>
                        <div class="message-info">
                            <div class="role-name">{{ message.role === 'user' ? '我' : 'AI助手' }}</div>
                            <div class="timestamp">{{ formatDate(message.timestamp) }}</div>
                        </div>
                    </div>

                    <div class="message-content">
                        <!-- 用户消息 -->
                        <div v-if="message.role === 'user'">{{ message.content }}</div>

                        <!-- AI消息 -->
                        <div v-else-if="message.status === 'loading'" class="loading-content">
                            <div class="typing-indicator">
                                <span></span>
                                <span></span>
                                <span></span>
                            </div>
                        </div>
                        <div v-else-if="message.status === 'error'" class="error-content">
                            {{ message.content }}
                        </div>
                        <div v-else class="ai-content" v-html="renderMarkdown(message.content)"></div>

                        <!-- 引用来源 -->
                        <div v-if="message.citations && message.citations.length > 0" class="message-citations">
                            <el-button size="small" type="primary" plain @click="viewCitations(message)">
                                查看引用来源 ({{ message.citations.length }})
                            </el-button>
                            <div class="citations-preview" v-if="message.citations.length > 0">
                                <el-tag 
                                    v-for="(citation, index) in message.citations.slice(0, 3)" 
                                    :key="index"
                                    size="small" 
                                    type="info" 
                                    class="citation-preview-tag">
                                    {{ formatSimilarity(citation.similarity_score) }}
                                </el-tag>
                                <span v-if="message.citations.length > 3" class="more-citations">
                                    +{{ message.citations.length - 3 }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="input-container">
                <el-input v-model="currentMessage" type="textarea" :rows="3" placeholder="输入您的问题..."
                    :disabled="!selectedKB || !selectedModel || sendingMessage"
                    @keydown.enter.exact.prevent="sendMessage" />
                <div class="input-actions">
                    <el-button type="primary" :icon="ChatRound" :loading="sendingMessage"
                        :disabled="!currentMessage.trim() || !selectedKB || !selectedModel" @click="sendMessage">
                        发送
                    </el-button>
                </div>
            </div>
        </div>

        <!-- 检索设置弹窗 -->
        <el-dialog v-model="retrievalSettingsVisible" title="检索设置" width="500px">
            <div class="retrieval-settings">
                <div class="setting-item">
                    <div class="setting-label">检索结果数量 (Top-K)</div>
                    <div class="setting-control">
                        <el-slider v-model="retrievalSettings.retrieve_count" :min="1" :max="10" :step="1" show-stops
                            show-input />
                    </div>
                    <div class="setting-desc">决定每次检索返回的文档片段数量</div>
                </div>

                <div class="setting-item">
                    <div class="setting-label">相似度阈值</div>
                    <div class="setting-control">
                        <el-slider v-model="retrievalSettings.similarity_threshold" :min="0.1" :max="0.9" :step="0.05"
                            show-stops show-input />
                    </div>
                    <div class="setting-desc">
                        仅返回相似度高于此值的文档。推荐值：0.3-0.7
                        <br>
                        <span style="color: #909399; font-size: 11px;">
                            过高可能找不到结果，过低可能返回不相关内容
                        </span>
                    </div>
                </div>

                <div class="setting-item">
                    <div class="setting-label">生成多样性 (Temperature)</div>
                    <div class="setting-control">
                        <el-slider v-model="retrievalSettings.diversity" :min="0" :max="2" :step="0.1" show-stops
                            show-input />
                    </div>
                    <div class="setting-desc">较低的值使输出更确定，较高的值使输出更多样化</div>
                </div>
            </div>

            <template #footer>
                <div class="dialog-footer">
                    <el-button @click="resetRetrievalSettings">重置为默认</el-button>
                    <el-button type="primary" @click="retrievalSettingsVisible = false">确定</el-button>
                </div>
            </template>
        </el-dialog>

        <!-- 引用来源弹窗 -->
        <el-dialog v-model="showCitations" title="引用来源" width="600px" class="citation-dialog">
            <div v-if="currentCitations.length > 0" class="citations-container">
                <div class="citations-navigation">
                    <div class="citation-counter">
                        第 {{ citationIndex + 1 }} 个，共 {{ currentCitations.length }} 个引用
                    </div>
                    <div class="citation-pagination">
                        <el-button 
                            size="small" 
                            :disabled="citationIndex <= 0"
                            @click="citationIndex = Math.max(0, citationIndex - 1)">
                            上一个
                        </el-button>
                        <el-button 
                            size="small" 
                            :disabled="citationIndex >= currentCitations.length - 1"
                            @click="citationIndex = Math.min(currentCitations.length - 1, citationIndex + 1)">
                            下一个
                        </el-button>
                    </div>
                </div>

                <div class="citation-content">
                    <div class="citation-header">
                        <div class="citation-title">
                            {{ currentCitation?.title || '未知文档' }}
                        </div>
                        <div class="citation-meta">
                            <div class="citation-tags">
                                <el-tag size="small" class="source-tag">
                                    <span class="source-label">来源:</span>
                                    <span 
                                        class="source-path" 
                                        :title="currentCitation?.source || '未知来源'">
                                        {{ formatSourcePath(currentCitation?.source || '未知来源') }}
                                    </span>
                                </el-tag>
                                <el-tag 
                                    v-if="currentCitation?.similarity_score !== undefined" 
                                    size="small" 
                                    type="success" 
                                    class="similarity-tag">
                                    相似度: {{ formatSimilarity(currentCitation.similarity_score) }}
                                </el-tag>
                            </div>
                        </div>
                    </div>

                    <div class="citation-text">
                        {{ currentCitation?.content || '无内容' }}
                    </div>
                </div>
            </div>

            <template #footer>
                <div class="dialog-footer">
                    <el-button @click="showCitations = false">关闭</el-button>
                </div>
            </template>
        </el-dialog>
    </div>
</template>

<style scoped>
.single-chat-container {
    height: calc(100vh - 70px);
    display: flex;
    background-color: #f5f7fa;
    padding: 16px;
    border-radius: 8px;
    position: relative;
    box-sizing: border-box;
    overflow: hidden;
    /* 添加相对定位，用于全屏加载效果 */
}

/* 全屏加载效果 */
.page-loading {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(255, 255, 255, 0.9);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    z-index: 999;
}

.loading-icon {
    font-size: 48px;
    color: #409eff;
    animation: rotate 2s linear infinite;
}

.loading-text {
    margin-top: 16px;
    font-size: 16px;
    color: #409eff;
}

@keyframes rotate {
    0% {
        transform: rotate(0deg);
    }

    100% {
        transform: rotate(360deg);
    }
}

/* 列表项加载占位符 */
.loading-placeholder {
    padding: 10px;
    border-radius: 8px;
    border: 1px solid #eaeaea;
    margin-bottom: 8px;
}

.sidebar {
    width: 300px;
    min-width: 300px;
    background-color: white;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 100px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    overflow: hidden;
    margin-right: 16px;
}

.sidebar-section {
    margin-bottom: 24px;
    padding: 0 16px;
}

.sidebar-content {
    padding: 16px 0;
    overflow-y: auto;
    flex: 1;
}

.sidebar-title {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 12px;
    color: #333;
    display: flex;
    align-items: center;
}

/* 检索设置按钮样式优化 */
.settings-button {
    width: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px 0;
}

.button-icon {
    margin-right: 8px;
}

.knowledge-base-list,
.model-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.knowledge-base-item,
.model-item {
    display: flex;
    align-items: center;
    padding: 10px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.3s;
    border: 1px solid #eaeaea;
}

.knowledge-base-item:hover,
.model-item:hover {
    background-color: #f0f7ff;
}

.knowledge-base-item.active,
.model-item.active {
    background-color: #ecf5ff;
    border-color: #409eff;
}

.knowledge-base-info,
.model-info {
    margin-left: 10px;
    flex: 1;
}

.knowledge-base-name,
.model-name {
    font-weight: 500;
    font-size: 14px;
}

.knowledge-base-desc,
.model-provider {
    font-size: 12px;
    color: #888;
    margin-top: 2px;
}

.chat-container {
    flex: 1;
    display: flex;
    flex-direction: column;
    height: calc(100vh - 100px);
    overflow: hidden;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.chat-header {
    padding: 16px 24px;
    background-color: white;
    border-bottom: 1px solid #e6e6e6;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-shrink: 0;
    /* 防止头部被压缩 */
}

.chat-info {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    /* 确保标题左对齐 */
}

.chat-title {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
    text-align: left;
}

.model-info {
    font-size: 13px;
    color: #666;
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
}

.retrieval-info {
    font-size: 12px;
    margin-top: 6px;
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}

.chat-actions {
    display: flex;
    gap: 12px;
    /* 增加按钮间距 */
}

/* 操作按钮样式优化 */
.action-button {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 8px 16px;
}

.messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 16px 24px;
    background-color: #f9f9f9;
    /* 稍微调亮背景色，增加对比 */
    min-height: 0;
    /* 允许flex容器收缩 */
    max-height: calc(100vh - 200px);
    /* 限制最大高度 */
}

.message {
    margin-bottom: 24px;
    max-width: 85%;
    /* 减小一点宽度，让消息气泡看起来更舒适 */
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    /* 添加轻微阴影 */
}

.message.user {
    margin-left: auto;
    background-color: #e8f5e9;
    /* 用户消息使用绿色背景 */
    text-align: right;
    /* 右对齐消息气泡 */
}

.message.assistant {
    margin-right: auto;
    background-color: white;
    /* AI消息使用白色背景 */
    text-align: left;
    /* 左对齐消息气泡 */
}

.message-header {
    display: flex;
    align-items: center;
    margin-bottom: 8px;
    padding: 8px 12px 0;
    /* 添加内边距 */
}

.message.user .message-header {
    flex-direction: row-reverse;
}

.avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
}

.message.user .avatar {
    background-color: #4caf50;
    /* 用户头像颜色 */
    margin-left: 12px;
}

.message.assistant .avatar {
    background-color: #2196f3;
    /* AI头像颜色 */
    margin-right: 12px;
}

.message-info {
    display: flex;
    flex-direction: column;
}

.message.user .message-info {
    align-items: flex-end;
}

.role-name {
    font-size: 14px;
    font-weight: 500;
}

.timestamp {
    font-size: 12px;
    color: #999;
}

.message-content {
    padding: 12px 16px;
    border-radius: 0 0 12px 12px;
    position: relative;
    text-align: left;
    /* 确保所有消息内容都是左对齐的 */
}

.message.user .message-content {
    color: #333;
    /* 深色文字更易读 */
    border-top-right-radius: 2px;
}

.message.assistant .message-content {
    border-top-left-radius: 2px;
}

.loading-content {
    display: flex;
    justify-content: center;
    padding: 20px 0;
}

.typing-indicator {
    display: flex;
    align-items: center;
}

.typing-indicator span {
    height: 8px;
    width: 8px;
    background-color: #606266;
    border-radius: 50%;
    display: inline-block;
    margin: 0 2px;
    opacity: 0.4;
    animation: typing 1.5s infinite;
}

.typing-indicator span:nth-child(1) {
    animation-delay: 0s;
}

.typing-indicator span:nth-child(2) {
    animation-delay: 0.3s;
}

.typing-indicator span:nth-child(3) {
    animation-delay: 0.6s;
}

@keyframes typing {
    0% {
        opacity: 0.4;
        transform: scale(1);
    }

    50% {
        opacity: 1;
        transform: scale(1.2);
    }

    100% {
        opacity: 0.4;
        transform: scale(1);
    }
}

.error-content {
    color: #f56c6c;
    font-weight: 500;
    /* 加粗错误消息 */
    padding: 12px;
    background-color: #fef0f0;
    /* 浅红色背景突出错误 */
    border-radius: 4px;
    margin-top: 4px;
}

.message-citations {
    margin-top: 12px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 8px;
}

.citations-preview {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-wrap: wrap;
}

.citation-preview-tag {
    font-size: 11px;
    padding: 2px 6px;
}

.more-citations {
    font-size: 12px;
    color: #909399;
    margin-left: 4px;
}

.ai-content {
    line-height: 1.6;
}

.ai-content :deep(pre) {
    background-color: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 12px 0;
    /* 增加代码块上下间距 */
}

.ai-content :deep(code) {
    font-family: 'Courier New', Courier, monospace;
    background-color: #f5f7fa;
    padding: 2px 4px;
    border-radius: 2px;
}

.ai-content :deep(p) {
    margin: 10px 0;
    /* 增加段落间距 */
}

.ai-content :deep(ul),
.ai-content :deep(ol) {
    padding-left: 24px;
    margin: 10px 0;
    /* 增加列表间距 */
}

.ai-content :deep(h1),
.ai-content :deep(h2),
.ai-content :deep(h3) {
    margin-top: 20px;
    margin-bottom: 10px;
    font-weight: 600;
    /* 加粗标题 */
}

.input-container {
    padding: 16px 24px;
    background-color: white;
    border-top: 1px solid #e6e6e6;
    flex-shrink: 0;
    /* 防止输入容器被压缩 */
}

.input-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 12px;
}

/* 检索设置弹窗样式优化 */
.retrieval-settings {
    display: flex;
    flex-direction: column;
    gap: 24px;
    padding: 8px;
}

.setting-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    background-color: #f9f9f9;
    border-radius: 8px;
    padding: 16px;
    /* 添加内边距 */
    border: 1px solid #eaeaea;
    /* 添加边框 */
}

.setting-label {
    font-weight: 600;
    /* 加粗标签 */
    font-size: 15px;
    color: #333;
}

.setting-desc {
    font-size: 12px;
    color: #888;
    margin-top: 4px;
}

/* 引用来源弹窗样式优化 */
.citation-dialog :deep(.el-dialog__body),
.citation-dialog :deep(.el-dialog__header),
.citation-dialog :deep(.el-dialog__footer) {
    text-align: left;
}

.citations-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.citations-navigation {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding: 12px 16px;
    background-color: #f5f7fa;
    border-radius: 8px;
    border: 1px solid #e4e7ed;
}

.citation-counter {
    font-size: 14px;
    color: #606266;
    font-weight: 500;
}

.citation-pagination {
    display: flex;
    gap: 8px;
}

.citation-content {
    background-color: #f9f9f9;
    border-radius: 8px;
    padding: 20px;
    /* 增加内边距 */
    border: 1px solid #eaeaea;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
    text-align: left;
    /* 确保内容左对齐 */
}

.citation-header {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 16px;
    /* 增加间距 */
    padding-bottom: 12px;
    /* 增加内边距 */
    border-bottom: 1px solid #eaeaea;
    text-align: left;
    /* 确保标题左对齐 */
}

.citation-meta {
    display: flex;
    align-items: center;
    width: 100%;
}

.citation-tags {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.citation-title {
    font-weight: 600;
    /* 加粗标题 */
    font-size: 16px;
    color: #333;
    text-align: left;
    /* 确保标题文本左对齐 */
}

.source-tag {
    max-width: 100%;
    display: inline-flex;
    align-items: center;
}

.source-label {
    margin-right: 4px;
    flex-shrink: 0;
}

.source-path {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: help;
    transition: all 0.3s ease;
}

.source-path:hover {
    color: #409eff;
}

.similarity-tag {
    background-color: #f0f9ff;
    border-color: #67c23a;
    color: #67c23a;
    font-weight: 500;
}

.citation-text {
    white-space: pre-wrap;
    line-height: 1.6;
    max-height: 300px;
    overflow-y: auto;
    padding: 16px;
    /* 添加内边距 */
    background-color: white;
    /* 白色背景 */
    border-radius: 4px;
    border: 1px solid #eee;
    /* 浅色边框 */
    font-size: 14px;
    color: #333;
    box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.05);
    margin-top: 8px;
    text-align: left;
    /* 确保内容左对齐 */
}

/* 自定义空状态样式 */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 30px 20px;
    color: #909399;
}

.empty-icon {
    font-size: 36px;
    margin-bottom: 12px;
    opacity: 0.6;
}

.empty-text {
    font-size: 14px;
    font-weight: 500;
    color: #606266;
}

.chat-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 300px;
    color: #909399;
}

.chat-empty-icon {
    font-size: 64px;
    margin-bottom: 20px;
    opacity: 0.6;
}

.chat-empty-text {
    font-size: 18px;
    font-weight: 500;
    margin-bottom: 8px;
    color: #606266;
}

.chat-empty-hint {
    font-size: 14px;
    color: #909399;
    text-align: center;
}

/* 响应式设计优化 */
@media (max-width: 768px) {
    .single-chat-container {
        flex-direction: column;
        padding: 8px;
    }

    .sidebar {
        width: 100%;
        height: calc(40vh - 16px);
        margin-right: 0;
        margin-bottom: 8px;
    }

    .chat-container {
        height: calc(60vh - 16px);
    }

    .knowledge-base-list,
    .model-list {
        flex-direction: row;
        overflow-x: auto;
        gap: 12px;
        padding-bottom: 8px;
    }

    .knowledge-base-item,
    .model-item {
        min-width: 200px;
        flex-shrink: 0;
        /* 防止项目被压缩 */
    }

    .chat-header {
        flex-direction: column;
        align-items: flex-start;
    }

    .chat-actions {
        margin-top: 12px;
        width: 100%;
        justify-content: flex-end;
    }

    .message {
        max-width: 95%;
        /* 移动设备上消息宽度更大 */
    }
}

/* 大屏幕优化 */
@media (min-width: 1920px) {
    .sidebar {
        height: calc(100vh - 100px);
    }

    .chat-container {
        height: calc(100vh - 100px);
    }
}

/* 中等屏幕优化 */
@media (min-width: 769px) and (max-width: 1919px) {
    .sidebar {
        height: calc(100vh - 100px);
    }

    .chat-container {
        height: calc(100vh - 100px);
    }
}
</style>
