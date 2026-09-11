const { chromium } = require('playwright');

const TARGET_URL = 'http://localhost:5173';

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();

  // 设置桌面视口
  await page.setViewportSize({ width: 1400, height: 900 });

  console.log('导航到:', TARGET_URL);
  await page.goto(TARGET_URL, { waitUntil: 'networkidle', timeout: 15000 });

  // 等待 React 渲染
  await page.waitForTimeout(2000);

  // 获取页面标题
  console.log('页面标题:', await page.title());

  // 获取 #root 内容长度
  const rootContent = await page.locator('#root').innerHTML();
  console.log('#root 内容长度:', rootContent.length, '字符');

  // 截图
  await page.screenshot({ path: 'C:/Users/吴啸/AppData/Local/Temp/screenshot-ui.png', fullPage: true });
  console.log('截图保存到: C:/Users/吴啸/AppData/Local/Temp/screenshot-ui.png');

  // 获取一些元素的样式信息
  const sidebarBg = await page.locator('aside').evaluate(el => el.style.backgroundColor || getComputedStyle(el).backgroundColor);
  console.log('侧边栏背景色:', sidebarBg);

  const bodyBg = await page.locator('body').evaluate(el => getComputedStyle(el).backgroundColor);
  console.log('body 背景色:', bodyBg);

  await browser.close();
})();