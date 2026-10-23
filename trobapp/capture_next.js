const { chromium } = require('playwright');

async function captureNext() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  const viewports = [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'mobile', width: 390, height: 844 },
  ];

  const views = ['agent', 'list', 'map', 'inqs'];

  for (const vp of viewports) {
    for (const v of views) {
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
      try {
        await page.goto(`http://127.0.0.1:3000`, { waitUntil: 'load' });
        await page.waitForTimeout(600);

        // Click on the view tab
        const tab = await page.$(`button.view-tab:has-text("${v === 'agent' ? 'تربچت' : v === 'list' ? 'فهرست' : v === 'map' ? 'نقشه' : 'استعلام‌ها'}")`);
        if (tab) {
          await tab.click();
          await page.waitForTimeout(600);
        }

        await page.screenshot({ path: `/root/starcoach-hack/trobapp/audit-screenshots/next_before_${vp.name}_${v}.png` });
        console.log(`Captured next_before_${vp.name}_${v}.png`);
      } catch (err) {
        console.error(`Error capturing next_before_${vp.name}_${v}:`, err);
      } finally {
        await page.close();
      }
    }
  }

  await browser.close();
  console.log('All Next.js before screenshots captured!');
}

captureNext().catch((err) => {
  console.error(err);
  process.exit(1);
});
