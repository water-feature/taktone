/* End-to-end checks against local user-supplied firmware. Never uploads firmware. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {createHash} = require('node:crypto');
const {spawnSync} = require('node:child_process');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const firmware = path.join(root, 'taktone-core/firmware');
const base = process.env.PATCHER_URL || 'http://127.0.0.1:8765';
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'taktone-web-check-'));
const results = [];

(async () => {
  const browser = await chromium.launch({headless: true, ...(process.env.CHROMIUM_PATH ? {executablePath: process.env.CHROMIUM_PATH} : {})});
  try {
    const page = await browser.newPage();
    const errors = [], requests = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('request', r => requests.push({url:r.url(), method:r.method()}));
    await page.goto(base);
    assert.equal(await page.locator('#firmware-create').isDisabled(), true);
    const dt153 = path.join(firmware, 'Digitakt_OS1.53.syx');
    const dt154 = path.join(firmware, 'Digitakt_OS1.54.syx');
    const dn = path.join(firmware, 'Digitone_and_Digitone_Keys_OS1.43.syx');
    const select = async (input, reference) => {
      await page.locator('#firmware-file').setInputFiles(reference ? input : []);
      await page.locator('#reference-file').setInputFiles(reference || input);
      await page.locator('#digitone-file').setInputFiles(dn);
      await page.waitForFunction(() => !document.querySelector('#firmware-status').textContent.startsWith('Checking'));
    };
    const finish = async () => {
      await page.waitForFunction(() => document.querySelector('#firmware-cancel').hidden, {}, {timeout:900000});
      return page.locator('#firmware-status').textContent();
    };
    // Selection errors and stale-selection races.
    await page.locator('#reference-file').setInputFiles(dt153);
    await page.locator('#digitone-file').setInputFiles(dt153);
    await page.waitForFunction(() => document.querySelector('#firmware-status').textContent.startsWith('Cannot patch:'));
    assert.equal(await page.locator('#firmware-create').isDisabled(), true);
    await select(dt154);
    await page.waitForFunction(() => !document.querySelector('#firmware-create').disabled);
    await page.locator('#firmware-create').click();
    await page.locator('#firmware-cancel').click();
    assert.match(await page.locator('#firmware-status').textContent(), /cancelled/);
    assert.equal(await page.locator('#downloads a').count(), 0);
    assert.equal(await page.locator('#firmware-file').isEnabled(), true);
    results.push('Wrong stock reference rejected; cancellation clears downloads and restores controls.');
    const cases = [{name:'stock-1.53', input:dt153}, {name:'stock-1.54', input:dt154}];
    if (process.env.MOD_FILE) cases.push({name:'modified-1.53', input:path.resolve(process.env.MOD_FILE), reference:dt153});
    for (const item of cases) {
      console.log('Building desktop reference:', item.name);
      const out = path.join(temp, item.name);
      const args = [path.join(root, 'taktone-core/patch.py'), item.input, '--digitone', dn, '--out', out];
      if (item.reference) args.push('--digitakt', item.reference);
      const referenceBuild = spawnSync(process.env.PYTHON || 'python3', args, {cwd:root, encoding:'utf8', timeout:600000});
      assert.equal(referenceBuild.status, 0, referenceBuild.stdout + referenceBuild.stderr);
      const expected = JSON.parse(fs.readFileSync(path.join(out, 'conversion-report.json'))).output_sha256;
      await select(item.input, item.reference);
      await page.waitForFunction(() => !document.querySelector('#firmware-create').disabled);
      const start = Date.now();
      await page.locator('#firmware-create').click();
      assert.match(await finish(), /Both firmware files verified/);
      assert.equal(await page.locator('#downloads a').count(), 3);
      for (const anchor of await page.locator('#downloads a[download$=".syx"]').all()) {
        const name = await anchor.getAttribute('download');
        const downloadEvent = page.waitForEvent('download');
        await anchor.click();
        const download = await downloadEvent;
        const saved = path.join(temp, download.suggestedFilename());
        await download.saveAs(saved);
        assert.ok(Object.values(expected).includes(digest(fs.readFileSync(saved))), name + ' differs from desktop output');
      }
      const reportEvent = page.waitForEvent('download');
      await page.locator('#downloads a[download="conversion-report.json"]').click();
      const reportDownload = await reportEvent;
      const reportPath = path.join(temp, item.name + '-report.json');
      await reportDownload.saveAs(reportPath);
      const report = JSON.parse(fs.readFileSync(reportPath));
      assert.equal(report.status, 'candidate-built-hardware-untested');
      results.push(`${item.name}: both saved browser files match desktop SHA-256 (${Math.round((Date.now()-start)/1000)} seconds).`);
      await page.locator('#reference-file').setInputFiles([]);
      assert.equal(await page.locator('#downloads a').count(), 0);
    }
    await page.locator('#reference-file').setInputFiles(dn);
    await page.waitForFunction(() => document.querySelector('#firmware-status').textContent.startsWith('Cannot patch:'));
    assert.equal(await page.locator('#firmware-create').isDisabled(), true);
    results.push('Invalid factory Digitakt firmware rejected.');
    // Corrupt source ZIP must fail before unpacking or conversion.
    await page.route('**/core.zip', async route => {
      const response = await route.fetch();
      const bytes = Buffer.from(await response.body()); bytes[30] ^= 1;
      await route.fulfill({response, body:bytes});
    });
    await select(dt153);
    await page.waitForFunction(() => !document.querySelector('#firmware-create').disabled);
    await page.locator('#firmware-create').click();
    assert.match(await finish(), /Patcher source hash differs/);
    assert.equal(await page.locator('#downloads a').count(), 0);
    await page.unroute('**/core.zip');
    results.push('Corrupt source archive rejected before conversion.');
    await page.setViewportSize({width:375, height:812});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
    await page.screenshot({path:path.join(temp, 'mobile.png'), fullPage:true});
    assert.deepEqual(errors, []);
    assert.equal(requests.some(r => r.method !== 'GET' || (!r.url.startsWith('blob:') && new URL(r.url).origin !== new URL(base).origin)), false, 'Unexpected outbound request');
    results.push('375px layout has no horizontal overflow; no page errors or off-site/non-GET requests.');
    console.log(results.join('\n'));
    console.log('Local artifacts: ' + temp);
  } finally { await browser.close(); }
})().catch(error => {console.error(error);process.exitCode = 1;});
