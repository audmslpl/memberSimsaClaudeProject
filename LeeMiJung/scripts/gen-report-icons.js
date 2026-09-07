#!/usr/bin/env node
/* =============================================================
 * 보고서 PPT용 아이콘 PNG 생성 스크립트
 *
 * 용도:
 *   react-icons(Lucide) 아이콘을 SVG로 렌더링한 뒤 sharp로 512px PNG로
 *   래스터화한다. python-pptx는 SVG를 넣을 수 없으므로 PNG가 필요하다.
 *
 * 사용법:
 *   npm install react react-dom react-icons sharp
 *   node scripts/gen-report-icons.js [출력디렉토리]
 *   (기본 출력: logs/report-icons/)
 *
 * 동작 흐름:
 *   1) ICONS 목록의 Lucide 컴포넌트를 renderToStaticMarkup으로 SVG 문자열화
 *   2) SVG의 currentColor를 팔레트 색상 리터럴로 치환 (librsvg가 currentColor를
 *      inline style에서 해석하지 못해 아이콘이 비어 보이는 문제 회피)
 *   3) sharp로 512x512 PNG 저장 → {아이콘}-{색상키}.png
 *
 * 변경이력:
 *   2026-08-20  최초 작성. 보고서 v2(모던 리디자인)용 아이콘 세트 생성.
 * ============================================================= */
const fs = require("fs");
const path = require("path");
const React = require("react");
const { renderToStaticMarkup } = require("react-dom/server");
const Lu = require("react-icons/lu");
const sharp = require("sharp");

const OUT = process.argv[2] || path.join(__dirname, "..", "logs", "report-icons");
const SIZE = 512;

// PPT 팔레트와 동일하게 유지할 것 (build-report-ppt-v2.py 의 색상표와 1:1 대응)
const COLORS = {
  amber: "#FFB020",
  teal: "#4ECDC4",
  rose: "#FF6B6B",
  green: "#3DDC84",
  violet: "#9B8CFF",
  white: "#F2F4F8",
  muted: "#8B93A8",
  ink: "#0A0E1A",
};

const ICONS = [
  "LuSend", "LuBot", "LuLayers", "LuClock", "LuActivity", "LuShieldCheck",
  "LuTrendingUp", "LuCloudSun", "LuPlane", "LuTerminal", "LuRefreshCw",
  "LuTriangleAlert", "LuCircleCheck", "LuRocket", "LuTarget", "LuKeyRound",
  "LuBoxes", "LuWorkflow", "LuArrowRightLeft", "LuServer", "LuDatabase",
  "LuZap", "LuBug", "LuLock", "LuCalendarClock", "LuMessageCircle",
  "LuChartCandlestick", "LuGauge", "LuPuzzle", "LuTimer", "LuCircleAlert",
  "LuLightbulb", "LuHeartPulse", "LuSettings", "LuFileCode", "LuUsers",
  "LuGitBranch", "LuCpu", "LuBellRing", "LuScanEye", "LuCalendarCheck",
  "LuListChecks", "LuFlag", "LuSparkles", "LuHardDrive", "LuNetwork",
  "LuMonitorSmartphone", "LuShieldAlert", "LuOctagonAlert",
];

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  let n = 0;
  for (const name of ICONS) {
    const Comp = Lu[name];
    if (!Comp) {
      console.warn("skip (not found):", name);
      continue;
    }
    const raw = renderToStaticMarkup(React.createElement(Comp, { size: SIZE }));
    for (const [key, hex] of Object.entries(COLORS)) {
      const svg = raw.replace(/currentColor/g, hex);
      const file = path.join(OUT, `${name}-${key}.png`);
      await sharp(Buffer.from(svg)).resize(SIZE, SIZE).png().toFile(file);
      n++;
    }
  }
  console.log(`saved ${n} png -> ${OUT}`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
