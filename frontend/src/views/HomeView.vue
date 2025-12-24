<template>
  <div class="home-container">
    <!-- Hero Section -->
    <div class="hero-section">
      <div class="hero-bg-blobs">
        <div class="blob blob-1"></div>
        <div class="blob blob-2"></div>
      </div>
      <div class="hero-content">
        <div class="hero-badge">Open Source Online Judge</div>
        <h1 class="title">SKYOJ</h1>
        <p class="subtitle">一个开源的在线评测与知识共享平台</p>
        <div class="hero-actions">
          <el-button class="action-btn primary-btn" round size="large" type="primary"
                     @click="$router.push('/problems')">
            开始编程
            <el-icon class="el-icon--right">
              <ArrowRight/>
            </el-icon>
          </el-button>
          <el-button class="action-btn" round size="large" @click="scrollToAbout">
            了解更多
          </el-button>
        </div>
      </div>
    </div>

    <!-- Stats Section -->
    <div class="stats-container">
      <div class="stat-item">
        <div class="stat-value">100+</div>
        <div class="stat-label">精选题目</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">4</div>
        <div class="stat-label">主流语言</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">3</div>
        <div class="stat-label">评测模式</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">AI</div>
        <div class="stat-label">辅助出题</div>
      </div>
    </div>

    <!-- About Section -->
    <div id="about-section" class="section-container">
      <div class="section-header">
        <h2 class="section-title">关于 SKYOJ</h2>
        <p class="section-subtitle">现代化、开源、易用的在线评测系统</p>
      </div>
      <el-row :gutter="60" align="middle">
        <el-col :md="12" :xs="24">
          <div class="about-content">
            <p class="about-text">
              SKYOJ 是一个专为学生、教育工作者和编程爱好者设计的现代化开源在线评测系统（Online Judge）。
              它提供了一个强大的平台，用于练习算法、举办比赛以及分享编程知识。
            </p>
            <p class="about-text">
              我们的使命是通过提供易于访问的工具和资源来普及计算机科学教育。
              无论您是学习 Python 的初学者，还是解决复杂图论问题的专家，SKYOJ 都能为您的学习之旅提供支持。
            </p>
            <div class="features-grid">
              <div class="feature-card">
                <el-icon class="feature-icon">
                  <Timer/>
                </el-icon>
                <span>实时代码评测</span>
              </div>
              <div class="feature-card">
                <el-icon class="feature-icon">
                  <Monitor/>
                </el-icon>
                <span>多语言支持</span>
              </div>
              <div class="feature-card">
                <el-icon class="feature-icon">
                  <DataAnalysis/>
                </el-icon>
                <span>Kaggle 模式</span>
              </div>
              <div class="feature-card">
                <el-icon class="feature-icon">
                  <MagicStick/>
                </el-icon>
                <span>AI 辅助教学</span>
              </div>
            </div>
          </div>
        </el-col>
        <el-col :md="12" :xs="24">
          <div class="about-visual">
            <div class="code-window">
              <div class="window-header">
                <span class="dot red"></span>
                <span class="dot yellow"></span>
                <span class="dot green"></span>
              </div>
              <div class="window-content">
                <pre><code><span class="keyword">def</span> <span class="function">solve</span>():
    <span class="comment"># Welcome to SKYOJ</span>
    print(<span class="string">"Hello, SKYOJ!"</span>)

<span class="keyword">if</span> __name__ == <span class="string">"__main__"</span>:
    solve()</code></pre>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- Documentation / Modes Section -->
    <div id="docs-section" class="section-container dark-section">
      <div class="section-header">
        <h2 class="section-title">评测模式介绍</h2>
        <p class="section-subtitle">针对不同教学场景设计的专业评测模式</p>
      </div>
      <el-row :gutter="30">
        <el-col v-for="mode in modes" :key="mode.title" :md="8" :xs="24" class="mb-4">
          <div class="mode-card-new" @click="$router.push(mode.route)">
            <div :style="{ backgroundColor: mode.color + '15', color: mode.color }" class="mode-icon-wrapper">
              <el-icon :size="32">
                <component :is="mode.icon"/>
              </el-icon>
            </div>
            <h3>{{ mode.title }}</h3>
            <p class="mode-desc">{{ mode.description }}</p>
            <div class="mode-footer">
              <span class="learn-more">了解详情 <el-icon><ArrowRight/></el-icon></span>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>

    <!-- External Resources Section -->
    <div class="section-container">
      <div class="section-header">
        <h2 class="section-title">开源知识资源</h2>
        <p class="section-subtitle">连接全球最优秀的开发者社区与文档</p>
      </div>
      <div class="resources-grid">
        <div v-for="resource in resources" :key="resource.name" class="resource-item" @click="openLink(resource.url)">
          <div :style="{ color: resource.color }" class="resource-icon-box">
            <el-icon :size="28">
              <component :is="resource.icon"/>
            </el-icon>
          </div>
          <div class="resource-info">
            <h4>{{ resource.name }}</h4>
            <p>{{ resource.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ArrowRight, DataAnalysis, MagicStick, Monitor, Timer} from '@element-plus/icons-vue'

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
  document.getElementById('about-section')?.scrollIntoView({behavior: 'smooth'})
}

const openLink = (url) => {
  window.open(url, '_blank')
}
</script>

