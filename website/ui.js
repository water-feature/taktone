'use strict';
(() => {
  const byId = id => document.getElementById(id);
  const input = byId('firmware-file'), digitone = byId('digitone-file');
  const reference = byId('reference-file');
  const button = byId('firmware-create'), cancel = byId('firmware-cancel');
  const status = byId('firmware-status'), downloads = byId('downloads');
  const inputs = [input, digitone, reference];
  const stock = new Set(['9bdd44bb6102fb25c143cfab97bc92b7a89c463f795d3112dce89771e29bcc92',
    'f78ba80fa7b1da5fb0e1ff61ad61e9e71aafe79f4364fc49679f3651353e3cf6']);
  const dnHash = 'c5a54cc05b921f2e4bd814834c5365c2a5aa01d7772a9a2961fac1c3095bf9aa';
  let selected = null, worker = null, generation = 0, urls = [];
  const digest = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(b => b.toString(16).padStart(2, '0')).join('');
  function clear() {
    urls.forEach(url => URL.revokeObjectURL(url)); urls = [];
    downloads.replaceChildren();
  }
  function busy(value) {
    inputs.forEach(field => { field.disabled = value; });
    button.disabled = value || !selected;
    cancel.hidden = !value;
  }
  function stop() {
    if (worker) worker.terminate();
    worker = null; busy(false);
  }
  function link(content, name, label, type) {
    const url = URL.createObjectURL(new Blob([content], {type})); urls.push(url);
    const p = document.createElement('p'), a = document.createElement('a');
    a.href = url; a.download = name; a.textContent = label; p.append(a); downloads.append(p);
  }
  async function validate() {
    const current = ++generation;
    selected = null; button.disabled = true; clear();
    if (!reference.files[0] || !digitone.files[0]) {
      status.textContent = 'Select factory Digitakt and Digitone firmware, plus modified firmware if converting a mod.'; return;
    }
    status.textContent = 'Checking selected firmware hashes…';
    try {
      if (!crypto.subtle || typeof Worker === 'undefined') throw new Error('Use a current browser over HTTPS or localhost.');
      for (const field of inputs) {
        const file = field.files[0];
        if (file && (file.size > 16 * 1024 * 1024 || !file.size)) throw new Error('Firmware must be a nonempty .syx file smaller than 16 MB.');
      }
      const [modBytes, dnBytes, refBytes] = await Promise.all(inputs.map(field => field.files[0]?.arrayBuffer() ?? null));
      const [digitoneHash, referenceHash] = await Promise.all([digest(dnBytes), digest(refBytes)]);
      if (current !== generation) return;
      if (digitoneHash !== dnHash) throw new Error('Select the exact original Digitone OS 1.43 firmware.');
      if (!stock.has(referenceHash)) throw new Error('Select the exact factory Digitakt OS 1.53 or 1.54.');
      selected = {input: modBytes ?? refBytes, digitone: dnBytes, reference: refBytes, name: (input.files[0] ?? reference.files[0]).name};
      button.disabled = false;
      status.textContent = !modBytes ? 'Verified stock firmware. Ready to patch.' : 'Stock references verified. Ready to check modified firmware compatibility and patch.';
    } catch (error) {
      if (current === generation) status.textContent = 'Cannot patch: ' + error.message;
    }
  }
  inputs.forEach(field => field.addEventListener('change', validate));
  cancel.addEventListener('click', () => { ++generation; stop(); clear(); status.textContent = 'Build cancelled. No firmware was created.'; });
  button.addEventListener('click', () => {
    if (!selected || worker) return;
    clear(); busy(true);
    status.textContent = 'Starting local patcher…';
    const current = ++generation;
    try {
      worker = new Worker('worker.js');
      worker.onmessage = async ({data}) => {
        if (current !== generation) return;
        if (data.progress) { status.textContent = data.progress; return; }
        if (data.error) { clear(); stop(); status.textContent = 'Cannot create firmware: ' + data.error; return; }
        try {
          // Check transfer integrity before publishing either download.
          for (const file of data.outputs) {
            if (file.data.byteLength !== file.bytes || await digest(file.data) !== file.sha256) throw new Error('Output transfer hash differs.');
          }
          if (current !== generation) return;
          for (const file of data.outputs) {
            const recovery = file.name.endsWith('-recovery.syx');
            link(file.data, file.name, 'Download ' + file.name + (recovery ? ' (startup recovery / DIN MIDI)' : ' (running Digitakt-based firmware)'), 'application/octet-stream');
            const info = document.createElement('p');
            info.textContent = file.bytes.toLocaleString() + ' bytes · SHA-256: ' + file.sha256;
            info.className = 'hash'; downloads.append(info);
          }
          link(JSON.stringify(data.report, null, 2) + '\n', 'conversion-report.json', 'Download verification report', 'application/json');
          status.textContent = 'Both firmware files verified. Save the update, recovery file and report before installing.';
        } catch (error) { if (current === generation) { clear(); status.textContent = 'Cannot create firmware: ' + error.message; } }
        finally { if (current === generation) stop(); }
      };
      worker.onerror = () => { if (current === generation) { clear(); stop(); status.textContent = 'The patching engine failed to load or ran out of memory. Reload, try a desktop browser, or use the Python patcher.'; } };
      // Structured cloning leaves the selected buffers available for retry after cancellation.
      worker.postMessage(selected);
    } catch (error) { stop(); status.textContent = 'Cannot start patcher: ' + error.message; }
  });
  window.addEventListener('pagehide', () => { ++generation; clear(); stop(); });
})();
