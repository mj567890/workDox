<template>
  <div class="department-management">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">部门管理</span>
          <el-button type="primary" @click="handleAddRoot">
            <el-icon><Plus /></el-icon>添加顶级部门
          </el-button>
        </div>
      </template>

      <el-table
        :data="treeData"
        row-key="id"
        v-loading="loading"
        :tree-props="{ children: 'children' }"
        default-expand-all
        stripe
      >
        <template #empty>
          <el-empty description="暂无部门数据" />
        </template>
        <el-table-column prop="name" label="部门名称" min-width="200" />
        <el-table-column prop="code" label="部门编码" width="200" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleAddChild(row)">
              添加子部门
            </el-button>
            <el-button text type="primary" size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-button text type="danger" size="small" @click="handleDelete(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="480px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <el-form-item label="部门名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入部门名称" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="部门编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入部门编码" maxlength="50" />
        </el-form-item>
        <el-form-item label="上级部门">
          <el-tree-select
            v-model="form.parent_id"
            :data="parentOptions"
            :props="{ label: 'name', value: 'id', children: 'children' }"
            check-strictly
            node-key="id"
            clearable
            placeholder="无（顶级部门）"
            class="tree-select-full"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Plus } from '@element-plus/icons-vue'
import { usersApi, type DepartmentItem } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormRules, FormInstance } from 'element-plus'

// -------------------------------------------------------------------
// Types
// -------------------------------------------------------------------

interface TreeNode extends DepartmentItem {
  children?: TreeNode[]
}

// -------------------------------------------------------------------
// Reactive state
// -------------------------------------------------------------------

const loading = ref(false)
const departments = ref<DepartmentItem[]>([])
const treeData = ref<TreeNode[]>([])

const dialogVisible = ref(false)
const editingRow = ref<DepartmentItem | null>(null)
const saving = ref(false)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  code: '',
  parent_id: null as number | null,
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入部门名称', trigger: 'blur' },
  ],
  code: [
    { required: true, message: '请输入部门编码', trigger: 'blur' },
  ],
}

// -------------------------------------------------------------------
// Computed
// -------------------------------------------------------------------

const dialogTitle = computed(() => {
  if (editingRow.value) return '编辑部门'
  return '添加部门'
})

/**
 * 上级部门可选列表（从当前平铺列表构建树，编辑时排除自身及子部门防止循环）
 */
const parentOptions = computed(() => {
  return buildParentTree(departments.value, editingRow.value?.id)
})

// -------------------------------------------------------------------
// Tree building helpers
// -------------------------------------------------------------------

/**
 * 将平铺的部门列表构建为树形结构，用于 el-table 展示。
 * 叶子节点不包含 children 字段，避免展开箭头误显。
 */
function buildTree(items: DepartmentItem[]): TreeNode[] {
  const map = new Map<number, TreeNode>()
  const roots: TreeNode[] = []

  // 第一遍：为每个部门创建节点，初始化空的 children 数组
  for (const item of items) {
    map.set(item.id, { ...item, children: [] })
  }

  // 第二遍：建立父子关系
  for (const item of items) {
    const node = map.get(item.id)!
    if (item.parent_id === null || !map.has(item.parent_id)) {
      roots.push(node)
    } else {
      map.get(item.parent_id)!.children!.push(node)
    }
  }

  // 清除叶子节点上的空 children 数组
  const stack = [...roots]
  while (stack.length) {
    const node = stack.pop()!
    if (node.children!.length === 0) {
      delete node.children
    } else {
      stack.push(...node.children!)
    }
  }

  return roots
}

/**
 * 为上级部门选择器构建树，编辑时排除正在编辑的节点及其子孙，
 * 防止将部门挂载到自己或自己的子部门下。
 */
function buildParentTree(items: DepartmentItem[], excludeId?: number): TreeNode[] {
  const tree = buildTree(items)
  if (excludeId == null) return tree

  // 深拷贝后移除被排除的子树
  const cloned = JSON.parse(JSON.stringify(tree)) as TreeNode[]
  removeSubtree(cloned, excludeId)
  return cloned
}

/** 在树中移除指定 id 的节点（含其子树） */
function removeSubtree(nodes: TreeNode[], id: number): boolean {
  for (let i = nodes.length - 1; i >= 0; i--) {
    if (nodes[i].id === id) {
      nodes.splice(i, 1)
      return true
    }
    if (nodes[i].children) {
      if (removeSubtree(nodes[i].children!, id)) return true
    }
  }
  return false
}

// -------------------------------------------------------------------
// Data fetching
// -------------------------------------------------------------------

async function fetchData() {
  loading.value = true
  try {
    departments.value = await usersApi.getDepartments()
    treeData.value = buildTree(departments.value)
  } finally {
    loading.value = false
  }
}

// -------------------------------------------------------------------
// Form helpers
// -------------------------------------------------------------------

function resetForm() {
  form.name = ''
  form.code = ''
  form.parent_id = null
  editingRow.value = null
  formRef.value?.clearValidate()
}

// -------------------------------------------------------------------
// Event handlers
// -------------------------------------------------------------------

function handleAddRoot() {
  resetForm()
  dialogVisible.value = true
}

function handleAddChild(row: DepartmentItem) {
  resetForm()
  form.parent_id = row.id
  dialogVisible.value = true
}

function handleEdit(row: DepartmentItem) {
  editingRow.value = row
  form.name = row.name
  form.code = row.code
  form.parent_id = row.parent_id
  dialogVisible.value = true
}

async function handleSave() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const data: Record<string, any> = {
      name: form.name,
      code: form.code,
      parent_id: form.parent_id,
    }

    if (editingRow.value) {
      await usersApi.updateDepartment(editingRow.value.id, data)
      ElMessage.success('部门已更新')
    } else {
      await usersApi.createDepartment(data)
      ElMessage.success('部门已创建')
    }

    dialogVisible.value = false
    resetForm()
    await fetchData()
  } finally {
    saving.value = false
  }
}

async function handleDelete(row: DepartmentItem) {
  // 判断当前部门是否有子部门
  const hasChildren = departments.value.some((d) => d.parent_id === row.id)

  try {
    await ElMessageBox.confirm(
      hasChildren
        ? `确认删除部门"${row.name}"？该部门下存在子部门，删除后将一并移除。`
        : `确认删除部门"${row.name}"？`,
      '确认删除',
      {
        confirmButtonText: '确认删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    )
    await usersApi.deleteDepartment(row.id)
    ElMessage.success('部门已删除')
    await fetchData()
  } catch {
    // 用户取消操作
  }
}

// -------------------------------------------------------------------
// Lifecycle
// -------------------------------------------------------------------

onMounted(fetchData)
</script>

<style scoped>
.department-management {
  padding: 0;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
}

.tree-select-full {
  width: 100%;
}
</style>
