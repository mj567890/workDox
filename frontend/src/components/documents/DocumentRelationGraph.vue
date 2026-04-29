<template>
  <el-card header="文档关联图谱" shadow="never">
    <div v-if="loading" style="height: 400px; display: flex; align-items: center; justify-content: center">
      <el-skeleton animated :rows="5" />
    </div>
    <div v-else-if="!hasData" style="height: 400px; display: flex; align-items: center; justify-content: center">
      <el-empty description="暂无关联数据" />
    </div>
    <div v-else ref="chartRef" style="height: 400px"></div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'
import { documentsApi, type GraphData } from '@/api/documents'

const props = defineProps<{
  docId: number
}>()

const chartRef = ref<HTMLElement>()
const loading = ref(true)
const hasData = ref(false)
let chart: echarts.ECharts | null = null
let resizeHandler: (() => void) | null = null

async function loadData() {
  loading.value = true
  try {
    const data = await documentsApi.getDocumentGraph(props.docId)
    if (data && data.nodes?.length > 0) {
      hasData.value = true
      await nextTick()
      renderChart(data)
    } else {
      hasData.value = false
    }
  } catch {
    hasData.value = false
  } finally {
    loading.value = false
  }
}

function renderChart(data: GraphData) {
  if (!chartRef.value) return

  if (chart) chart.dispose()

  chart = echarts.init(chartRef.value)

  const categoryColors: Record<number, string> = {
    0: '#409EFF',  // source
    1: '#67C23A',  // same matter
    2: '#E6A23C',  // similar
    3: '#909399',  // same tags
  }

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'edge') {
          return params.data.label || ''
        }
        const d = params.data
        return `<b>${d.name}</b><br/>类型: ${['当前文档', '同事项', '内容相似', '相同标签'][d.category] || '其他'}`
      },
    },
    legend: {
      data: data.categories?.map((c: any) => c.name) || ['当前文档', '同事项', '内容相似', '相同标签'],
      bottom: 0,
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        force: {
          repulsion: 200,
          gravity: 0.1,
          edgeLength: [100, 250],
        },
        data: data.nodes.map((n) => ({
          ...n,
          itemStyle: { color: categoryColors[n.category] || '#409EFF' },
          label: {
            show: n.category === 0,
            position: 'right',
            fontSize: 12,
          },
        })),
        links: data.links.map((l) => ({
          ...l,
          label: {
            show: true,
            fontSize: 10,
            formatter: l.label,
          },
          lineStyle: {
            curveness: 0.2,
          },
        })),
        categories: data.categories?.map((c: any, i: number) => ({
          name: c.name,
          itemStyle: { color: categoryColors[i] || '#409EFF' },
        })),
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 2 },
        },
      },
    ],
  })

  resizeHandler = () => chart?.resize()
  window.addEventListener('resize', resizeHandler)

  // Click to navigate
  chart.on('click', (params: any) => {
    if (params.dataType === 'node') {
      const id = params.data.id
      if (id && id.startsWith('doc_')) {
        const docId = id.replace('doc_', '')
        if (Number(docId) !== props.docId) {
          window.open(`/documents/${docId}`, '_blank')
        }
      }
    }
  })
}

onBeforeUnmount(() => {
  if (resizeHandler) {
    window.removeEventListener('resize', resizeHandler)
  }
  chart?.dispose()
})

watch(() => props.docId, () => {
  if (props.docId) loadData()
}, { immediate: true })
</script>
