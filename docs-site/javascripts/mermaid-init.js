// 初始化Mermaid图表
(function() {
  // 等待DOM加载完成
  function initMermaid() {
    console.log('Mermaid init started');

    // 检查mermaid是否已加载
    if (typeof mermaid === 'undefined') {
      console.warn('Mermaid library not loaded, retrying in 500ms');
      setTimeout(initMermaid, 500);
      return;
    }

    console.log('Mermaid library loaded, initializing...');

    // 初始化mermaid配置
    mermaid.initialize({
      theme: 'default',
      startOnLoad: false, // 我们手动初始化
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
      },
      sequence: {
        useMaxWidth: true,
        messageFontSize: 14,
        messageFontWeight: 'normal',
        noteFontSize: 14,
        actorFontSize: 14,
        actorFontWeight: 'bold',
      },
      er: {
        useMaxWidth: true,
      },
      pie: {
        useMaxWidth: true,
      },
      securityLevel: 'loose',
      fontFamily: '"Roboto", "Segoe UI", sans-serif',
    });

    // 查找所有可能的mermaid代码块
    // MkDocs Material将代码块渲染为: <div class="language-text highlight"><pre><code>...</code></pre></div>
    const codeContainers = document.querySelectorAll('div.language-text.highlight, div.language-mermaid.highlight');

    let mermaidCount = 0;
    console.log(`Found ${codeContainers.length} code containers to check`);

    codeContainers.forEach((container, index) => {
      console.log(`Checking container ${index}:`, container.className);
      // 获取code元素
      const codeElement = container.querySelector('code');
      if (!codeElement) {
        console.log(`Container ${index}: no code element found`);
        return;
      }

      // 获取所有文本内容（包括span内的文本）
      let content = '';
      const spans = codeElement.querySelectorAll('span');

      if (spans.length > 0) {
        // 如果有span元素，收集所有span的文本
        spans.forEach(span => {
          content += span.textContent + '\n';
        });
      } else {
        // 如果没有span，直接获取code的文本
        content = codeElement.textContent;
      }

      // 清理内容：移除多余的空行和空格
      content = content.trim();
      console.log(`Container ${index}: content preview: "${content.substring(0, 100)}..."`);

      // 检查是否是mermaid图表
      const isMermaid = content.includes('flowchart') ||
                       content.includes('graph TD') ||
                       content.includes('graph LR') ||
                       content.includes('sequenceDiagram') ||
                       content.includes('classDiagram') ||
                       content.includes('stateDiagram') ||
                       content.includes('erDiagram') ||
                       content.includes('pie');

      console.log(`Container ${index}: isMermaid = ${isMermaid}, includes sequenceDiagram = ${content.includes('sequenceDiagram')}`);

      if (isMermaid) {
        console.log(`Found mermaid diagram at container ${index}:`, content.substring(0, 100) + '...');

        // 创建新的mermaid div
        const mermaidDiv = document.createElement('div');
        mermaidDiv.className = 'mermaid';
        mermaidDiv.textContent = content;

        // 替换整个代码容器
        container.parentNode.replaceChild(mermaidDiv, container);

        mermaidCount++;
      }
    });

    // 如果有找到mermaid图表，进行渲染
    if (mermaidCount > 0) {
      console.log(`Found ${mermaidCount} mermaid diagrams, rendering...`);

      // 添加一些样式
      const style = document.createElement('style');
      style.textContent = `
        .mermaid {
          margin: 1.5em 0;
          text-align: center;
          background-color: transparent !important;
        }
        .mermaid svg {
          max-width: 100%;
          height: auto;
        }
        /* 强制所有文本为黑色，确保可读性 */
        .mermaid text,
        .mermaid .label text,
        .mermaid .messageText,
        .mermaid .actor,
        .mermaid .actor-man,
        .mermaid .actor-woman,
        .mermaid .actor text,
        .mermaid .label,
        .mermaid .node rect,
        .mermaid .node circle,
        .mermaid .node ellipse,
        .mermaid .node polygon,
        .mermaid .node path,
        .mermaid .node text,
        .mermaid .cluster rect,
        .mermaid .cluster text,
        .mermaid .edgeLabel text,
        .mermaid .edgePath path,
        .mermaid .marker,
        .mermaid .marker path,
        .mermaid .marker text {
          fill: #000000 !important;
          color: #000000 !important;
          stroke: #000000 !important;
        }
        /* 确保背景有足够对比度 */
        .mermaid .actor,
        .mermaid .actor-man,
        .mermaid .actor-woman,
        .mermaid .label rect,
        .mermaid .node rect,
        .mermaid .node circle,
        .mermaid .node ellipse,
        .mermaid .cluster rect {
          fill: #f0f0f0 !important;
          stroke: #333333 !important;
        }
      `;
      document.head.appendChild(style);

      // 渲染所有mermaid图表
      try {
        mermaid.init(undefined, '.mermaid');
        console.log('Mermaid diagrams rendered successfully');
      } catch (error) {
        console.error('Error rendering mermaid diagrams:', error);
      }
    } else {
      console.log('No mermaid diagrams found');
    }
  }

  // 启动初始化
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMermaid);
  } else {
    initMermaid();
  }
})();