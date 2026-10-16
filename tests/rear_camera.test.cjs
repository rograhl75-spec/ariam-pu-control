const {test} = require("node:test");
const assert = require("node:assert/strict");
const {readFileSync} = require("node:fs");
const {join} = require("node:path");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "../ui/rear_camera/camera.js"), "utf8");
const settle = () => new Promise(resolve => setImmediate(resolve));

function setup({secure = true, media = true, getUserMedia} = {}) {
  const messages = [], calls = [], tracks = [], nodes = new Map();
  const listeners = {}, documentListeners = {};
  const element = () => ({
    hidden: true, disabled: false, value: "", children: [], handlers: {},
    videoWidth: 640, videoHeight: 480,
    addEventListener(type, callback) { this.handlers[type] = callback; },
    removeAttribute(name) { delete this[name]; },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    play: async () => {},
    getContext: () => ({drawImage() {}}),
    toDataURL: () => "data:image/jpeg;base64,aW1hZ2U=",
  });
  const document = {
    hidden: false, body: {scrollHeight: 450},
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, element());
      return nodes.get(id);
    },
    createElement: element,
    addEventListener(type, callback) { documentListeners[type] = callback; },
  };
  function newStream(facing = "environment", id = "back") {
    const track = {
      stopped: 0, stop() { this.stopped++; },
      getSettings: () => ({facingMode: facing, deviceId: id}),
      addEventListener(type, callback) { this[type] = callback; },
    };
    tracks.push(track);
    return {getTracks: () => [track], getVideoTracks: () => [track]};
  }
  const mediaDevices = {
    async getUserMedia(constraints) {
      calls.push(constraints);
      return getUserMedia ? getUserMedia(constraints, newStream) : newStream();
    },
    enumerateDevices: async () => [
      {kind: "videoinput", deviceId: "front", label: "Frontal"},
      {kind: "videoinput", deviceId: "back", label: "Traseira"},
    ],
  };
  const window = {
    isSecureContext: secure,
    parent: {postMessage(message) { messages.push(message); }},
    addEventListener(type, callback) { listeners[type] = callback; },
  };
  vm.runInNewContext(source, {
    window, document, navigator: {mediaDevices: media ? mediaDevices : undefined},
    ResizeObserver: class { observe() {} },
  });
  function render(active = true, session = 1) {
    listeners.message({source: window.parent, data: {
      type: "streamlit:render", args: {active, session, max_bytes: 5 * 1024 * 1024},
    }});
  }
  const values = () => messages.filter(message => message.type === "streamlit:setComponentValue");
  const click = id => nodes.get(id).handlers.click();
  render();
  return {nodes, messages, calls, tracks, listeners, documentListeners, document,
    render, values, click, mediaDevices, newStream};
}

test("camera opens only on explicit action, requests environment and sends captured bytes", async () => {
  const app = setup();
  assert.equal(app.calls.length, 0);
  app.click("start");
  await settle();
  assert.equal(app.calls[0].video.facingMode.ideal, "environment");
  assert.equal(app.calls[0].audio, false);
  assert.equal(app.nodes.get("devices").children.length, 2);
  assert.match(app.nodes.get("status").textContent, /traseira informada/);
  app.click("capture");
  const photo = app.values().at(-1).value;
  assert.equal(photo.status, "photo");
  assert.equal(photo.session, 1);
  assert.equal(photo.data, "data:image/jpeg;base64,aW1hZ2U=");
  assert.equal(app.tracks[0].stopped, 1);
  const count = app.values().length;
  app.render();
  assert.equal(app.values().length, count, "render must not create rerun loops");
  assert.equal(app.nodes.get("preview").hidden, false);
  app.click("clear");
  assert.equal(app.values().at(-1).value.status, "empty");
});

test("device change stops previous stream and requests selected device, without claiming rear camera", async () => {
  const app = setup({getUserMedia: async (_, stream) => stream("user", "front")});
  app.click("start");
  await settle();
  assert.match(app.nodes.get("status").textContent, /traseira não confirmada/);
  app.nodes.get("devices").value = "back";
  app.nodes.get("devices").handlers.change();
  await settle();
  assert.equal(app.tracks[0].stopped, 1);
  assert.equal(app.calls[1].video.deviceId.exact, "back");
  app.listeners.pagehide();
  assert.equal(app.tracks[1].stopped, 1);
});

test("adding a capture resets only the pending preview and allows another rear-camera photo", async () => {
  const app = setup();
  app.click("start");
  await settle();
  app.click("capture");
  assert.equal(app.values().at(-1).value.session, 1);
  app.render(true, 2);
  assert.equal(app.nodes.get("preview").hidden, true);
  assert.equal(app.calls.length, 1, "reset must not reopen camera automatically");
  app.click("start");
  await settle();
  app.click("capture");
  assert.equal(app.values().at(-1).value.session, 2);
  assert.equal(app.values().at(-1).value.status, "photo");
  assert.equal(app.calls[1].video.facingMode.ideal, "environment");
  assert.ok(app.tracks.every(track => track.stopped === 1));
});

test("source switch closes stream, clears preview and ignores late permission result", async () => {
  let resolve;
  const app = setup({getUserMedia: () => new Promise(done => { resolve = done; })});
  app.click("start");
  app.render(false, 2);
  const late = app.newStream();
  resolve(late);
  await settle();
  assert.equal(app.tracks[0].stopped, 1);
  assert.equal(app.nodes.get("video").srcObject, null);
  assert.equal(app.nodes.get("preview").hidden, true);
  app.render(true, 3);
  assert.equal(app.calls.length, 1, "reactivation must not start camera automatically");
});

test("cancel pending request and backgrounding release cameras", async () => {
  let resolve;
  const app = setup({getUserMedia: () => new Promise(done => { resolve = done; })});
  app.click("start");
  app.click("stop");
  resolve(app.newStream());
  await settle();
  assert.equal(app.tracks[0].stopped, 1);
  const running = setup();
  running.click("start");
  await settle();
  running.document.hidden = true;
  running.documentListeners.visibilitychange();
  assert.equal(running.tracks[0].stopped, 1);
});

for (const options of [{secure: false}, {media: false}]) {
  test(`unsupported context offers upload: ${JSON.stringify(options)}`, () => {
    const app = setup(options);
    app.click("start");
    assert.equal(app.calls.length, 0);
    assert.match(app.nodes.get("status").textContent, /HTTPS.*Enviar arquivo/);
    assert.equal(app.values().at(-1).value.status, "error");
  });
}

for (const name of ["NotAllowedError", "NotFoundError", "NotReadableError", "OverconstrainedError"]) {
  test(`camera failure ${name} has feedback and fallback`, async () => {
    const app = setup({getUserMedia: async () => { throw {name}; }});
    app.click("start");
    await settle();
    assert.match(app.nodes.get("status").textContent, /Enviar arquivo/);
    assert.equal(app.values().at(-1).value.status, "error");
    assert.equal(app.nodes.get("start").disabled, false);
  });
}

test("enumeration failure does not prevent capture; video failure releases stream", async () => {
  const app = setup();
  app.mediaDevices.enumerateDevices = async () => { throw new Error("unsupported"); };
  app.click("start");
  await settle();
  assert.equal(app.nodes.get("capture").hidden, false);
  app.click("capture");
  assert.equal(app.values().at(-1).value.status, "photo");
  const failed = setup();
  failed.nodes.get("video").play = async () => { throw new Error("play"); };
  failed.click("start");
  await settle();
  assert.equal(failed.tracks[0].stopped, 1);
  assert.equal(failed.values().at(-1).value.status, "error");
});
