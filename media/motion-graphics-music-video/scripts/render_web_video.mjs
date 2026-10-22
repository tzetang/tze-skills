#!/usr/bin/env node
/**
 * Deterministic Headless Chrome Frame-by-Frame Video Renderer (Zero NPM Dependencies).
 *
 * Serves the workspace over a local HTTP server, launches Google Chrome with
 * Chrome DevTools Protocol (CDP), calls `window.seekToFrame(frameIndex, timeSeconds)`
 * for every frame at 30fps, captures screenshots, and pipes them directly into FFmpeg
 * along with the source audio track to produce `final/music-video.mp4` (H.264 yuv420p + AAC).
 *
 * Usage:
 *   node render_web_video.mjs --html src/index.html --audio song/passage.mp3 --out final/music-video.mp4
 */

import { spawn, execFileSync } from "node:child_process";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

function parseArgs(argv) {
  const args = {
    html: "src/index.html",
    audio: "song/passage.mp3",
    out: "final/music-video.mp4",
    width: 1920,
    height: 1080,
    fps: 30,
    duration: null,
    root: process.cwd(),
  };
  for (let i = 2; i < argv.length; i++) {
    const k = argv[i];
    const v = argv[i + 1];
    if (k === "--html") { args.html = v; i++; }
    else if (k === "--audio") { args.audio = v; i++; }
    else if (k === "--out") { args.out = v; i++; }
    else if (k === "--width") { args.width = parseInt(v, 10); i++; }
    else if (k === "--height") { args.height = parseInt(v, 10); i++; }
    else if (k === "--fps") { args.fps = parseInt(v, 10); i++; }
    else if (k === "--duration") { args.duration = parseFloat(v); i++; }
    else if (k === "--root") { args.root = path.resolve(v); i++; }
  }
  return args;
}

function getAudioDuration(audioPath) {
  const out = execFileSync("ffprobe", [
    "-v", "error",
    "-show_entries", "format=duration",
    "-of", "default=noprint_wrappers=1:nokey=1",
    audioPath,
  ], { encoding: "utf-8" });
  return parseFloat(out.trim());
}

function findChromeBinary() {
  const candidates = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "chromium",
  ];
  for (const c of candidates) {
    if (c.startsWith("/") && fs.existsSync(c)) return c;
  }
  return candidates[0];
}

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".mp3": "audio/mpeg",
  ".ttf": "font/ttf",
  ".otf": "font/otf",
  ".woff2": "font/woff2",
};

function startStaticServer(rootDir) {
  return new Promise((resolve) => {
    const server = http.createServer((req, res) => {
      const cleanUrl = decodeURIComponent((req.url || "/").split("?")[0]);
      const filePath = path.join(rootDir, cleanUrl);
      if (!filePath.startsWith(rootDir) || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        res.writeHead(404);
        res.end("Not Found");
        return;
      }
      const ext = path.extname(filePath).toLowerCase();
      res.writeHead(200, { "Content-Type": MIME_TYPES[ext] || "application/octet-stream" });
      fs.createReadStream(filePath).pipe(res);
    });
    server.listen(0, "127.0.0.1", () => {
      resolve({ server, port: server.address().port });
    });
  });
}

class CDPClient {
  constructor(wsUrl) {
    this.ws = new WebSocket(wsUrl);
    this.nextId = 1;
    this.pending = new Map();
  }
  async connect() {
    await new Promise((resolve, reject) => {
      this.ws.addEventListener("open", resolve, { once: true });
      this.ws.addEventListener("error", reject, { once: true });
    });
    this.ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      }
    });
  }
  send(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }
  close() {
    this.ws.close();
  }
}

