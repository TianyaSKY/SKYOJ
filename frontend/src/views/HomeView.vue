<template>
  <div class="home-container">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="title">SKYOJ</h1>
        <p class="subtitle">一个开源的在线评测与知识共享平台</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" round @click="$router.push('/problems')">
            开始编程 <el-icon class="el-icon--right"><ArrowRight /></el-icon>
          </el-button>
          <el-button size="large" round @click="scrollToAbout">
            了解更多
          </el-button>
        </div>
      </div>
    </div>

    <!-- About Section -->
    <div class="section-container" id="about-section">
      <h2 class="section-title">关于 SKYOJ</h2>
      <el-row :gutter="40" align="middle">
        <el-col :span="14">
          <p class="about-text">
            SKYOJ 是一个专为学生、教育工作者和编程爱好者设计的现代化开源在线评测系统（Online Judge）。
            它提供了一个强大的平台，用于练习算法、举办比赛以及分享编程知识。
          </p>
          <p class="about-text">
            我们的使命是通过提供易于访问的工具和资源来普及计算机科学教育。
            无论您是学习 Python 的初学者，还是解决复杂图论问题的专家，SKYOJ 都能为您的学习之旅提供支持。
          </p>
          <div class="features-list">
            <div class="feature-item"><el-icon class="feature-icon"><Check /></el-icon> 实时代码评测</div>
            <div class="feature-item"><el-icon class="feature-icon"><Check /></el-icon> 多编程语言支持</div>
            <div class="feature-item"><el-icon class="feature-icon"><Check /></el-icon> Kaggle 模式竞赛</div>
            <div class="feature-item"><el-icon class="feature-icon"><Check /></el-icon> 开放知识库</div>
          </div>
        </el-col>
        <el-col :span="10">
          <div class="about-image-placeholder">
            <el-icon :size="120" color="#409eff"><Platform /></el-icon>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- External Resources Section -->
    <div class="section-container">
      <h2 class="section-title">开源知识资源</h2>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" :lg="6" v-for="resource in resources" :key="resource.name" class="mb-4">
          <el-card shadow="hover" class="resource-card" @click="openLink(resource.url)">
            <div class="resource-content">
              <div class="resource-icon" :style="{ color: resource.color }">
                <el-icon :size="40"><component :is="resource.icon" /></el-icon>
              </div>
              <h3>{{ resource.name }}</h3>
              <p>{{ resource.description }}</p>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- Documentation / Modes Section -->
    <div class="section-container" id="docs-section">
      <h2 class="section-title">评测模式介绍</h2>
      <el-row :gutter="30">
        <el-col :xs="24" :md="8" v-for="mode in modes" :key="mode.title" class="mb-4">
          <el-card class="mode-card" shadow="hover" @click="$router.push(mode.route)">
            <div class="mode-icon">
              <el-icon :size="50" :color="mode.color"><component :is="mode.icon" /></el-icon>
            </div>
            <h3>{{ mode.title }}</h3>
            <p class="mode-desc">{{ mode.description }}</p>
            <ul class="mode-features">
              <li v-for="feature in mode.features" :key="feature">
                <el-icon class="feature-check"><Check /></el-icon> {{ feature }}
              </li>
            </ul>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import {
  ArrowRight, Check, Platform, Link, Share, Reading, DataLine,
  Cpu, DataAnalysis, Connection, ChatLineSquare, MagicStick
} from '@element-plus/icons-vue'

const resources = [
  {
    name: 'GitHub',
    description: '全球最大的代码托管平台。',
    url: 'https://github.com',
    icon: 'Share',
    color: '#333'
  },
  {
    name: 'Stack Overflow',
    description: '开发者问答社区。',
    url: 'https://stackoverflow.com',
    icon: 'ChatLineSquare',
    color: '#f48024'
  },
  {
    name: 'MDN Web Docs',
    description: 'Web 开发权威文档。',
    url: 'https://developer.mozilla.org',
    icon: 'Reading',
    color: '#000'
  },
  {
    name: 'OI Wiki',
    description: '免费的编程竞赛知识库。',
    url: 'https://oi-wiki.org/',
    icon: 'DataLine',
    color: '#0052cc'
  },
  {
    name: 'Python 文档',
    description: 'Python 官方文档。',
    url: 'https://docs.python.org/zh-cn/3/',
    icon: 'Link',
    color: '#3776ab'
  },
  {
    name: 'CppReference',
    description: 'C++ 标准库参考手册。',
    url: 'https://zh.cppreference.com/',
    icon: 'Link',
    color: '#004482'
  },
  {
    name: 'Hugging Face',
    description: '构建未来的 AI 社区。',
    url: 'https://huggingface.co/',
    icon: 'MagicStick',
    color: '#FFD21E'
  },
  {
    name: 'Kaggle',
    description: '数据科学与机器学习之家。',
    url: 'https://www.kaggle.com/',
    icon: 'DataAnalysis',
    color: '#20BEFF'
  }
]

