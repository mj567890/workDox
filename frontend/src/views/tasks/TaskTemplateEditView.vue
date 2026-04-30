<template>
  <div class="template-edit-page">
    <div class="page-header">
      <el-button text @click="$router.push('/task-templates')">&larr; 返回模板列表</el-button>
      <h2 v-if="template">{{ template.name }}</h2>
    </div>

    <div v-loading="loading">
      <!-- Template metadata -->
      <el-card shadow="never" class="section-card">
        <template #header><span>基本信息</span></template>
        <el-form :model="metaForm" label-width="80px" inline>
          <el-form-item label="名称">
            <el-input v-model="metaForm.name" style="width: 220px" />
          </el-form-item>
          <el-form-item label="分类">
            <el-input v-model="metaForm.category" style="width: 180px" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="metaForm.description" style="width: 320px" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleSaveMeta">保存基本信息</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- Stages -->
      <el-card shadow="never" class="section-card">
        <template #header>
          <div class="card-header-row">
            <span>阶段管理（{{ stages.length }} 个阶段）</span>
            <el-button size="small" type="primary" @click="openAddStage">+ 添加阶段</el-button>
          </div>
        </template>

        <el-collapse v-model="activeStages">
          <el-collapse-item
            v-for="(stage, si) in stages"
            :key="stage.id || si"
            :name="String(stage.id || 'new-' + si)"
          >
            <template #title>
              <div class="stage-title">
                <el-tag>{{ stage.order }}</el-tag>
                <span>{{ stage.name }}</span>
                <span class="stage-desc" v-if="stage.description">{{ stage.description }}</span>
                <el-button text size="small" type="danger" @click.stop="handleDeleteStage(si)">删除阶段</el-button>
              </div>
            </template>

            <!-- Stage metadata -->
            <div class="stage-meta">
              <el-input v-model="stage.name" placeholder="阶段名称" size="small" style="width: 180px" @change="saveStage(si)" />
              <el-input v-model="stage.description" placeholder="阶段描述" size="small" style="width: 240px" @change="saveStage(si)" />
              <el-input-number v-model="stage.order" :min="1" size="small" style="width: 80px" controls-position="right" @change="saveStage(si)" />
              <el-input-number v-model="stage.deadline_offset_days" :min="0" placeholder="截止天数" size="small" style="width: 100px" controls-position="right" @change="saveStage(si)" />
            </div>

            <!-- Slots -->
            <div class="slot-section">
              <div class="slot-header">
                <span>文档槽位（{{ stage.slots?.length || 0 }} 个）</span>
                <el-button size="small" @click="openAddSlot(si)">+ 添加槽位</el-button>
              </div>
              <el-table :data="stage.slots || []" size="small" border>
                <el-table-column prop="name" label="槽位名称" min-width="150">
                  <template #default="{ row: slot }">
                    <el-input v-model="slot.name" size="small" />
                  </template>
                </el-table-column>
                <el-table-column prop="description" label="描述" min-width="160">
                  <template #default="{ row: slot }">
                    <el-input v-model="slot.description" size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="必填" width="70">
                  <template #default="{ row: slot }">
                    <el-switch v-model="slot.is_required" size="small" />
                  </template>
                </el-table-column>
                <el-table-column label="文件类型提示" width="160">
                  <template #default="{ row: slot }">
                    <el-input v-model="slot.file_type_hints_display" size="small" placeholder="pdf,docx" />
                  </template>
                </el-table-column>
                <el-table-column label="排序" width="70">
                  <template #default="{ row: slot }">
                    <el-input-number v-model="slot.sort_order" :min="0" size="small" controls-position="right" />
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="{ $index: slotIdx, row: slot }">
                    <el-button size="small" @click="saveSlot(si, slotIdx)">保存</el-button>
                    <el-button size="small" type="danger" @click="handleDeleteSlot(si, slotIdx)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-collapse-item>
        </el-collapse>

        <el-empty v-if="!stages.length" description="暂无阶段，点击上方按钮添加" />
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useTaskMgmtStore } from '@/stores/task-mgmt'
import { taskTemplatesApi } from '@/api/task-templates'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const store = useTaskMgmtStore()
const loading = ref(false)
const template = ref<any>(null)
const stages = ref<any[]>([])
const activeStages = ref<string[]>([])
const metaForm = reactive({ name: '', category: '', description: '' })

