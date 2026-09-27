"use strict";
const $ = id => document.getElementById(id);
const text = $("transcript"), record = $("recordBtn");
let ready = false, recording = false, acquiring = false, backlog = 0, chain = Promise.resolve();
let stream, context, source, processor, mute, analyser, timerId, frameId;
let samples = [], sampleCount = 0, silenceSamples = 0, startTime = 0, activeLanguage = "fa";
let fault = false, closing = false;
const bars = Array.from({length: 35}, () => { const bar = document.createElement("i"); $("wave").append(bar); return bar; });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
function notice(message, error = false) { $("notice").textContent = message; $("notice").classList.toggle("error", error); }
function updateText() {
  const value = text.value.trim();
  $("emptyState").hidden = !!value;
  $("wordCount").textContent = (value ? value.split(/\s+/u).length : 0).toLocaleString("fa-IR") + " کلمه";
  $("copyBtn").disabled = $("downloadBtn").disabled = !value;
}
function controls() {
  const busy = recording || acquiring || backlog > 0 || closing;
  record.disabled = acquiring || closing || (!recording && (!ready || backlog > 0));
  $("uploadBtn").disabled = !ready || busy;
  $("language").disabled = busy;
  $("clearBtn").disabled = busy || !text.value;
  text.readOnly = busy;
  record.classList.toggle("recording", recording);
  $("orb").classList.toggle("recording", recording);
  $("recordIcon").textContent = recording ? "■" : "●";
  $("recordLabel").textContent = recording ? "پایان ضبط" : acquiring ? "در انتظار میکروفون…" : closing ? "پایان ضبط…" : backlog ? "در حال نوشتن…" : ready ? "شروع صحبت" : "در حال آماده‌سازی مدل…";
  $("liveBadge").textContent = recording ? "● در حال شنیدن" : backlog ? "در حال پردازش" : "آمادهٔ شنیدن";
  $("liveBadge").classList.toggle("active", busy);
  updateText();
}
async function checkModel() {
  try {
    const response = await fetch("/api/status");
    if (!response.ok) throw Error("ارتباط با برنامه برقرار نشد.");
    const status = await response.json();
    ready = status.status === "ready";
    $("statusDot").className = "status-dot " + (ready ? "ready" : status.status === "error" ? "error" : "");
    $("modelStatus").textContent = ready ? "مدل محلی آماده است · CPU / int8" : status.status === "error" ? "بارگذاری مدل ناموفق بود" : "ویسپر در حال بارگذاری است";
    if (status.status === "error") notice("خطای مدل: " + status.error, true);
    else if (ready) notice("آماده‌ایم. برای ضبط، اجازهٔ دسترسی به میکروفون را در مرورگر بده. متن هر چند ثانیه به‌روز می‌شود.");
    controls();
    if (status.status === "loading") setTimeout(checkModel, 1500);
  } catch (error) {
    ready = false; controls();
    notice("ارتباط با برنامه قطع است. پنجرهٔ اجرای پایتون را باز نگه دار؛ اتصال دوباره بررسی می‌شود.", true);
    setTimeout(checkModel, 3000);
  }
}
function wav(chunks, count, rate) {
  const buffer = new ArrayBuffer(44 + count * 2), view = new DataView(buffer);
  const ascii = (offset, value) => { for (let i = 0; i < value.length; i++) view.setUint8(offset + i, value.charCodeAt(i)); };
  ascii(0, "RIFF"); view.setUint32(4, 36 + count * 2, true); ascii(8, "WAVE"); ascii(12, "fmt ");
  view.setUint32(16, 16, true); view.setUint16(20, 1, true); view.setUint16(22, 1, true);
  view.setUint32(24, rate, true); view.setUint32(28, rate * 2, true); view.setUint16(32, 2, true); view.setUint16(34, 16, true);
  ascii(36, "data"); view.setUint32(40, count * 2, true);
  let offset = 44;
  for (const chunk of chunks) for (const value of chunk) { const sample = Math.max(-1, Math.min(1, value)); view.setInt16(offset, Math.round(sample * (sample < 0 ? 32768 : 32767)), true); offset += 2; }
  return new Blob([buffer], {type: "audio/wav"});
}
function submit(blob, language) {
  backlog++; controls();
  chain = chain.then(async () => {
    const base = text.value;
    let latest = "";
    try {
      const response = await fetch("/api/transcribe", {method: "POST", headers: {"Content-Type": "application/octet-stream", "X-Language": language}, body: blob});
      const submitted = await response.json();
      if (!response.ok) throw Error(submitted.error || "دریافت صدا ناموفق بود.");
      while (true) {
        const result = await fetch("/api/jobs/" + submitted.id);
        const job = await result.json();
        if (!result.ok) throw Error(job.error || "نتیجه پیدا نشد.");
        if (latest !== job.text) {
          latest = job.text;
          text.value = base + (base.trim() && latest ? "\n" : "") + latest;
          text.scrollTop = text.scrollHeight; updateText();
        }
        if (job.status === "error") throw Error(job.error);
        if (job.status === "done") {
          if (!recording && backlog === 1 && !fault) notice(latest ? "متن آماده است. می‌توانی آن را ویرایش، کپی یا ذخیره کنی." : "گفتاری در این صدا تشخیص داده نشد. میکروفون و بلندی صدا را بررسی کن.");
          break;
        }
        await delay(900);
      }
    } catch (error) {
      fault = true;
      notice("تبدیل صدا ناموفق بود: " + error.message, true);
      if (recording) await stopRecording();
    } finally { backlog--; controls(); }
  });
}
function flush() {
  if (!sampleCount || !context) return;
  const blob = wav(samples, sampleCount, context.sampleRate);
  samples = []; sampleCount = 0; silenceSamples = 0;
  submit(blob, activeLanguage);
}
function animate() {
  if (!recording) return;
  const levels = new Uint8Array(analyser.frequencyBinCount); analyser.getByteFrequencyData(levels);
  bars.forEach((bar, i) => { bar.style.height = (4 + (levels[i * 3] || 0) / 255 * 24) + "px"; bar.style.background = "#b4f0d1"; });
  frameId = requestAnimationFrame(animate);
}
async function startRecording() {
  acquiring = true; fault = false; controls();
  try {
    if (!navigator.mediaDevices?.getUserMedia) throw Error("مرورگر از ضبط پشتیبانی نمی‌کند. برنامه را با Chrome یا Edge در آدرس محلی باز کن.");
    stream = await navigator.mediaDevices.getUserMedia({audio: {channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true}});
    context = new AudioContext(); await context.resume();
    source = context.createMediaStreamSource(stream);
    // PCM avoids codec differences and does not require an external ffmpeg executable.
    processor = context.createScriptProcessor(4096, 1, 1);
    mute = context.createGain(); mute.gain.value = 0;
    analyser = context.createAnalyser(); analyser.fftSize = 256;
    source.connect(analyser); source.connect(processor); processor.connect(mute); mute.connect(context.destination);
    samples = []; sampleCount = 0; silenceSamples = 0;
    activeLanguage = $("language").value;
    recording = true; startTime = Date.now();
    processor.onaudioprocess = event => {
      if (!recording) return;
      const chunk = new Float32Array(event.inputBuffer.getChannelData(0));
      samples.push(chunk); sampleCount += chunk.length;
      let energy = 0; for (const value of chunk) energy += value * value;
      silenceSamples = Math.sqrt(energy / chunk.length) < .012 ? silenceSamples + chunk.length : 0;
      // Prefer pauses to avoid cutting words; continuous speech is split at 22 seconds.
      if ((sampleCount > context.sampleRate * 8 && silenceSamples > context.sampleRate * .7) || sampleCount > context.sampleRate * 22) {
        flush();
        if (backlog >= 3) { notice("پردازش از ضبط عقب افتاده؛ ضبط متوقف شد تا متن بخش‌های دریافت‌شده کامل شود."); stopRecording(); }
      }
    };
    stream.getAudioTracks()[0].onended = () => { if (recording) { notice("ارتباط میکروفون قطع شد؛ صدای دریافت‌شده پردازش می‌شود.", true); stopRecording(); } };
    timerId = setInterval(() => { const seconds = Math.floor((Date.now() - startTime) / 1000); $("timer").textContent = String(Math.floor(seconds / 60)).padStart(2,"0") + ":" + String(seconds % 60).padStart(2,"0"); }, 250);
    $("modeChip").textContent = "میکروفون";
    $("recordHint").textContent = "صدایت را می‌شنوم؛ راحت صحبت کن";
    notice("ضبط روشن است. متن در مکث‌های گفتار یا حداکثر هر ۲۲ ثانیه برای پردازش فرستاده می‌شود. با «پایان ضبط» بخش آخر هم نوشته می‌شود.");
    animate();
  } catch (error) {
    stream?.getTracks().forEach(track => track.stop());
    if (context && context.state !== "closed") await context.close();
    recording = false;
    notice(error.name === "NotAllowedError" ? "اجازهٔ میکروفون داده نشد. از علامت کنار آدرس مرورگر، دسترسی میکروفون را فعال کن." : error.name === "NotFoundError" ? "میکروفون پیدا نشد. اتصال میکروفون را بررسی کن." : error.message, true);
  } finally { acquiring = false; controls(); }
}
async function stopRecording() {
  if (!recording) return;
  recording = false; closing = true; controls();
  clearInterval(timerId); cancelAnimationFrame(frameId);
  processor.onaudioprocess = null;
  source.disconnect(); processor.disconnect(); mute.disconnect();
  stream.getTracks().forEach(track => { track.onended = null; track.stop(); });
  flush();
  try { await context.close(); } finally { context = null; closing = false; controls(); }
  bars.forEach(bar => { bar.style.height = "5px"; bar.style.background = ""; });
  $("recordHint").textContent = "ضبط پایان یافت؛ میکروفون خاموش است";
  if (!fault) notice("ضبط تمام شد. در حال تکمیل متن بخش‌های باقی‌مانده…");
}
record.addEventListener("click", () => recording ? stopRecording() : startRecording());
$("uploadBtn").addEventListener("click", () => $("fileInput").click());
$("fileInput").addEventListener("change", event => {
  const file = event.target.files[0]; event.target.value = "";
  if (!file) return;
  if (file.size > 100 * 1024 * 1024 || !file.size) return notice("یک فایل صوتی غیرخالی با اندازهٔ حداکثر ۱۰۰ مگابایت انتخاب کن.", true);
  if (recording || backlog || acquiring || closing || !ready) return;
  fault = false; $("modeChip").textContent = "فایل صوتی";
  notice("در حال تبدیل «" + file.name + "». پردازش فایل بلند روی CPU ممکن است چند دقیقه طول بکشد.");
  submit(file, $("language").value);
});
text.addEventListener("input", () => { updateText(); $("clearBtn").disabled = !text.value; });
$("clearBtn").addEventListener("click", () => { text.value = ""; controls(); notice("متن پاک شد. آمادهٔ یک شروع تازه‌ایم."); });
$("copyBtn").addEventListener("click", async () => { try { await navigator.clipboard.writeText(text.value); notice("متن کپی شد."); } catch { notice("کپی خودکار ممکن نشد؛ متن را انتخاب کن و Ctrl+C بزن.", true); } });
$("downloadBtn").addEventListener("click", () => {
  const url = URL.createObjectURL(new Blob(["\ufeff", text.value], {type: "text/plain;charset=utf-8"}));
  const anchor = document.createElement("a"); anchor.href = url; anchor.download = "transcript-" + new Date().toISOString().slice(0,19).replaceAll(":","-") + ".txt";
  anchor.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  notice("فایل متن ذخیره شد.");
});
window.addEventListener("beforeunload", event => { if (recording || backlog || text.value.trim()) { event.preventDefault(); event.returnValue = ""; } });
controls(); checkModel();
