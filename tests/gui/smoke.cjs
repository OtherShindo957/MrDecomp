/* Run against a fresh local MrDecomp instance:
   MRDECOMP_TEST_URL='http://127.0.0.1:6464/?k=SECRET' node tests/gui/smoke.cjs
   Requires Playwright and Chromium. Never imports a commercial game or installs toolchains.
*/
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES
  ? require(path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES, 'playwright'))
  : require('playwright');
(async () => {
  assert(process.env.MRDECOMP_TEST_URL, 'Set MRDECOMP_TEST_URL to the authenticated local app URL');
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1280, height: 900}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(process.env.MRDECOMP_TEST_URL);
    await page.locator('#projectMode option').first().waitFor({state: 'attached'});
    assert.equal(await page.title(), 'MrDecomp');
    await page.selectOption('#projectMode', 'native');
    assert.match(await page.locator('#modeReason').innerText(), /runtime/);
    assert.equal(await page.locator('#drop').isVisible(), false);
    await page.selectOption('#projectMode', 'decompilation');
    assert.equal(await page.locator('#drop').isVisible(), true);
    await page.click('#systemCheck');
    await page.locator('#dialog:not([hidden])').waitFor();
    assert.match(await page.locator('#dialogBody').innerText(), /Python/);
    await page.keyboard.press('Escape');
    await page.click('#backendCheck');
    await page.locator('#dialog:not([hidden])').waitFor();
    assert.match(await page.locator('#dialogBody').innerText(), /RV32I/);
    await page.keyboard.press('Escape');
    const fixture = path.resolve(__dirname, '../../src/decompnet/app/static/demo/demo-quest-64.z64');
    assert(fs.existsSync(fixture));
    await page.setInputFiles('#file', fixture);
    await page.locator('#dropPicked:not([hidden])').waitFor();
    await page.check('#own');
    // Review performs read-only preflight; do not confirm an import or compiler install.
    if (await page.locator('#mwConsent').isVisible()) await page.check('#mwAccept');
    await page.click('#analyse');
    await page.locator('#confirmImport').waitFor();
    assert.match(await page.locator('#dialogTitle').innerText(), /Review/);
    await page.keyboard.press('Escape');
    await page.click('#recompLab');
    await page.locator('#rvRun').waitFor();
    await page.click('#rvRun');
    await page.waitForFunction(() => /a0 = 55/.test(document.getElementById('rvStatus')?.textContent || ''), null, {timeout: 45000});
    assert.equal(errors.length, 0, errors.join('\n'));
    console.log('PASS: modes, diagnostics, preflight and actual native recompilation through GUI');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