const templateId = computed(() => Number(route.params.id))

onMounted(async () => {
  loading.value = true
  try {
    template.value = await taskTemplatesApi.getDetail(templateId.value)
    metaForm.name = template.value.name
    metaForm.category = template.value.category || ''
    metaForm.description = template.value.description || ''
    stages.value = (template.value.stages || []).map((s: any) => ({
      ...s,
      slots: (s.slots || []).map((sl: any) => ({
        ...sl,
        file_type_hints_display: sl.file_type_hints?.join(',') || '',
      })),
    }))
    activeStages.value = stages.value.map((s: any) => String(s.id))
  } finally {
    loading.value = false
  }
})

async function handleSaveMeta() {
  await taskTemplatesApi.update(templateId.value, {
    name: metaForm.name,
    category: metaForm.category || undefined,
    description: metaForm.description || undefined,
  })
  ElMessage.success('基本信息已保存')
}

// ── Stage operations ──

async function openAddStage() {
  const stage = await taskTemplatesApi.addStage(templateId.value, {
    name: '新阶段',
    order: stages.value.length + 1,
  })
  stages.value.push({
    ...stage,
    slots: [],
  })
  activeStages.value.push(String(stage.id))
  ElMessage.success('阶段已添加')
}

async function saveStage(si: number) {
  const s = stages.value[si]
  if (!s.id) return
  await taskTemplatesApi.updateStage(templateId.value, s.id, {
    name: s.name,
    order: s.order,
    description: s.description,
    deadline_offset_days: s.deadline_offset_days,
  })
}

async function handleDeleteStage(si: number) {
  const s = stages.value[si]
  if (!s.id) {
    stages.value.splice(si, 1)
    return
  }
  try {
    await ElMessageBox.confirm(`删除阶段「${s.name}」及其下所有槽位？`, '确认删除', { type: 'warning' })
    await taskTemplatesApi.deleteStage(templateId.value, s.id)
    stages.value.splice(si, 1)
    ElMessage.success('阶段已删除')
  } catch { /* cancelled */ }
}

// ── Slot operations ──

async function openAddSlot(si: number) {
  const stage = stages.value[si]
  const slot = await taskTemplatesApi.addSlot(templateId.value, stage.id, {
    name: '新槽位',
    is_required: true,
    sort_order: (stage.slots || []).length + 1,
  })
  if (!stage.slots) stage.slots = []
  stage.slots.push({ ...slot, file_type_hints_display: '' })
  ElMessage.success('槽位已添加')
}

async function saveSlot(si: number, slotIdx: number) {
  const stage = stages.value[si]
  const slot = stage.slots[slotIdx]
  if (!slot.id) return
  await taskTemplatesApi.updateSlot(templateId.value, stage.id, slot.id, {
    name: slot.name,
    description: slot.description,
    is_required: slot.is_required,
    file_type_hints: slot.file_type_hints_display
      ? slot.file_type_hints_display.split(',').map((s: string) => s.trim()).filter(Boolean)
      : null,
    sort_order: slot.sort_order,
  })
  ElMessage.success('槽位已保存')
}

async function handleDeleteSlot(si: number, slotIdx: number) {
  const stage = stages.value[si]
  const slot = stage.slots[slotIdx]
  if (!slot.id) {
    stage.slots.splice(slotIdx, 1)
    return
  }
  try {
    await ElMessageBox.confirm(`删除槽位「${slot.name}」？`, '确认删除', { type: 'warning' })
    await taskTemplatesApi.deleteSlot(templateId.value, stage.id, slot.id)
    stage.slots.splice(slotIdx, 1)
    ElMessage.success('槽位已删除')
  } catch { /* cancelled */ }
}
</script>

<style scoped>
.template-edit-page { padding: 20px; max-width: 1200px; }
.page-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
.page-header h2 { margin: 0; }
.section-card { margin-bottom: 20px; }
.card-header-row { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.stage-title { display: flex; align-items: center; gap: 10px; flex: 1; }
.stage-desc { color: #909399; font-size: 13px; margin-left: 8px; }
.stage-meta { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; padding: 8px 0; }
.slot-section { padding: 8px 0; }
.slot-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; font-size: 13px; color: #606266; }
</style>
