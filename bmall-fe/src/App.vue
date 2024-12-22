<template>
  <div class="container">
    <el-container>
      <el-header>
        <h1>B站同人商城</h1>
      </el-header>
      <el-main>
        <sku-list />
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import SkuList from './components/SkuList.vue'
</script>

<style>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.el-header {
  text-align: center;
  padding: 20px 0;
}

h1 {
  color: #409EFF;
  margin: 0;
}
</style>