const modes = [
  {
    title: 'ACM 模式',
    description: '经典的算法竞赛模式，重点考察算法设计与数据结构。',
    icon: 'Cpu',
    color: '#409eff',
    route: '/docs/acm',
    features: [
      '标准输入输出 (stdin/stdout)',
      '严格的时间与内存限制',
      '即时评测反馈 (AC/WA/TLE)',
      '支持多种编程语言'
    ]
  },
  {
    title: 'Kaggle 模式',
    description: '数据科学与机器学习竞赛模式，解决实际数据问题。',
    icon: 'DataAnalysis',
    color: '#67c23a',
    route: '/docs/kaggle',
    features: [
      '基于 CSV 文件的预测提交',
      '大数据集处理与分析',
      '模型准确率评分',
      '适合 AI 与数据挖掘任务'
    ]
  },
  {
    title: 'OOP 模式',
    description: '面向对象编程模式，考察代码设计与工程能力。',
    icon: 'Connection',
    color: '#e6a23c',
    route: '/docs/oop',
    features: [
      '实现特定的类与接口',
      '单元测试覆盖',
      '代码结构与设计模式',
      '适合 Java/C++ 工程实践'
    ]
  }
]

const scrollToAbout = () => {
  document.getElementById('about-section')?.scrollIntoView({ behavior: 'smooth' })
}

const openLink = (url) => {
  window.open(url, '_blank')
}
</script>

<style scoped>
.home-container {
  /* padding handled by layout */
}

.hero-section {
  background: linear-gradient(135deg, var(--el-color-primary-light-8) 0%, var(--el-color-primary-light-9) 100%);
  border-radius: 16px;
  padding: 80px 40px;
  text-align: center;
  margin-bottom: 60px;
}

.title {
  font-size: 3.5rem;
  font-weight: 800;
  color: var(--el-text-color-primary);
  margin: 0 0 15px;
  letter-spacing: -1px;
}

.subtitle {
  font-size: 1.5rem;
  color: var(--el-text-color-secondary);
  margin: 0 0 40px;
  font-weight: 300;
}

.hero-actions {
  display: flex;
  gap: 20px;
  justify-content: center;
}

.section-container {
  margin-bottom: 80px;
}

.section-title {
  text-align: center;
  font-size: 2rem;
  margin-bottom: 40px;
  color: var(--el-text-color-primary);
  position: relative;
}

.section-title::after {
  content: '';
  display: block;
  width: 60px;
  height: 4px;
  background-color: var(--el-color-primary);
  margin: 10px auto 0;
  border-radius: 2px;
}

.about-text {
  font-size: 1.1rem;
  line-height: 1.8;
  color: var(--el-text-color-regular);
  margin-bottom: 20px;
}

.features-list {
  margin-top: 30px;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 15px;
}

.feature-item {
  display: flex;
  align-items: center;
  font-size: 1.1rem;
  color: var(--el-text-color-primary);
}

.feature-icon {
  color: var(--el-color-success);
  margin-right: 10px;
  font-weight: bold;
}

.about-image-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 300px;
  background-color: var(--el-fill-color-light);
  border-radius: 16px;
}

.resource-card {
  cursor: pointer;
  transition: transform 0.3s, box-shadow 0.3s;
  height: 100%;
  text-align: center;
}

.resource-card:hover {
  transform: translateY(-5px);
  box-shadow: var(--el-box-shadow-light);
}

.resource-content {
  padding: 20px 10px;
}

.resource-icon {
  margin-bottom: 15px;
}

.resource-content h3 {
  margin: 10px 0;
  font-size: 1.2rem;
}

.resource-content p {
  color: var(--el-text-color-secondary);
  font-size: 0.9rem;
  margin: 0;
}

.mb-4 {
  margin-bottom: 20px;
}

/* Mode Card Styles */
.mode-card {
  height: 100%;
  text-align: center;
  transition: transform 0.3s;
  cursor: pointer; /* Added cursor pointer */
}

.mode-card:hover {
  transform: translateY(-5px);
}

.mode-icon {
  margin: 20px 0;
}

.mode-desc {
  color: var(--el-text-color-secondary);
  margin-bottom: 20px;
  min-height: 40px;
}

.mode-features {
  list-style: none;
  padding: 0;
  text-align: left;
  margin: 0 auto;
  display: inline-block;
}

.mode-features li {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
  color: var(--el-text-color-regular);
}

.feature-check {
  color: var(--el-color-success);
  margin-right: 8px;
}
</style>
