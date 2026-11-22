'use strict';
// A fresh worker and RAM filesystem for every build. No firmware network requests.
self.onmessage = async ({data}) => {
  const progress = message => self.postMessage({progress: message});
  try {
    progress('Loading local patching engine…');
    importScripts('runtime/pyodide.js');
    const py = await loadPyodide({indexURL: 'runtime/', stdout: progress});
    const response = await fetch('core.zip');
    if (!response.ok) throw new Error('Could not load patcher sources. Reload and try again.');
    const archive = new Uint8Array(await response.arrayBuffer());
    const manifestResponse = await fetch('source-manifest.json');
    if (!manifestResponse.ok) throw new Error('Could not load source manifest.');
    const manifest = await manifestResponse.json();
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', archive))].map(b => b.toString(16).padStart(2, '0')).join('');
    if (hash !== manifest.core_sha256) throw new Error('Patcher source hash differs. Reload the page.');
    py.unpackArchive(archive, 'zip', {extractDir: '/app'});
    py.FS.mkdirTree('/work/input');
    py.FS.writeFile('/work/input.bin', new Uint8Array(data.input));
    py.FS.writeFile('/work/digitone.syx', new Uint8Array(data.digitone));
    if (data.reference) py.FS.writeFile('/work/reference.syx', new Uint8Array(data.reference));
    if (data.ram) py.FS.writeFile('/work/ram.json', new Uint8Array(data.ram));
    py.runPython("import sys\nsys.path.insert(0, '/app/core/internal')\nfrom browser_bridge import browser_build");
    progress('Checking compatibility, building and verifying both firmware files. This can take several minutes…');
    const build = py.globals.get('browser_build');
    let result;
    try { result = JSON.parse(build(data.name, Boolean(data.reference), Boolean(data.ram))); }
    finally { build.destroy(); }
    if (result.error) throw new Error(result.error);
    const outputs = result.files.map(file => ({...file, data: py.FS.readFile(file.path).slice().buffer}));
    self.postMessage({outputs, report: result.report}, outputs.map(file => file.data));
  } catch (error) {
    self.postMessage({error: String(error.message || error)});
  }
};
