(() => {
  "use strict";
  const el = id => document.getElementById(id);
  const video = el("video");
  const devices = el("devices");
  let stream = null;
  let active = false;
  let session = null;
  let maxBytes = 5 * 1024 * 1024;
  let request = 0;
  let busy = false;

  // Streamlit Components v1 wire protocol; no parent DOM access.
  function send(type, data = {}) {
    window.parent.postMessage({isStreamlitMessage: true, type, ...data}, "*");
  }
  function height() {
    send("streamlit:setFrameHeight", {height: active ? document.body.scrollHeight + 8 : 0});
  }
  function value(status, data) {
    send("streamlit:setComponentValue", {
      value: {session, status, ...(data ? {data} : {})}, dataType: "json",
    });
  }
  function status(text) {
    el("status").textContent = text;
    height();
  }
  function stop() {
    request += 1;
    if (stream) stream.getTracks().forEach(track => track.stop());
    stream = null;
    video.srcObject = null;
    video.hidden = true;
    el("capture").hidden = true;
    el("stop").hidden = true;
    el("devices-label").hidden = true;
    busy = false;
    el("start").disabled = false;
    devices.disabled = false;
    height();
  }
  function clearPhoto() {
    el("preview").removeAttribute("src");
    el("preview").hidden = true;
    el("clear").hidden = true;
  }
  function failure(error) {
    const messages = {
      NotAllowedError: "Permissão de câmera negada ou bloqueada. Libere a câmera nas permissões do site e do Android.",
      SecurityError: "A política do navegador bloqueou a câmera. Verifique HTTPS e permissões do site.",
      NotFoundError: "Nenhuma câmera disponível neste dispositivo.",
      NotReadableError: "Não foi possível abrir a câmera. Feche outros aplicativos que a estejam usando.",
      OverconstrainedError: "A câmera selecionada não está disponível. Tente abrir novamente.",
    };
    status((messages[error.name] || "Não foi possível usar a câmera neste navegador.") +
      " Tente novamente ou selecione 'Enviar arquivo'.");
  }
  async function listDevices(currentRequest) {
    devices.replaceChildren();
    if (!navigator.mediaDevices.enumerateDevices) return;
    try {
      const cameras = (await navigator.mediaDevices.enumerateDevices())
        .filter(device => device.kind === "videoinput");
      if (currentRequest !== request || !stream) return;
      const selected = stream.getVideoTracks()[0].getSettings?.().deviceId;
      cameras.forEach((device, index) => {
        const option = document.createElement("option");
        option.value = device.deviceId;
        option.textContent = device.label || `Câmera ${index + 1}`;
        option.selected = device.deviceId === selected;
        devices.appendChild(option);
      });
      el("devices-label").hidden = cameras.length < 2;
    } catch (_) {
      // Captura ainda funciona quando a enumeração é bloqueada.
    }
  }
  async function start(deviceId) {
    if (!active || busy) return;
    stop();
    clearPhoto();
    value("empty");
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      status("Câmera indisponível. Use HTTPS com certificado válido ou localhost no próprio dispositivo. " +
        "Verifique as permissões do navegador ou selecione 'Enviar arquivo'.");
      value("error");
      return;
    }
    const currentRequest = request;
    busy = true;
    el("start").disabled = true;
    devices.disabled = true;
    el("stop").hidden = false;
    status("Aguardando a câmera e a permissão do navegador…");
    try {
      const constraints = deviceId
        ? {deviceId: {exact: deviceId}}
        : {facingMode: {ideal: "environment"}};
      const opened = await navigator.mediaDevices.getUserMedia({audio: false, video: constraints});
      if (currentRequest !== request || !active) {
        opened.getTracks().forEach(track => track.stop());
        return;
      }
      stream = opened;
      video.srcObject = opened;
      video.hidden = false;
      await video.play();
      if (currentRequest !== request || !active) return;
      const track = stream.getVideoTracks()[0];
      track.addEventListener("ended", () => {
        if (stream === opened) {
          stop();
          status("A câmera foi desconectada. Tente novamente ou selecione 'Enviar arquivo'.");
        }
      });
      const facing = track.getSettings?.().facingMode;
      status(facing === "environment"
        ? "Câmera traseira informada pelo navegador. Confira o enquadramento e capture."
        : "Câmera traseira não confirmada pelo navegador. Confira a imagem; " +
          "se necessário, selecione outra câmera ou use 'Enviar arquivo'.");
      await listDevices(currentRequest);
      if (currentRequest !== request || !active) return;
      busy = false;
      devices.disabled = false;
      el("start").disabled = false;
      el("capture").hidden = false;
      height();
    } catch (error) {
      if (currentRequest !== request) return;
      stop();
      failure(error);
      value("error");
    }
  }
  el("start").addEventListener("click", () => start());
  devices.addEventListener("change", () => start(devices.value));
  el("capture").addEventListener("click", () => {
    if (!stream || !video.videoWidth || !video.videoHeight) {
      status("Aguarde a imagem da câmera antes de capturar.");
      return;
    }
    try {
      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      canvas.getContext("2d").drawImage(video, 0, 0);
      const data = canvas.toDataURL("image/jpeg", 0.92);
      if (!data.startsWith("data:image/jpeg;base64,") ||
          Math.floor((data.length - data.indexOf(",") - 1) * 3 / 4) > maxBytes) {
        stop();
        status("Foto excede 5 MiB ou não pôde ser processada. Use 'Enviar arquivo' com uma imagem menor.");
        value("error");
        return;
      }
      stop();
      el("preview").src = data;
      el("preview").hidden = false;
      el("clear").hidden = false;
      status("Foto capturada. Toque em 'Adicionar evidências à inspeção' para mantê-la na galeria e continuar capturando. Uma nova captura substitui apenas esta prévia pendente.");
      value("photo", data);
    } catch (_) {
      stop();
      status("Falha ao processar a captura. Tente novamente ou selecione 'Enviar arquivo'.");
      value("error");
    }
  });
  el("stop").addEventListener("click", () => {
    stop();
    status("Câmera desligada. Nenhuma nova foto capturada.");
  });
  el("clear").addEventListener("click", () => {
    stop();
    clearPhoto();
    status("Captura pendente descartada. As fotos já anexadas à inspeção foram mantidas.");
    value("empty");
  });
  window.addEventListener("message", event => {
    if (event.source !== window.parent || event.data?.type !== "streamlit:render") return;
    const args = event.data.args;
    if (args.session !== session || args.active !== active) {
      stop();
      clearPhoto();
      session = args.session;
      active = args.active;
      el("camera").hidden = !active;
      status(active ? "A câmera só será aberta ao tocar em 'Tirar foto com câmera traseira'." : "");
    }
    maxBytes = args.max_bytes;
    height();
  });
  window.addEventListener("pagehide", stop);
  window.addEventListener("beforeunload", stop);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      stop();
      status("Câmera desligada ao sair da tela. Toque no botão para reabrir.");
    }
  });
  video.addEventListener("loadedmetadata", height);
  el("preview").addEventListener("load", height);
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(height).observe(document.body);
  send("streamlit:componentReady", {apiVersion: 1});
})();
