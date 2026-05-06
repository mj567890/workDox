<template>
  <div class="ai-chat-container">
    <!-- Sidebar -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" @click="store.newChat()" :icon="Plus">
          新对话
        </el-button>
      </div>
      <el-scrollbar height="calc(100vh - 140px)">
        <div
          v-for="conv in store.conversations"
          :key="conv.id"
          class="conv-item"
          :class="{ active: conv.id === store.currentConversationId }"
          @click="selectConversation(conv.id)"
        >
          <div class="conv-title">{{ conv.title }}</div>
          <div class="conv-meta">{{ conv.message_count }} 条消息</div>
          <el-button
            class="conv-delete"
            text
            size="small"
            type="danger"
            :icon="Delete"
            @click.stop="handleDelete(conv.id)"
          />
        </div>
        <el-empty v-if="store.conversations.length === 0" description="暂无对话" />
      </el-scrollbar>
    </div>

    <!-- Main Chat -->
    <div class="chat-main">
      <div class="chat-header">
        <span class="chat-title">文档智能助手</span>
        <el-select
          v-model="store.selectedProviderId"
          placeholder="选择 AI 模型"
          style="width: 220px; margin-left: 16px"
          size="default"
        >
          <el-option
            v-for="p in store.providers"
            :key="p.id"
            :label="`${p.name} (${p.model})`"
            :value="p.id"
          />
        </el-select>
      </div>

      <div class="chat-messages" ref="messagesContainer">
        <el-empty v-if="store.currentMessages.length === 0" description="开始提问吧" />
        <div
          v-for="msg in store.currentMessages"
          :key="msg.id"
          class="message-row"
          :class="msg.role"
        >
          <div class="message-avatar">
            <el-avatar v-if="msg.role === 'user'" :size="32" :icon="UserFilled" />
            <el-avatar v-else :size="32" style="background: #409EFF">
              AI
            </el-avatar>
          </div>
          <div class="message-content">
            <div class="message-text">{{ msg.content }}</div>
            <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
              <el-collapse>
                <el-collapse-item title="参考来源">
                  <div
                    v-for="(s, i) in msg.sources"
                    :key="i"
                    class="source-item"
                  >
                    <span class="source-doc">{{ s.document_name }}</span>
                    <span class="source-sim">相似度 {{ (s.similarity * 100).toFixed(0) }}%</span>
                    <p class="source-text">{{ s.text_snippet }}</p>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="3"
          placeholder="输入问题，AI 将根据文档内容回答..."
          :disabled="store.loading"
          @keydown.enter.exact.prevent="handleSend"
        />
        <el-button
          type="primary"
          :loading="store.loading"
          :icon="Promotion"
          @click="handleSend"
          style="margin-top: 8px"
        >
          发送
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { Plus, Delete, UserFilled, Promotion } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAIStore } from '@/stores/ai'

const store = useAIStore()
const inputText = ref('')
const messagesContainer = ref<HTMLElement>()

onMounted(async () => {
  try {
    await Promise.all([
      store.fetchConversations(),
      store.fetchProviders(),
    ])
  } catch {
    // API interceptor handles error messages
  }
})

async function selectConversation(id: number) {
  try {
    await store.fetchMessages(id)
  } catch {
    // API interceptor handles error messages
  }
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  await store.sendMessage(text)
  scrollToBottom()
}

async function handleDelete(convId: number) {
  try {
    await ElMessageBox.confirm('确定删除该对话？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })
    await store.deleteConversation(convId)
    ElMessage.success('已删除')
  } catch {
    // cancelled
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}
</script>

<style scoped>
.ai-chat-container {
  display: flex;
  height: calc(100vh - 64px);
  background: var(--el-bg-color-page);
}

.chat-sidebar {
  width: 260px;
  border-right: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color);
}

.conv-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid var(--el-border-color-lighter);
  position: relative;
}
.conv-item:hover,
.conv-item.active {
  background: var(--el-fill-color-light);
}
.conv-title {
  font-size: 14px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 24px;
}
.conv-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
.conv-delete {
  position: absolute;
  right: 8px;
  top: 8px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
  display: flex;
  align-items: center;
}
.chat-title {
  font-size: 18px;
  font-weight: 600;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.message-row {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.message-row.user {
  flex-direction: row-reverse;
}
.message-row.user .message-content {
  text-align: right;
}
.message-avatar {
  flex-shrink: 0;
}

.message-content {
  max-width: 70%;
}
.message-text {
  background: var(--el-bg-color);
  padding: 12px 16px;
  border-radius: 8px;
  line-height: 1.6;
  white-space: pre-wrap;
}
.message-row.user .message-text {
  background: var(--el-color-primary-light-9);
}

.message-sources {
  margin-top: 8px;
  font-size: 13px;
}
.source-item {
  padding: 8px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.source-doc {
  font-weight: 500;
}
.source-sim {
  margin-left: 8px;
  color: var(--el-color-success);
  font-size: 12px;
}
.source-text {
  color: var(--el-text-color-secondary);
  margin: 4px 0 0;
  font-size: 12px;
}

.chat-input {
  padding: 16px 24px;
  border-top: 1px solid var(--el-border-color);
  background: var(--el-bg-color);
}
</style>
