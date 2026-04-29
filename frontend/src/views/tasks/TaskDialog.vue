<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑任务' : '创建任务'"
    width="600px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="任务标题" prop="title">
        <el-input v-model="form.title" placeholder="请输入任务标题" />
      </el-form-item>
      <el-form-item label="关联事项" prop="matter_id">
        <el-select v-model="form.matter_id" placeholder="选择关联事项" filterable>
          <el-option
            v-for="m in matters"
            :key="m.id"
            :label="`${m.matter_no} ${m.title}`"
            :value="m.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="负责人" prop="assignee_id">
        <el-select v-model="form.assignee_id" placeholder="选择负责人" filterable>
          <el-option
            v-for="u in users"
            :key="u.id"
            :label="u.real_name"
            :value="u.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级" prop="priority">
        <el-select v-model="form.priority" placeholder="选择优先级">
          <el-option label="低" value="low" />
          <el-option label="中" value="medium" />
          <el-option label="高" value="high" />
          <el-option label="紧急" value="urgent" />
        </el-select>
      </el-form-item>
      <el-form-item label="截止时间" prop="due_time">
        <el-date-picker
          v-model="form.due_time"
          type="datetime"
          placeholder="选择截止时间"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DDTHH:mm:ss"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="4"
          placeholder="请输入任务描述"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '保存' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from 'vue'
import { tasksApi, type TaskItem } from '@/api/tasks'
import { mattersApi, type MatterItem } from '@/api/matters'
import { usersApi, type UserItem } from '@/api/users'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

const props = defineProps<{
  modelValue: boolean
  task: TaskItem | null
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'saved': []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const isEdit = computed(() => props.task !== null)

const formRef = ref<FormInstance>()
const submitting = ref(false)
const matters = ref<MatterItem[]>([])
const users = ref<UserItem[]>([])

const form = reactive({
  title: '',
  matter_id: null as number | null,
  assignee_id: null as number | null,
  priority: 'medium',
  due_time: '' as string | null,
  description: '',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入任务标题', trigger: 'blur' }],
  matter_id: [{ required: true, message: '请选择关联事项', trigger: 'change' }],
  assignee_id: [{ required: true, message: '请选择负责人', trigger: 'change' }],
  priority: [{ required: true, message: '请选择优先级', trigger: 'change' }],
}

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      if (props.task) {
        form.title = props.task.title
        form.matter_id = props.task.matter_id
        form.assignee_id = props.task.assignee_id
        form.priority = props.task.priority
        form.due_time = props.task.due_time ? formatForPicker(props.task.due_time) : ''
        form.description = props.task.description || ''
      } else {
        resetForm()
      }
      loadOptions()
    }
  },
)

function formatForPicker(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

async function loadOptions() {
  if (matters.value.length === 0) {
    mattersApi.getList({ page_size: 500 }).then((res) => {
      matters.value = res.items
    })
  }
  if (users.value.length === 0) {
    usersApi.getList({ page_size: 500 }).then((res) => {
      users.value = res.items
    })
  }
}

function resetForm() {
  form.title = ''
  form.matter_id = null
  form.assignee_id = null
  form.priority = 'medium'
  form.due_time = ''
  form.description = ''
  formRef.value?.resetFields()
}

function handleClose() {
  visible.value = false
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const data: Record<string, any> = {
      title: form.title,
      matter_id: form.matter_id,
      assignee_id: form.assignee_id,
      priority: form.priority,
      description: form.description || undefined,
    }
    if (form.due_time) {
      data.due_time = form.due_time
    }

    if (props.task) {
      await tasksApi.update(props.task.id, data)
      ElMessage.success('任务更新成功')
    } else {
      await tasksApi.create(data)
      ElMessage.success('任务创建成功')
    }
    visible.value = false
    emit('saved')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
</style>
