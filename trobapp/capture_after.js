const { chromium } = require('playwright');

async function captureAfter() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
  });

  const viewports = [
    { name: 'desktop', width: 1440, height: 900 },
    { name: 'tablet', width: 768, height: 1024 },
    { name: 'mobile', width: 390, height: 844 },
  ];

  const views = [
    { key: 'agent', tabAttr: 'agent' },
    { key: 'list', tabAttr: 'list' },
    { key: 'map', tabAttr: 'map' },
    { key: 'inqs', tabAttr: 'inq' },
  ];

  for (const vp of viewports) {
    for (const v of views) {
      const page = await browser.newPage({ viewport: { width: vp.width, height: vp.height } });
      try {
        await page.goto(`http://127.0.0.1:3000`, { waitUntil: 'load' });
        await page.waitForTimeout(500);

        // Click on the view tab
        const tab = await page.$(`a.view-tab[data-view="${v.tabAttr}"]`);
        if (tab) {
          await tab.click();
          await page.waitForTimeout(v.key === 'map' ? 1800 : 800);
        }

        const outPath = `/root/starcoach-hack/trobapp/audit-screenshots/next_after_${vp.name}_${v.key}.png`;
        await page.screenshot({ path: outPath });
        console.log(`Captured ${outPath}`);
      } catch (err) {
        console.error(`Error capturing next_after_${vp.name}_${v.key}:`, err);
      } finally {
        await page.close();
      }
    }
  }

  // Also capture modals on desktop to verify reconstruction
  const modalsToTest = [
    { name: 'filter', trigger: '#filterBtn' },
    { name: 'account_profile', trigger: '#acctBtn', then: '[data-acct="profile"]' },
    { name: 'help', trigger: '#helpBtn' },
  ];

  for (const m of modalsToTest) {
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    try {
      await page.goto(`http://127.0.0.1:3000`, { waitUntil: 'load' });
      await page.waitForTimeout(500);

      // switch to list view for filter or help
      const listTab = await page.$('a.view-tab[data-view="list"]');
      if (listTab) await listTab.click();
      await page.waitForTimeout(400);

      const trig = await page.$(m.trigger);
      if (trig) {
        await trig.click();
        await page.waitForTimeout(400);
        if (m.then) {
          const sub = await page.$(m.then);
          if (sub) {
            await sub.click();
            await page.waitForTimeout(400);
          }
        }
        const outPath = `/root/starcoach-hack/trobapp/audit-screenshots/next_after_modal_${m.name}.png`;
        await page.screenshot({ path: outPath });
        console.log(`Captured modal ${outPath}`);
      }
    } catch (err) {
      console.error(`Error capturing modal ${m.name}:`, err);
    } finally {
      await page.close();
    }
  }

  await browser.close();
  console.log('All Next.js after screenshots captured!');
}

captureAfter().catch((err) => {
  console.error(err);
  process.exit(1);
});