<style scoped>
.home-container {
  overflow-x: hidden;
}

/* Hero Section */
.hero-section {
  position: relative;
  background: #fff;
  padding: 120px 20px;
  text-align: center;
  margin-bottom: 40px;
  overflow: hidden;
}

.hero-bg-blobs {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  filter: blur(80px);
  opacity: 0.4;
}

.blob {
  position: absolute;
  border-radius: 50%;
}

.blob-1 {
  width: 400px;
  height: 400px;
  background: var(--el-color-primary-light-5);
  top: -100px;
  right: -100px;
}

.blob-2 {
  width: 300px;
  height: 300px;
  background: var(--el-color-success-light-5);
  bottom: -50px;
  left: -50px;
}

.hero-content {
  position: relative;
  z-index: 1;
  max-width: 800px;
  margin: 0 auto;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-radius: 20px;
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 24px;
  border: 1px solid var(--el-color-primary-light-7);
}

.title {
  font-size: 4.5rem;
  font-weight: 800;
  color: #1a1a1a;
  margin: 0 0 20px;
  letter-spacing: -2px;
  line-height: 1;
}

.subtitle {
  font-size: 1.4rem;
  color: #666;
  margin: 0 0 48px;
  font-weight: 400;
}

.hero-actions {
  display: flex;
  gap: 16px;
  justify-content: center;
}

.action-btn {
  padding: 12px 32px;
  font-weight: 600;
  transition: all 0.3s;
}

.primary-btn {
  box-shadow: 0 4px 14px 0 rgba(64, 158, 255, 0.39);
}

.primary-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(64, 158, 255, 0.23);
}

/* Stats Section */
.stats-container {
  display: flex;
  justify-content: center;
  gap: 80px;
  padding: 40px 20px;
  background: #fff;
  border-bottom: 1px solid #f0f0f0;
  margin-bottom: 80px;
}

.stat-item {
  text-align: center;
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 800;
  color: #1a1a1a;
  line-height: 1.2;
}

.stat-label {
  font-size: 0.9rem;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Section Common */
.section-container {
  max-width: 1200px;
  margin: 0 auto 120px;
  padding: 0 20px;
}

.section-header {
  text-align: center;
  margin-bottom: 60px;
}

.section-title {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1a1a1a;
  margin-bottom: 12px;
}

.section-subtitle {
  font-size: 1.1rem;
  color: #888;
}

/* About Section */
.about-content {
  padding-right: 20px;
}

.about-text {
  font-size: 1.15rem;
  line-height: 1.8;
  color: #444;
  margin-bottom: 24px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-top: 40px;
}

.feature-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #f9f9f9;
  border-radius: 12px;
  font-weight: 600;
  color: #333;
}

.feature-icon {
  color: var(--el-color-primary);
  font-size: 1.4rem;
}

.about-visual {
  perspective: 1000px;
}

.code-window {
  background: #1e1e1e;
  border-radius: 12px;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.2);
  overflow: hidden;
  transform: rotateY(-10deg) rotateX(5deg);
  transition: transform 0.5s;
}

.code-window:hover {
  transform: rotateY(0deg) rotateX(0deg);
}

.window-header {
  background: #333;
  padding: 12px 16px;
  display: flex;
  gap: 8px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.red {
  background: #ff5f56;
}

.yellow {
  background: #ffbd2e;
}

.green {
  background: #27c93f;
}

.window-content {
  padding: 24px;
  font-family: 'Fira Code', monospace;
  font-size: 1rem;
}

.window-content pre {
  margin: 0;
}

.keyword {
  color: #c678dd;
}

.function {
  color: #61afef;
}

.string {
  color: #98c379;
}

.comment {
  color: #5c6370;
  font-style: italic;
}

/* Mode Cards */
.mode-card-new {
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 20px;
  padding: 40px 32px;
  height: 100%;
  transition: all 0.3s;
  cursor: pointer;
  display: flex;
  flex-direction: column;
}

.mode-card-new:hover {
  border-color: var(--el-color-primary-light-5);
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.05);
  transform: translateY(-5px);
}

.mode-icon-wrapper {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 24px;
}

.mode-card-new h3 {
  font-size: 1.5rem;
  margin-bottom: 16px;
  color: #1a1a1a;
}

.mode-desc {
  color: #666;
  line-height: 1.6;
  margin-bottom: 24px;
  flex-grow: 1;
}

.mode-footer {
  padding-top: 20px;
  border-top: 1px solid #f5f5f5;
}

.learn-more {
  color: var(--el-color-primary);
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
}

/* Resources Grid */
.resources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.resource-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.resource-item:hover {
  background: #f9f9f9;
  border-color: #ddd;
  transform: scale(1.02);
}

.resource-icon-box {
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.resource-info h4 {
  margin: 0 0 4px;
  font-size: 1.1rem;
  color: #1a1a1a;
}

.resource-info p {
  margin: 0;
  font-size: 0.9rem;
  color: #888;
  line-height: 1.4;
}

@media (max-width: 768px) {
  .title {
    font-size: 3rem;
  }

  .stats-container {
    gap: 30px;
    flex-wrap: wrap;
  }

  .hero-section {
    padding: 80px 20px;
  }

  .features-grid {
    grid-template-columns: 1fr;
  }

  .about-visual {
    margin-top: 40px;
  }
}
</style>
