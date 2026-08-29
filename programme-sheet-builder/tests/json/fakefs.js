/* In-memory FileSystemDirectoryHandle stand-in for the NSE Programme Sheet
   Builder's "Meeting files on disk" code. Speaks only the standard interface the
   app uses: getFileHandle / createWritable / write / close / getFile / entries /
   queryPermission / requestPermission / removeEntry.

   Injected with page.add_init_script so it exists before the app's own script
   runs, which also lets us force FS_SUPPORTED true or false. */
(function () {
  window.__FSLOG = [];
  function log(ev) { ev.t = performance.now(); window.__FSLOG.push(ev); return ev; }
  const sleep = ms => new Promise(r => setTimeout(r, ms));

  /* opts:
       perm            'granted' | 'denied' | 'prompt'      (queryPermission)
       requestPerm     'granted' | 'denied' | throw-string  (requestPermission)
       faults          { createWritable, write, close }  each: null | {name,message}
       latency         { createWritable, write, close, getFile } ms
       afterClose      (name, text) => text|null   rewrite/short/delete on commit
       gone            true  -> every op throws NotFoundError (folder deleted)
  */
  window.__mkFakeDir = function (opts) {
    opts = opts || {};
    const files = new Map();              /* name -> string */
    const st = {
      perm: opts.perm || 'granted',
      requestPerm: opts.requestPerm || 'granted',
      faults: Object.assign({}, opts.faults),
      latency: Object.assign({}, opts.latency),
      afterClose: opts.afterClose || null,
      gone: !!opts.gone,
      lock: !!opts.lock,
      open: new Set(),
      files: files,
    };

    function boom(spec) {
      const e = new Error(spec.message || 'fault');
      e.name = spec.name || 'Error';
      return e;
    }
    function checkGone() {
      if (st.gone) { const e = new Error('folder is gone'); e.name = 'NotFoundError'; throw e; }
    }

    function mkFileHandle(name) {
      return {
        kind: 'file',
        name: name,
        async getFile() {
          checkGone();
          if (st.latency.getFile) await sleep(st.latency.getFile);
          if (!files.has(name)) { const e = new Error('no file'); e.name = 'NotFoundError'; throw e; }
          return new File([files.get(name)], name, { type: 'application/json' });
        },
        async createWritable() {
          checkGone();
          log({ ev: 'createWritable', file: name });
          /* Chrome takes an exclusive lock per file entry; a second concurrent
             createWritable rejects. Toggle st.lock to model either behaviour. */
          if (st.lock && st.open.has(name)) {
            const e = new Error('file is locked'); e.name = 'NoModificationAllowedError';
            log({ ev: 'locked', file: name });
            throw e;
          }
          st.open.add(name);
          if (st.latency.createWritable) await sleep(st.latency.createWritable);
          if (st.faults.createWritable) { st.open.delete(name); throw boom(st.faults.createWritable); }
          let buf = '';
          let closed = false;
          return {
            async write(data) {
              checkGone();
              log({ ev: 'write', file: name, bytes: (typeof data === 'string' ? data.length : -1) });
              if (st.latency.write) await sleep(st.latency.write);
              if (st.faults.write) throw boom(st.faults.write);
              buf += (typeof data === 'string') ? data : String(data);
            },
            async truncate() { buf = ''; },
            async abort() { closed = true; st.open.delete(name); },
            async close() {
              checkGone();
              if (st.latency.close) await sleep(st.latency.close);
              st.open.delete(name);
              if (st.faults.close) throw boom(st.faults.close);
              closed = true;
              let out = buf;
              if (st.afterClose) out = st.afterClose(name, buf);
              if (out === null) { files.delete(name); }
              else { files.set(name, out); }
              log({ ev: 'close', file: name, bytes: out === null ? 0 : out.length,
                    marker: out ? markerOf(out) : null });
            },
          };
        },
      };
    }
    function markerOf(text) {
      /* the meeting title is our payload fingerprint in the ordering tests */
      const m = /"title":\s*"([^"]*)"/.exec(text);
      return m ? m[1] : null;
    }

    const dir = {
      kind: 'directory',
      name: 'meetings',
      async queryPermission() { checkGone(); return st.perm; },
      async requestPermission() {
        checkGone();
        if (typeof st.requestPerm === 'object' && st.requestPerm && st.requestPerm.throw) {
          throw boom(st.requestPerm);
        }
        st.perm = st.requestPerm === 'granted' ? 'granted' : st.perm;
        return st.requestPerm;
      },
      async getFileHandle(name, o) {
        checkGone();
        log({ ev: 'getFileHandle', file: name, create: !!(o && o.create) });
        if (st.latency.getFileHandle) await sleep(st.latency.getFileHandle);
        if (!files.has(name)) {
          if (!(o && o.create)) { const e = new Error('not found'); e.name = 'NotFoundError'; throw e; }
          files.set(name, '');
        }
        return mkFileHandle(name);
      },
      async removeEntry(name) { checkGone(); files.delete(name); },
      async *entries() {
        checkGone();
        for (const n of Array.from(files.keys())) yield [n, mkFileHandle(n)];
      },
      /* test-side controls, not part of the web interface */
      __st: st,
      __set(name, text) { files.set(name, text); },
      __get(name) { return files.has(name) ? files.get(name) : null; },
      __list() { return Array.from(files.keys()); },
      __handleFor(name) { return mkFileHandle(name); },
    };
    return dir;
  };
})();
