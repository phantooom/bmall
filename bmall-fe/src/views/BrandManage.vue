<template>
  <div class="brand-manage">
    <div class="header">
      <h2>品牌管理</h2>
      <el-button type="primary" @click="showAddDialog">
        添加品牌
      </el-button>
    </div>

    <el-table :data="brands" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="品牌名称" />
      <el-table-column prop="total_items" label="商品数量" width="120" />
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button 
            type="danger" 
            size="small" 
            :disabled="row.total_items > 0"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加品牌对话框 -->
    <el-dialog
      v-model="dialogVisible"
      title="添加品牌"
      width="500px"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="80px"
      >
        <el-form-item label="品牌名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入品牌名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit">
            确定
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import axios from 'axios'

interface Brand {
  id: number
  name: string
  total_items: number
}

const brands = ref<Brand[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const formRef = ref<FormInstance>()

const form = ref({
  name: ''
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入品牌名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ]
}

// 获取品牌列表
const fetchBrands = async () => {
  loading.value = true
  try {
    const response = await axios.get<Brand[]>('http://localhost:8000/api/brands')
    brands.value = response.data
  } catch (error) {
    ElMessage.error('获取品牌列表失败')
  } finally {
    loading.value = false
  }
}

// 显示添加对话框
const showAddDialog = () => {
  form.value.name = ''
  dialogVisible.value = true
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        const response = await axios.post('http://localhost:8000/api/brands', form.value)
        if (response.data.success) {
          ElMessage.success('添加成功')
          dialogVisible.value = false
          fetchBrands()
        }
      } catch (error) {
        ElMessage.error('添加失败')
      }
    }
  })
}

// 删除品牌
const handleDelete = async (brand: Brand) => {
  if (brand.total_items > 0) {
    ElMessage.warning('该品牌下还有商品，不能删除')
    return
  }

  try {
    await ElMessageBox.confirm(
      '确定要删除该品牌吗？',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const response = await axios.delete(`http://localhost:8000/api/brands/${brand.id}`)
    if (response.data.success) {
      ElMessage.success('删除成功')
      fetchBrands()
    }
  } catch (error) {
    if (error instanceof Error) {
      ElMessage.error('删除失败：' + error.message)
    }
  }
}

onMounted(() => {
  fetchBrands()
})
</script>

<style scoped>
.brand-manage {
  padding: 20px 0;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

h2 {
  margin: 0;
  font-size: 24px;
  color: #303133;
}
</style> 