async function main() {
  const args = parseArgs(process.argv);
  const audioAbs = path.resolve(args.root, args.audio);
  const outAbs = path.resolve(args.root, args.out);
  fs.mkdirSync(path.dirname(outAbs), { recursive: true });

  const duration = args.duration ?? getAudioDuration(audioAbs);
  const totalFrames = Math.round(duration * args.fps);
  console.log(`Rendering ${totalFrames} frames (${duration.toFixed(3)}s @ ${args.fps}fps, ${args.width}x${args.height}) -> ${outAbs}`);

  const { server, port } = await startStaticServer(args.root);
  const relHtml = path.relative(args.root, path.resolve(args.root, args.html)).replace(/\\/g, "/");
  const targetUrl = `http://127.0.0.1:${port}/${relHtml}`;

  const chromeBin = findChromeBinary();
  const userDataDir = fs.mkdtempSync("/tmp/chrome-mv-render-");
  const chromeProc = spawn(chromeBin, [
    "--headless=new",
    "--remote-debugging-port=0",
    `--user-data-dir=${userDataDir}`,
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-gpu-vsync",
    "--enable-webgl",
    "--ignore-gpu-blocklist",
    "--hide-scrollbars",
    "--mute-audio",
    `--window-size=${args.width},${args.height}`,
    "about:blank",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const wsBrowserUrl = await new Promise((resolve, reject) => {
    let stderrBuf = "";
    chromeProc.stderr.on("data", (chunk) => {
      stderrBuf += chunk.toString();
      const m = stderrBuf.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (m) resolve(m[1]);
    });
    chromeProc.on("exit", (code) => reject(new Error(`Chrome exited early (${code}): ${stderrBuf}`)));
  });

  const debugPort = new URL(wsBrowserUrl).port;
  const targets = await fetch(`http://127.0.0.1:${debugPort}/json/list`).then((r) => r.json());
  const pageTarget = targets.find((t) => t.type === "page");
  const cdp = new CDPClient(pageTarget.webSocketDebuggerUrl);
  await cdp.connect();

  await cdp.send("Page.enable");
  await cdp.send("Runtime.enable");
  await cdp.send("Emulation.setDeviceMetricsOverride", {
    width: args.width,
    height: args.height,
    deviceScaleFactor: 1,
    mobile: false,
  });

  await cdp.send("Page.navigate", { url: targetUrl });
  // Wait for page readiness & optional window.initScene()
  await cdp.send("Runtime.evaluate", {
    expression: `new Promise((resolve) => {
      const check = async () => {
        if (document.readyState === 'complete') {
          if (typeof window.initScene === 'function') await window.initScene();
          resolve(true);
        } else {
          setTimeout(check, 50);
        }
      };
      check();
    })`,
    awaitPromise: true,
  });

  // Spawn FFmpeg to encode piped JPEG frames + original audio
  const ffmpegArgs = [
    "-y",
    "-f", "image2pipe",
    "-vcodec", "mjpeg",
    "-r", String(args.fps),
    "-i", "-",
    "-i", audioAbs,
    "-map", "0:v:0",
    "-map", "1:a:0",
    "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p",
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-color_range", "tv",
    "-r", String(args.fps),
    "-c:a", "aac",
    "-b:a", "192k",
    "-t", duration.toFixed(3),
    outAbs,
  ];
  const ffmpegProc = spawn("ffmpeg", ffmpegArgs, { stdio: ["pipe", "ignore", "pipe"] });
  let ffmpegStderr = "";
  ffmpegProc.stderr.on("data", (d) => { ffmpegStderr += d.toString(); });

  const startTime = Date.now();
  for (let frame = 0; frame < totalFrames; frame++) {
    const timeSec = frame / args.fps;
    await cdp.send("Runtime.evaluate", {
      expression: `window.seekToFrame(${frame}, ${timeSec.toFixed(6)})`,
      awaitPromise: true,
    });
    const shot = await cdp.send("Page.captureScreenshot", {
      format: "jpeg",
      quality: 94,
      optimizeForSpeed: true,
    });
    const buf = Buffer.from(shot.data, "base64");
    const canContinue = ffmpegProc.stdin.write(buf);
    if (!canContinue) {
      await new Promise((r) => ffmpegProc.stdin.once("drain", r));
    }
    if ((frame + 1) % 60 === 0 || frame + 1 === totalFrames) {
      const elapsed = (Date.now() - startTime) / 1000;
      const rate = (frame + 1) / elapsed;
      console.log(`  Frame ${frame + 1}/${totalFrames} (${((frame + 1) / totalFrames * 100).toFixed(1)}%) - ${rate.toFixed(1)} fps`);
    }
  }

  ffmpegProc.stdin.end();
  await new Promise((resolve, reject) => {
    ffmpegProc.on("close", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`FFmpeg failed with code ${code}:\n${ffmpegStderr.slice(-1000)}`));
    });
  });

  cdp.close();
  chromeProc.kill("SIGKILL");
  server.close();
  fs.rmSync(userDataDir, { recursive: true, force: true });
  console.log(`Finished rendering ${outAbs}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
