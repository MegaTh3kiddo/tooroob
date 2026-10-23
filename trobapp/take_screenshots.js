const { chromium } = require('playwright');

async function capture() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  const viewports = [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'mobile', width: 390, height: 844 },
  ];

  const views = ['agent', 'list', 'map', 'inq'];

  for (const vp of viewports) {
    for (const v of views) {
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
      try {
        await page.goto(`http://127.0.0.1:8085/index.html#${v}`, { waitUntil: 'load' });
        await page.waitForTimeout(1000);
        await page.screenshot({ path: `/root/starcoach-hack/trobapp/audit-screenshots/static_${vp.name}_${v}.png` });
        console.log(`Captured static_${vp.name}_${v}.png`);
      } catch (err) {
        console.error(`Error capturing static_${vp.name}_${v}:`, err);
      } finally {
        await page.close();
      }
    }
  }

  await browser.close();
  console.log('All static screenshots captured!');
}

capture().catch((err) => {
  console.error(err);
  process.exit(1);
});
