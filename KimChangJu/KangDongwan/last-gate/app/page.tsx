"use client";

import {
  useRef,
  useState,
  type MouseEvent as ReactMouseEvent,
  type PointerEvent as ReactPointerEvent,
} from "react";

type Phase = "intro" | "map" | "event" | "battle" | "reward" | "victory" | "defeat";
type CardType = "attack" | "skill";
type CardRarity = "basic" | "common" | "rare";
type CardStrategy = "basic" | "bleed" | "guard" | "focus";
type OathId = "blood" | "iron" | "ember";
type MapNodeKind = "start" | "battle" | "event" | "rest" | "boss";
type MapEventEffect = "heal" | "max-hp" | "common-card" | "rare-card";
type IntentKind = "attack" | "guard" | "buff" | "drain" | "multi" | "counter";
type EffectKind = "enemy-hit" | "player-hit" | "shield" | "heal" | "buff" | "focus";
type EffectVariant = "slash" | "ward" | "crush" | "twin-slash" | "quick-slash" | "blood-blade" | "iron-wall" | "riposte" | "rally" | "last-stand" | "reap" | "brace" | "meditate";

type Player = {
  hp: number;
  maxHp: number;
  block: number;
  focus: number;
};

type Enemy = {
  name: string;
  title: string;
  hp: number;
  maxHp: number;
  attackMin: number;
  attackMax: number;
  art: string;
  description: string;
  tone: string;
  vulnerable: number;
  bleed: number;
  block: number;
  strength: number;
  phase: 1 | 2;
};

type OathDefinition = {
  id: OathId;
  name: string;
  subtitle: string;
  glyph: string;
  art: string;
  passive: string;
  starter: string;
  tone: string;
};

type EnemyIntent = {
  kind: IntentKind;
  amount: number;
  label: string;
  icon: string;
  note: string;
  hits: number;
  heavy: boolean;
};

type BattleEffect = {
  id: string;
  kind: EffectKind;
  target: "enemy" | "player";
  variant?: EffectVariant;
  text: string;
};

type CardDefinition = {
  id: string;
  name: string;
  type: CardType;
  rarity: CardRarity;
  cost: number;
  glyph: string;
  art: string;
  effect: EffectVariant;
  strategy: CardStrategy;
  description: string;
  damage?: number;
  hits?: number;
  block?: number;
  draw?: number;
  heal?: number;
  energy?: number;
  vulnerable?: number;
  focus?: number;
  bleed?: number;
  bleedScale?: number;
  blockScale?: number;
  consumeBleed?: boolean;
  missingScale?: boolean;
};

type CardInstance = {
  uid: string;
  cardId: string;
};

type LogEntry = {
  id: string;
  text: string;
  tone: "normal" | "good" | "danger";
};

type ExpeditionNode = {
  id: string;
  kind: MapNodeKind;
  label: string;
  encounter?: number;
  depth: number;
  column: number;
  links: string[];
};

type MapEventChoice = {
  id: string;
  label: string;
  description: string;
  effect: MapEventEffect;
  amount?: number;
  cost?: number;
};

type MapEventDefinition = {
  id: string;
  title: string;
  subtitle: string;
  glyph: string;
  description: string;
  tone: "spring" | "gold" | "sky" | "camp";
  choices: MapEventChoice[];
};

const ENCOUNTERS: Omit<Enemy, "hp" | "vulnerable" | "bleed" | "block" | "strength" | "phase">[] = [
  {
    name: "햇살 들개",
    title: "들판의 장난꾸러기",
    maxHp: 32,
    attackMin: 6,
    attackMax: 8,
    art: "/enemies/sunlit-hound-cute.png",
    description: "풀잎 사이로 꼬리를 흔들며 이빨을 드러낸다.",
    tone: "ash",
  },
  {
    name: "숲길 정찰병",
    title: "고목 숲의 파수꾼",
    maxHp: 44,
    attackMin: 8,
    attackMax: 10,
    art: "/enemies/forest-path-scout-cute.png",
    description: "나뭇잎 사이에서 청동 창끝이 반짝인다.",
    tone: "moss",
  },
  {
    name: "이끼 갑옷 기사",
    title: "오래된 회랑의 수호자",
    maxHp: 56,
    attackMin: 9,
    attackMax: 12,
    art: "/enemies/moss-armored-knight-cute.png",
    description: "갑옷 틈의 어린 덩굴이 바람에 흔들린다.",
    tone: "plague",
  },
  {
    name: "쌍두 감시자",
    title: "노을 성소의 감시자",
    maxHp: 72,
    attackMin: 11,
    attackMax: 14,
    art: "/enemies/twin-watcher-cute.png",
    description: "두 개의 눈동자가 황금빛으로 번뜩인다.",
    tone: "blood",
  },
  {
    name: "태양문의 수호자",
    title: "SUN GATE WARDEN",
    maxHp: 105,
    attackMin: 13,
    attackMax: 17,
    art: "/enemies/sun-gate-warden-cute.png",
    description: "태양석의 빛이 거대한 검 위로 흐른다.",
    tone: "boss",
  },
];

const EXPEDITION_MAP: ExpeditionNode[] = [
  { id: "start", kind: "start", label: "여정 시작", depth: 0, column: 1, links: ["field-west", "field-east"] },
  { id: "field-west", kind: "battle", label: "들꽃 비탈", encounter: 0, depth: 1, column: 0, links: ["forest-west", "forest-center"] },
  { id: "field-east", kind: "battle", label: "바람 언덕", encounter: 0, depth: 1, column: 2, links: ["forest-center", "forest-east"] },
  { id: "forest-west", kind: "battle", label: "고목 샛길", encounter: 1, depth: 2, column: 0, links: ["ruin-west", "ruin-center"] },
  { id: "forest-center", kind: "battle", label: "햇살 길목", encounter: 1, depth: 2, column: 1, links: ["ruin-west", "ruin-center", "ruin-east"] },
  { id: "forest-east", kind: "battle", label: "돌담 오솔길", encounter: 1, depth: 2, column: 2, links: ["ruin-center", "ruin-east"] },
  { id: "ruin-west", kind: "battle", label: "이끼 회랑", encounter: 2, depth: 3, column: 0, links: ["sanctum-west"] },
  { id: "ruin-center", kind: "battle", label: "오래된 정원", encounter: 2, depth: 3, column: 1, links: ["sanctum-west", "sanctum-east"] },
  { id: "ruin-east", kind: "battle", label: "푸른 폐허", encounter: 2, depth: 3, column: 2, links: ["sanctum-east"] },
  { id: "sanctum-west", kind: "battle", label: "노을 성소", encounter: 3, depth: 4, column: 0, links: ["sun-gate"] },
  { id: "sanctum-east", kind: "battle", label: "쌍둥이 탑", encounter: 3, depth: 4, column: 2, links: ["sun-gate"] },
  { id: "sun-gate", kind: "boss", label: "태양의 관문", encounter: 4, depth: 5, column: 1, links: [] },
];

const INITIAL_MAP_NODE_KINDS = Object.fromEntries(
  EXPEDITION_MAP.map((node) => [node.id, node.kind]),
) as Record<string, MapNodeKind>;

const MAP_EVENTS: MapEventDefinition[] = [
  {
    id: "sunwell",
    title: "노래하는 햇살샘",
    subtitle: "A WARM DISCOVERY",
    glyph: "◌",
    description: "꽃잎 사이에서 맑은 샘물이 작은 종소리를 냅니다. 손을 담그자 지친 몸에 온기가 번집니다.",
    tone: "sky",
    choices: [
      { id: "drink", label: "샘물을 마신다", description: "체력을 14 회복합니다.", effect: "heal", amount: 14 },
      { id: "blessing", label: "빛을 품는다", description: "최대 체력과 현재 체력이 4 증가합니다.", effect: "max-hp", amount: 4 },
    ],
  },
  {
    id: "seed",
    title: "검을 품은 씨앗",
    subtitle: "A CURIOUS BARGAIN",
    glyph: "✦",
    description: "반짝이는 씨앗이 모험가의 손바닥에서 싹을 틔웁니다. 작은 잎맥마다 낯선 검술이 흐릅니다.",
    tone: "spring",
    choices: [
      { id: "nurture", label: "온기를 나눈다", description: "체력 6을 지불하고 희귀 카드 1장을 얻습니다.", effect: "rare-card", cost: 6 },
      { id: "release", label: "바람에 놓아준다", description: "씨앗의 축복으로 체력을 8 회복합니다.", effect: "heal", amount: 8 },
    ],
  },
  {
    id: "satchel",
    title: "구름여우의 보따리",
    subtitle: "A PLAYFUL ENCOUNTER",
    glyph: "♢",
    description: "꼬리가 구름처럼 부푼 여우가 길을 막고 보따리를 내밉니다. 안에서는 카드들이 사각거립니다.",
    tone: "gold",
    choices: [
      { id: "trade", label: "보따리를 고른다", description: "무작위 일반 카드 1장을 얻습니다.", effect: "common-card" },
      { id: "snack", label: "간식을 나눠 먹는다", description: "체력을 8 회복합니다.", effect: "heal", amount: 8 },
    ],
  },
];

const REST_EVENT: MapEventDefinition = {
  id: "rest",
  title: "민들레 야영지",
  subtitle: "A QUIET MOMENT",
  glyph: "☼",
  description: "따뜻한 바람이 부는 작은 야영지입니다. 잠시 쉬거나 다음 여정을 위해 몸을 단련할 수 있습니다.",
  tone: "camp",
  choices: [
    { id: "rest", label: "푹 쉬어간다", description: "체력을 16 회복합니다.", effect: "heal", amount: 16 },
    { id: "train", label: "가볍게 단련한다", description: "최대 체력과 현재 체력이 3 증가합니다.", effect: "max-hp", amount: 3 },
  ],
};

const MAP_COLUMN_X = [18, 50, 82];
const MAP_DEPTH_Y = [91, 74, 57, 40, 23, 6];
const MAP_ASPECT_RATIO = 5 / 4;
const MAP_CONNECTIONS = EXPEDITION_MAP.flatMap((node) =>
  node.links.map((targetId) => ({ sourceId: node.id, targetId })),
);

const getMapNode = (nodeId: string) =>
  EXPEDITION_MAP.find((node) => node.id === nodeId);

const getMapPosition = (node: ExpeditionNode) => ({
  x: MAP_COLUMN_X[node.column],
  y: MAP_DEPTH_Y[node.depth],
});

const getMapConnectionStyle = (source: ExpeditionNode, target: ExpeditionNode) => {
  const from = getMapPosition(source);
  const to = getMapPosition(target);
  const deltaX = to.x - from.x;
  const deltaY = (to.y - from.y) / MAP_ASPECT_RATIO;
  return {
    left: `${from.x}%`,
    top: `${from.y}%`,
    width: `${Math.hypot(deltaX, deltaY)}%`,
    transform: `rotate(${Math.atan2(deltaY, deltaX) * 180 / Math.PI}deg)`,
  };
};

const CARD_LIBRARY: Record<string, CardDefinition> = {
  strike: {
    id: "strike",
    name: "타격",
    type: "attack",
    rarity: "basic",
    cost: 1,
    glyph: "╱",
    art: "/cards/strike.png",
    effect: "slash",
    strategy: "basic",
    description: "적에게 피해 6.",
    damage: 6,
  },
  defend: {
    id: "defend",
    name: "방어",
    type: "skill",
    rarity: "basic",
    cost: 1,
    glyph: "◇",
    art: "/cards/defend.png",
    effect: "ward",
    strategy: "guard",
    description: "방어도 5. 집중 1 획득.",
    block: 5,
    focus: 1,
  },
  bash: {
    id: "bash",
    name: "강타",
    type: "attack",
    rarity: "basic",
    cost: 2,
    glyph: "✦",
    art: "/cards/bash.png",
    effect: "crush",
    strategy: "focus",
    description: "피해 9. 취약 2 부여.",
    damage: 9,
    vulnerable: 2,
  },
  twinSlash: {
    id: "twinSlash",
    name: "쌍검 베기",
    type: "attack",
    rarity: "common",
    cost: 1,
    glyph: "╳",
    art: "/cards/twin-slash.png",
    effect: "twin-slash",
    strategy: "bleed",
    description: "피해 3을 2회. 적 출혈 1당 총 피해 +2.",
    damage: 3,
    hits: 2,
    bleedScale: 2,
  },
  quickSlash: {
    id: "quickSlash",
    name: "찰나의 검격",
    type: "attack",
    rarity: "common",
    cost: 1,
    glyph: "⌁",
    art: "/cards/quick-slash.png",
    effect: "quick-slash",
    strategy: "focus",
    description: "피해 5. 카드 1장 뽑기.",
    damage: 5,
    draw: 1,
  },
  bloodBlade: {
    id: "bloodBlade",
    name: "장미 칼날",
    type: "attack",
    rarity: "common",
    cost: 1,
    glyph: "⌄",
    art: "/cards/rose-blade.png",
    effect: "blood-blade",
    strategy: "bleed",
    description: "피해 4. 출혈 2 부여. 체력 2 회복.",
    damage: 4,
    bleed: 2,
    heal: 2,
  },
  ironWall: {
    id: "ironWall",
    name: "철벽",
    type: "skill",
    rarity: "common",
    cost: 2,
    glyph: "▣",
    art: "/cards/iron-wall.png",
    effect: "iron-wall",
    strategy: "guard",
    description: "방어도 14. 집중 1 획득.",
    block: 14,
    focus: 1,
  },
  counter: {
    id: "counter",
    name: "맞받아치기",
    type: "attack",
    rarity: "common",
    cost: 1,
    glyph: "↯",
    art: "/cards/counter.png",
    effect: "riposte",
    strategy: "guard",
    description: "피해 3 + 현재 방어도. 방어도 4 획득.",
    damage: 3,
    block: 4,
    blockScale: 1,
  },
  rally: {
    id: "rally",
    name: "불씨 되찾기",
    type: "skill",
    rarity: "rare",
    cost: 0,
    glyph: "☼",
    art: "/cards/rally.png",
    effect: "rally",
    strategy: "focus",
    description: "에너지 1. 카드 1장. 집중 1.",
    energy: 1,
    draw: 1,
    focus: 1,
  },
  lastStand: {
    id: "lastStand",
    name: "최후의 일격",
    type: "attack",
    rarity: "rare",
    cost: 2,
    glyph: "†",
    art: "/cards/last-stand.png",
    effect: "last-stand",
    strategy: "focus",
    description: "피해 8. 잃은 체력 8당 피해 +2.",
    damage: 8,
    missingScale: true,
  },
  reap: {
    id: "reap",
    name: "영혼 수확",
    type: "attack",
    rarity: "rare",
    cost: 2,
    glyph: "☾",
    art: "/cards/reap.png",
    effect: "reap",
    strategy: "bleed",
    description: "피해 8. 출혈 1당 +3 후 제거. 체력 5 회복.",
    damage: 8,
    heal: 5,
    bleedScale: 3,
    consumeBleed: true,
  },
  brace: {
    id: "brace",
    name: "이를 악물기",
    type: "skill",
    rarity: "common",
    cost: 0,
    glyph: "◈",
    art: "/cards/brace.png",
    effect: "brace",
    strategy: "guard",
    description: "방어도 3. 집중 1 획득.",
    block: 3,
    focus: 1,
  },
  meditate: {
    id: "meditate",
    name: "검의 호흡",
    type: "skill",
    rarity: "rare",
    cost: 1,
    glyph: "◎",
    art: "/cards/meditate.png",
    effect: "meditate",
    strategy: "focus",
    description: "집중 2. 카드 1장 뽑기.",
    focus: 2,
    draw: 1,
  },
};

const STRATEGY_LABELS: Record<CardStrategy, string> = {
  basic: "기본",
  bleed: "출혈 연계",
  guard: "방어 반격",
  focus: "집중 폭발",
};

const STRATEGY_CARD_IDS: Record<Exclude<CardStrategy, "basic">, string[]> = {
  bleed: ["twinSlash", "bloodBlade", "reap"],
  guard: ["ironWall", "counter", "brace"],
  focus: ["quickSlash", "rally", "lastStand", "meditate"],
};

const OATHS: Record<OathId, OathDefinition> = {
  blood: {
    id: "blood",
    name: "장미의 서약",
    subtitle: "출혈 연계",
    glyph: "⌄",
    art: "/oaths/rose-oath.png",
    passive: "출혈 카드가 출혈을 1 더 부여합니다.",
    starter: "장미 칼날 · 쌍검 베기",
    tone: "blood",
  },
  iron: {
    id: "iron",
    name: "수호의 서약",
    subtitle: "방어 반격",
    glyph: "▣",
    art: "/oaths/guardian-oath.png",
    passive: "매 전투 시작 시 방어도 6을 얻습니다.",
    starter: "이를 악물기 · 맞받아치기",
    tone: "iron",
  },
  ember: {
    id: "ember",
    name: "햇살의 서약",
    subtitle: "집중 폭발",
    glyph: "☼",
    art: "/oaths/sunlight-oath.png",
    passive: "매 턴 처음 사용한 스킬이 집중 1을 더 줍니다.",
    starter: "찰나의 검격 · 검의 호흡",
    tone: "ember",
  },
};

const INITIAL_PLAYER: Player = {
  hp: 80,
  maxHp: 80,
  block: 0,
  focus: 0,
};

const INITIAL_DECK: CardInstance[] = [
  ...Array.from({ length: 5 }, (_, index) => ({ uid: `strike-${index + 1}`, cardId: "strike" })),
  ...Array.from({ length: 4 }, (_, index) => ({ uid: `defend-${index + 1}`, cardId: "defend" })),
  { uid: "bash-1", cardId: "bash" },
];

const STARTER_DECK_IDS: Record<OathId, string[]> = {
  blood: ["strike", "strike", "strike", "strike", "defend", "defend", "defend", "bash", "bloodBlade", "twinSlash"],
  iron: ["strike", "strike", "strike", "strike", "defend", "defend", "defend", "bash", "brace", "counter"],
  ember: ["strike", "strike", "strike", "strike", "defend", "defend", "defend", "bash", "quickSlash", "meditate"],
};

let cardSequence = 0;

const makeEnemy = (index: number): Enemy => ({
  ...ENCOUNTERS[index],
  hp: ENCOUNTERS[index].maxHp,
  vulnerable: 0,
  bleed: 0,
  block: 0,
  strength: 0,
  phase: 1,
});

const makeStartingDeck = (oath: OathId): CardInstance[] =>
  STARTER_DECK_IDS[oath].map((cardId, index) => ({
    uid: `${oath}-${cardId}-${index}-${Date.now()}`,
    cardId,
  }));

const makeCard = (cardId: string): CardInstance => ({
  uid: `${cardId}-${Date.now()}-${++cardSequence}`,
  cardId,
});

const makeLog = (
  text: string,
  tone: LogEntry["tone"] = "normal",
): LogEntry => ({
  id: `${Date.now()}-${Math.random()}`,
  text,
  tone,
});

const shuffle = <T,>(items: T[]): T[] => {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const target = Math.floor(Math.random() * (index + 1));
    [result[index], result[target]] = [result[target], result[index]];
  }
  return result;
};

const createRandomMapNodeKinds = (): Record<string, MapNodeKind> => {
  const nextKinds = { ...INITIAL_MAP_NODE_KINDS };
  const forestSides = shuffle<MapNodeKind>(["event", "rest"]);
  const ruinSides = shuffle<MapNodeKind>(["event", "rest"]);
  const sanctumKinds = shuffle<MapNodeKind>([
    "battle",
    Math.random() < 0.5 ? "event" : "rest",
  ]);

  nextKinds["forest-west"] = forestSides[0];
  nextKinds["forest-center"] = "battle";
  nextKinds["forest-east"] = forestSides[1];
  nextKinds["ruin-west"] = ruinSides[0];
  nextKinds["ruin-center"] = "battle";
  nextKinds["ruin-east"] = ruinSides[1];
  nextKinds["sanctum-west"] = sanctumKinds[0];
  nextKinds["sanctum-east"] = sanctumKinds[1];

  return nextKinds;
};

const COMMON_EVENT_CARD_IDS = [
  "twinSlash",
  "quickSlash",
  "bloodBlade",
  "ironWall",
  "counter",
  "brace",
];

const RARE_EVENT_CARD_IDS = ["rally", "lastStand", "reap", "meditate"];

const drawCards = (
  count: number,
  currentDraw: CardInstance[],
  currentDiscard: CardInstance[],
) => {
  let nextDraw = [...currentDraw];
  let nextDiscard = [...currentDiscard];
  const drawn: CardInstance[] = [];

  for (let index = 0; index < count; index += 1) {
    if (nextDraw.length === 0 && nextDiscard.length > 0) {
      nextDraw = shuffle(nextDiscard);
      nextDiscard = [];
    }
    const card = nextDraw.pop();
    if (!card) break;
    drawn.push(card);
  }

  return { drawn, drawPile: nextDraw, discardPile: nextDiscard };
};

const BASE_ENERGY = 3;
const HAND_SIZE = 5;
const MAX_ENERGY_CARRY = 1;
const RETAIN_COST = 1;
const HAND_DRAG_THRESHOLD = 5;
const HAND_MOMENTUM_MS = 220;
const HAND_MAX_FLING_DISTANCE = 320;

const prepareHand = (runDeck: CardInstance[]) =>
  drawCards(HAND_SIZE, shuffle(runDeck), []);

const INTENT_PATTERNS: EnemyIntent[][] = [
  [
    { kind: "attack", amount: 7, label: "물어뜯기", icon: "↓", note: "단일 공격", hits: 1, heavy: false },
    { kind: "attack", amount: 7, label: "할퀴기", icon: "↓", note: "단일 공격", hits: 1, heavy: false },
    { kind: "attack", amount: 11, label: "달려들기", icon: "⚠", note: "강력한 공격", hits: 1, heavy: true },
  ],
  [
    { kind: "attack", amount: 9, label: "창 찌르기", icon: "↓", note: "단일 공격", hits: 1, heavy: false },
    { kind: "counter", amount: 3, label: "가시 방패", icon: "↯", note: "공격 카드마다 3 반격", hits: 1, heavy: false },
    { kind: "attack", amount: 12, label: "돌진", icon: "⚠", note: "강력한 공격", hits: 1, heavy: true },
  ],
  [
    { kind: "drain", amount: 8, label: "생명 흡수", icon: "☾", note: "공격 후 회복", hits: 1, heavy: false },
    { kind: "attack", amount: 11, label: "녹슨 대검", icon: "↓", note: "단일 공격", hits: 1, heavy: false },
    { kind: "buff", amount: 2, label: "이끼의 힘", icon: "↑", note: "공격력 영구 증가", hits: 1, heavy: false },
    { kind: "counter", amount: 4, label: "덩굴 반사", icon: "↯", note: "공격 카드마다 4 반격", hits: 1, heavy: false },
  ],
  [
    { kind: "multi", amount: 6, label: "쌍두 난타", icon: "⇊", note: "2회 공격", hits: 2, heavy: false },
    { kind: "counter", amount: 5, label: "두 겹의 응수", icon: "↯", note: "공격 카드마다 5 반격", hits: 1, heavy: false },
    { kind: "guard", amount: 10, label: "교차 방어", icon: "◇", note: "방어도 획득", hits: 1, heavy: false },
    { kind: "attack", amount: 15, label: "심판", icon: "⚠", note: "강력한 공격", hits: 1, heavy: true },
  ],
  [
    { kind: "attack", amount: 15, label: "태양의 검", icon: "↓", note: "단일 공격", hits: 1, heavy: false },
    { kind: "counter", amount: 6, label: "빛의 응수", icon: "↯", note: "공격 카드마다 6 반격", hits: 1, heavy: false },
    { kind: "guard", amount: 12, label: "석문", icon: "◇", note: "방어도 획득", hits: 1, heavy: false },
    { kind: "buff", amount: 3, label: "수호자의 결의", icon: "↑", note: "공격력 영구 증가", hits: 1, heavy: false },
    { kind: "multi", amount: 10, label: "연속 참격", icon: "⇊", note: "2회 공격", hits: 2, heavy: true },
    { kind: "attack", amount: 22, label: "관문 파쇄", icon: "⚠", note: "치명적인 일격", hits: 1, heavy: true },
  ],
];

const ARENA_NAMES = [
  "햇살 언덕",
  "바람꽃 숲길",
  "이끼 낀 회랑",
  "노을빛 성소",
  "태양의 관문",
];

const makeIntent = (stage: number, combatTurn: number, strength = 0): EnemyIntent => {
  const pattern = INTENT_PATTERNS[stage];
  const selected = pattern[(combatTurn - 1) % pattern.length];
  const scalesWithStrength = selected.kind === "attack" || selected.kind === "multi" || selected.kind === "drain";
  return {
    ...selected,
    amount: selected.amount + (scalesWithStrength ? strength : 0),
  };
};

const drawCardRewards = () =>
  (["bleed", "guard", "focus"] as const)
    .map((strategy) => CARD_LIBRARY[shuffle(STRATEGY_CARD_IDS[strategy])[0]]);

const getCardDamage = (card: CardDefinition, player: Player) => {
  const missingBonus = card.missingScale
    ? Math.floor((player.maxHp - player.hp) / 8) * 2
    : 0;
  return (card.damage ?? 0) + missingBonus;
};

function CardFace({
  card,
  player,
  disabled,
  onClick,
  reward = false,
}: {
  card: CardDefinition;
  player: Player;
  disabled?: boolean;
  onClick: () => void;
  reward?: boolean;
}) {
  const dynamicDamage = getCardDamage(card, player);
  const baseDescription = card.missingScale
    ? `피해 ${dynamicDamage}. 잃은 체력에 비례.`
    : card.description;
  const description = card.type === "attack" && player.focus > 0
    ? `${baseDescription} 집중 보너스 +${player.focus * 4}.`
    : baseDescription;

  return (
    <button
      type="button"
      className={`battle-card ${card.type} ${card.rarity} strategy-${card.strategy} ${reward ? "reward-card-face" : ""}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={`${card.name}, 비용 ${card.cost}, ${description}`}
    >
      <span className="card-cost">{card.cost}</span>
      <span className="card-rarity">{card.rarity === "rare" ? "RARE" : card.type === "attack" ? "ATTACK" : "SKILL"}</span>
      <strong>{card.name}</strong>
      <span className={`card-strategy strategy-${card.strategy}`}>{STRATEGY_LABELS[card.strategy]}</span>
      <span className="card-art" aria-hidden="true">
        <img src={card.art} alt="" draggable={false} />
      </span>
      <span className="card-description">{description}</span>
    </button>
  );
}

export default function Home() {
  const handScrollRef = useRef<HTMLDivElement>(null);
  const handDragRef = useRef({
    active: false,
    startX: 0,
    scrollLeft: 0,
    moved: false,
    lastX: 0,
    lastTime: 0,
    velocity: 0,
  });
  const handAnimationRef = useRef<number | null>(null);
  const suppressHandClickRef = useRef(false);
  const [phase, setPhase] = useState<Phase>("intro");
  const [oath, setOath] = useState<OathId | null>(null);
  const [stage, setStage] = useState(0);
  const [player, setPlayer] = useState<Player>(INITIAL_PLAYER);
  const [enemy, setEnemy] = useState<Enemy>(makeEnemy(0));
  const [intent, setIntent] = useState<EnemyIntent>(makeIntent(0, 1));
  const [battleEffect, setBattleEffect] = useState<BattleEffect | null>(null);
  const [deck, setDeck] = useState<CardInstance[]>(INITIAL_DECK);
  const [drawPile, setDrawPile] = useState<CardInstance[]>(INITIAL_DECK.slice(5));
  const [discardPile, setDiscardPile] = useState<CardInstance[]>([]);
  const [hand, setHand] = useState<CardInstance[]>(INITIAL_DECK.slice(0, 5));
  const [energy, setEnergy] = useState(BASE_ENERGY);
  const [retainedCardUid, setRetainedCardUid] = useState<string | null>(null);
  const [currentMapNodeId, setCurrentMapNodeId] = useState("start");
  const [visitedMapNodeIds, setVisitedMapNodeIds] = useState<string[]>(["start"]);
  const [mapNodeKinds, setMapNodeKinds] = useState<Record<string, MapNodeKind>>(INITIAL_MAP_NODE_KINDS);
  const [activeMapEvent, setActiveMapEvent] = useState<MapEventDefinition | null>(null);
  const [turns, setTurns] = useState(0);
  const [combatTurn, setCombatTurn] = useState(1);
  const [cardsPlayed, setCardsPlayed] = useState(0);
  const [skillsPlayedThisTurn, setSkillsPlayedThisTurn] = useState(0);
  const [cardRewards, setCardRewards] = useState<CardDefinition[]>([
    CARD_LIBRARY.twinSlash,
    CARD_LIBRARY.ironWall,
    CARD_LIBRARY.meditate,
  ]);
  const [logs, setLogs] = useState<LogEntry[]>([
    { id: "intro-log", text: "관문 너머에서 무언가 숨을 고른다.", tone: "normal" },
  ]);

  const enterBattle = (
    nextStage: number,
    runDeck: CardInstance[],
    nextPlayer: Player,
    activeOath: OathId | null = oath,
  ) => {
    const prepared = prepareHand(runDeck);
    const openingBlock = activeOath === "iron" ? 6 : 0;
    setStage(nextStage);
    setEnemy(makeEnemy(nextStage));
    setIntent(makeIntent(nextStage, 1));
    setPlayer({ ...nextPlayer, block: openingBlock, focus: 0 });
    setHand(prepared.drawn);
    setDrawPile(prepared.drawPile);
    setDiscardPile(prepared.discardPile);
    setEnergy(BASE_ENERGY);
    setRetainedCardUid(null);
    setCombatTurn(1);
    setSkillsPlayedThisTurn(0);
    setBattleEffect(null);
    setPhase("battle");
  };

  const startGame = (nextOath: OathId) => {
    const freshDeck = makeStartingDeck(nextOath);
    setOath(nextOath);
    setDeck(freshDeck);
    setPlayer({ ...INITIAL_PLAYER });
    setStage(0);
    setCurrentMapNodeId("start");
    setVisitedMapNodeIds(["start"]);
    setMapNodeKinds(createRandomMapNodeKinds());
    setActiveMapEvent(null);
    setRetainedCardUid(null);
    setEnergy(BASE_ENERGY);
    setTurns(0);
    setCardsPlayed(0);
    setLogs([
      makeLog(`${OATHS[nextOath].name}을 맺었다.`, "good"),
      makeLog("햇살이 갈라지는 원정 지도가 펼쳐졌다."),
      makeLog("첫 번째 전투로 향할 길을 선택하세요.", "good"),
    ]);
    setPhase("map");
  };

  const chooseMapNode = (targetNode: ExpeditionNode) => {
    if (phase !== "map") return;
    const currentNode = getMapNode(currentMapNodeId);
    if (!currentNode?.links.includes(targetNode.id)) return;

    const nodeKind = mapNodeKinds[targetNode.id] ?? targetNode.kind;

    setCurrentMapNodeId(targetNode.id);
    setVisitedMapNodeIds((current) => current.includes(targetNode.id) ? current : [...current, targetNode.id]);

    if ((nodeKind === "battle" || nodeKind === "boss") && targetNode.encounter !== undefined) {
      setLogs((current) => [
        makeLog(`${targetNode.label}(으)로 향한다.`, "good"),
        makeLog(`${ENCOUNTERS[targetNode.encounter!].name}이(가) 길을 막아선다.`, "danger"),
        ...current,
      ].slice(0, 14));
      enterBattle(targetNode.encounter, deck, player, oath);
      return;
    }

    const nextEvent = nodeKind === "rest"
      ? REST_EVENT
      : shuffle(MAP_EVENTS)[0];
    setActiveMapEvent(nextEvent);
    setLogs((current) => [
      makeLog(`${targetNode.label}에서 ${nextEvent.title}을(를) 발견했다.`, "good"),
      ...current,
    ].slice(0, 14));
    setPhase("event");
  };

  const resolveMapEvent = (choice: MapEventChoice) => {
    if (phase !== "event" || !activeMapEvent) return;
    if (choice.cost && player.hp <= choice.cost) return;

    const nextPlayer = { ...player, block: 0, focus: 0 };
    const nextDeck = [...deck];
    let resultText = choice.description;

    if (choice.cost) nextPlayer.hp -= choice.cost;

    if (choice.effect === "heal") {
      const recovered = Math.min(choice.amount ?? 0, nextPlayer.maxHp - nextPlayer.hp);
      nextPlayer.hp += recovered;
      resultText = recovered > 0 ? `체력을 ${recovered} 회복했다.` : "이미 체력이 가득 차 있어 잠시 숨을 골랐다.";
    } else if (choice.effect === "max-hp") {
      const growth = choice.amount ?? 0;
      nextPlayer.maxHp += growth;
      nextPlayer.hp += growth;
      resultText = `최대 체력과 현재 체력이 ${growth} 증가했다.`;
    } else {
      const cardPool = choice.effect === "rare-card" ? RARE_EVENT_CARD_IDS : COMMON_EVENT_CARD_IDS;
      const card = CARD_LIBRARY[shuffle(cardPool)[0]];
      nextDeck.push(makeCard(card.id));
      resultText = `${card.name}을(를) 덱에 추가했다.${choice.cost ? ` 체력 ${choice.cost}을 지불했다.` : ""}`;
    }

    setPlayer(nextPlayer);
    setDeck(nextDeck);
    setLogs((current) => [
      makeLog(`${activeMapEvent.title}: ${resultText}`, "good"),
      makeLog("지도로 돌아왔다. 이어질 길을 선택하세요."),
      ...current,
    ].slice(0, 14));
    setActiveMapEvent(null);
    setPhase("map");
  };

  const playCard = (instance: CardInstance) => {
    if (phase !== "battle") return;
    if (instance.uid === retainedCardUid) return;
    const card = CARD_LIBRARY[instance.cardId];
    if (!card || card.cost > energy) return;

    const nextPlayer = { ...player };
    const nextEnemy = { ...enemy };
    const nextLogs = [...logs];
    let nextHand = hand.filter((item) => item.uid !== instance.uid);
    let nextDrawPile = [...drawPile];
    let nextDiscardPile = [...discardPile];
    const perHitDamage = getCardDamage(card, nextPlayer);
    const hitCount = card.hits ?? 1;
    const vulnerabilityMultiplier = nextEnemy.vulnerable > 0 ? 1.5 : 1;
    const focusBonus = card.type === "attack" ? nextPlayer.focus * 4 : 0;
    const bleedBonus = (card.bleedScale ?? 0) * nextEnemy.bleed;
    const guardBonus = (card.blockScale ?? 0) * nextPlayer.block;
    const totalDamage = Math.round((perHitDamage * hitCount + focusBonus + bleedBonus + guardBonus) * vulnerabilityMultiplier);
    let nextEffect: BattleEffect | null = null;

    if (totalDamage > 0) {
      const absorbed = Math.min(nextEnemy.block, totalDamage);
      const hpDamage = totalDamage - absorbed;
      nextEnemy.block -= absorbed;
      nextEnemy.hp = Math.max(0, nextEnemy.hp - hpDamage);
      const hitText = hitCount > 1 ? ` (${perHitDamage}×${hitCount})` : "";
      const vulnerableText = nextEnemy.vulnerable > 0 ? " · 취약" : "";
      const focusText = focusBonus > 0 ? ` · 집중 +${focusBonus}` : "";
      const bleedText = bleedBonus > 0 ? ` · 출혈 연계 +${bleedBonus}` : "";
      const guardText = guardBonus > 0 ? ` · 방어 반격 +${guardBonus}` : "";
      const blockedText = absorbed > 0 ? ` · 적 방어 ${absorbed}` : "";
      nextLogs.unshift(makeLog(`${card.name}: ${hpDamage} 피해${hitText}${focusText}${bleedText}${guardText}${vulnerableText}${blockedText}`, "good"));
      nextEffect = {
        id: `${Date.now()}-${Math.random()}`,
        kind: "enemy-hit",
        target: "enemy",
        variant: card.effect,
        text: hpDamage > 0 ? `-${hpDamage}` : "BLOCK",
      };
      nextPlayer.focus = 0;
    }

    if (card.consumeBleed && nextEnemy.bleed > 0) {
      nextLogs.unshift(makeLog(`${card.name}: 출혈 ${nextEnemy.bleed}을(를) 모두 수확했다.`, "good"));
      nextEnemy.bleed = 0;
    }

    if (card.block) {
      nextPlayer.block += card.block;
      nextLogs.unshift(makeLog(`${card.name}: 방어도 ${card.block} 획득.`));
      nextEffect ??= {
        id: `${Date.now()}-${Math.random()}`,
        kind: "shield",
        target: "player",
        variant: card.effect,
        text: `+${card.block}`,
      };
    }

    if (card.heal) {
      const healed = Math.min(card.heal, nextPlayer.maxHp - nextPlayer.hp);
      nextPlayer.hp += healed;
      nextLogs.unshift(makeLog(`${card.name}: 체력 ${healed} 회복.`, "good"));
      if (healed > 0) {
        nextEffect ??= {
          id: `${Date.now()}-${Math.random()}`,
          kind: "heal",
          target: "player",
          variant: card.effect,
          text: `+${healed}`,
        };
      }
    }

    if (card.vulnerable) {
      nextEnemy.vulnerable += card.vulnerable;
      nextLogs.unshift(makeLog(`${nextEnemy.name}에게 취약 ${card.vulnerable} 부여.`, "good"));
    }

    if (card.bleed) {
      const appliedBleed = card.bleed + (oath === "blood" ? 1 : 0);
      nextEnemy.bleed += appliedBleed;
      nextLogs.unshift(makeLog(`${nextEnemy.name}에게 출혈 ${appliedBleed} 부여.`, "good"));
    }

    const oathFocus = oath === "ember" && card.type === "skill" && skillsPlayedThisTurn === 0 ? 1 : 0;
    const totalFocus = (card.focus ?? 0) + oathFocus;
    if (totalFocus > 0) {
      const gainedFocus = Math.min(totalFocus, 3 - nextPlayer.focus);
      nextPlayer.focus += gainedFocus;
      if (gainedFocus > 0) {
        nextLogs.unshift(makeLog(`${card.name}: 집중 ${gainedFocus} 획득. 다음 공격 피해 +${nextPlayer.focus * 4}.`, "good"));
        nextEffect ??= {
          id: `${Date.now()}-${Math.random()}`,
          kind: "focus",
          target: "player",
          variant: card.effect,
          text: `✦${nextPlayer.focus}`,
        };
      }
    }

    if (card.draw) {
      const result = drawCards(card.draw, nextDrawPile, nextDiscardPile);
      nextHand = [...nextHand, ...result.drawn];
      nextDrawPile = result.drawPile;
      nextDiscardPile = result.discardPile;
    }

    if (intent.kind === "counter" && card.type === "attack" && nextEnemy.hp > 0) {
      const absorbed = Math.min(nextPlayer.block, intent.amount);
      const counterDamage = Math.max(0, intent.amount - nextPlayer.block);
      nextPlayer.block -= absorbed;
      nextPlayer.hp = Math.max(0, nextPlayer.hp - counterDamage);
      nextLogs.unshift(makeLog(
        `${nextEnemy.name}의 반격: ${counterDamage} 피해${absorbed > 0 ? ` · 방어 ${absorbed}` : ""}`,
        counterDamage > 0 ? "danger" : "normal",
      ));
      nextEffect ??= {
        id: `${Date.now()}-${Math.random()}`,
        kind: "player-hit",
        target: "player",
        text: counterDamage > 0 ? `-${counterDamage}` : "BLOCK",
      };
    }

    if (
      stage === ENCOUNTERS.length - 1
      && nextEnemy.hp > 0
      && nextEnemy.hp <= Math.ceil(nextEnemy.maxHp / 2)
      && nextEnemy.phase === 1
      && nextPlayer.hp > 0
    ) {
      nextEnemy.phase = 2;
      nextEnemy.strength += 3;
      nextEnemy.block += 12;
      nextLogs.unshift(makeLog("수호자 2단계: 태양석 봉인이 깨어났다. 공격력 +3 · 방어도 12.", "danger"));
      setIntent(makeIntent(stage, combatTurn, nextEnemy.strength));
    }

    nextDiscardPile = [...nextDiscardPile, instance];
    setEnergy(energy - card.cost + (card.energy ?? 0));
    setCardsPlayed((value) => value + 1);
    if (card.type === "skill") setSkillsPlayedThisTurn((value) => value + 1);
    setPlayer(nextPlayer);
    setEnemy(nextEnemy);
    setHand(nextHand);
    setDrawPile(nextDrawPile);
    setDiscardPile(nextDiscardPile);
    setLogs(nextLogs.slice(0, 14));
    setBattleEffect(nextEffect);

    if (nextPlayer.hp === 0) {
      setPhase("defeat");
      return;
    }

    if (nextEnemy.hp === 0) {
      setLogs([
        makeLog(`${nextEnemy.name} 격파. 전리품과 휴식 중 하나를 선택하세요.`, "good"),
        ...nextLogs,
      ].slice(0, 14));

      if (stage === ENCOUNTERS.length - 1) {
        setPhase("victory");
      } else {
        setCardRewards(drawCardRewards());
        setPhase("reward");
      }
    }
  };

  const toggleRetain = (instance: CardInstance) => {
    if (phase !== "battle") return;
    const card = CARD_LIBRARY[instance.cardId];

    if (retainedCardUid === instance.uid) {
      setRetainedCardUid(null);
      setEnergy((value) => value + RETAIN_COST);
      setLogs((current) => [
        makeLog(`${card.name} 보존을 취소해 에너지 ${RETAIN_COST}을 되찾았다.`),
        ...current,
      ].slice(0, 14));
      return;
    }

    if (retainedCardUid) {
      setRetainedCardUid(instance.uid);
      setLogs((current) => [
        makeLog(`보존 대상을 ${card.name}(으)로 변경했다.`, "good"),
        ...current,
      ].slice(0, 14));
      return;
    }

    if (energy < RETAIN_COST) return;
    setRetainedCardUid(instance.uid);
    setEnergy((value) => value - RETAIN_COST);
    setLogs((current) => [
      makeLog(`${card.name} 보존 준비. 에너지 ${RETAIN_COST} 예약.`, "good"),
      ...current,
    ].slice(0, 14));
  };

  const endTurn = () => {
    if (phase !== "battle") return;

    const nextPlayer = { ...player, block: 0 };
    const nextEnemy = { ...enemy, block: 0 };
    const nextLogs = [...logs];
    let nextEffect: BattleEffect;

    if (intent.kind === "counter") {
      nextEnemy.block = intent.amount * 2;
      nextLogs.unshift(makeLog(`${enemy.name}이(가) 반격 태세를 거두며 방어도 ${nextEnemy.block} 획득.`));
      nextEffect = {
        id: `${Date.now()}-${Math.random()}`,
        kind: "shield",
        target: "enemy",
        text: `+${nextEnemy.block}`,
      };
    } else if (intent.kind === "guard") {
      nextEnemy.block = intent.amount;
      nextLogs.unshift(makeLog(`${enemy.name}의 ${intent.label}: 방어도 ${intent.amount} 획득.`));
      nextEffect = {
        id: `${Date.now()}-${Math.random()}`,
        kind: "shield",
        target: "enemy",
        text: `+${intent.amount}`,
      };
    } else if (intent.kind === "buff") {
      nextEnemy.strength += intent.amount;
      nextLogs.unshift(makeLog(`${enemy.name}의 ${intent.label}: 이후 공격력 +${intent.amount}.`, "danger"));
      nextEffect = {
        id: `${Date.now()}-${Math.random()}`,
        kind: "buff",
        target: "enemy",
        text: `↑${intent.amount}`,
      };
    } else {
      const incomingDamage = intent.amount * intent.hits;
      const absorbed = Math.min(player.block, incomingDamage);
      const damage = Math.max(0, incomingDamage - player.block);
      nextPlayer.hp = Math.max(0, player.hp - damage);
      const multiText = intent.hits > 1 ? ` (${intent.amount}×${intent.hits})` : "";
      let drainText = "";

      if (intent.kind === "drain") {
        const healed = Math.min(5, nextEnemy.maxHp - nextEnemy.hp);
        nextEnemy.hp += healed;
        drainText = ` · 체력 ${healed} 흡수`;
      }

      nextLogs.unshift(makeLog(
        `${enemy.name}의 ${intent.label}: ${damage} 피해${multiText}${absorbed > 0 ? ` · 방어 ${absorbed}` : ""}${drainText}`,
        damage >= 12 ? "danger" : "normal",
      ));
      nextEffect = {
        id: `${Date.now()}-${Math.random()}`,
        kind: "player-hit",
        target: "player",
        text: damage > 0 ? `-${damage}` : "BLOCK",
      };
    }

    setTurns((value) => value + 1);
    setPlayer(nextPlayer);
    setEnemy(nextEnemy);
    setBattleEffect(nextEffect);

    if (nextPlayer.hp === 0) {
      setLogs(nextLogs.slice(0, 14));
      setPhase("defeat");
      return;
    }

    const retainedCard = retainedCardUid
      ? hand.find((instance) => instance.uid === retainedCardUid)
      : undefined;
    const remainingHand = retainedCard
      ? hand.filter((instance) => instance.uid !== retainedCard.uid)
      : hand;
    const carriedEnergy = Math.min(MAX_ENERGY_CARRY, energy);
    const result = drawCards(
      HAND_SIZE - (retainedCard ? 1 : 0),
      drawPile,
      [...discardPile, ...remainingHand],
    );
    const nextCombatTurn = combatTurn + 1;

    if (retainedCard) {
      nextLogs.unshift(makeLog(
        `전술 보존: ${CARD_LIBRARY[retainedCard.cardId].name}을(를) 다음 턴 손에 남겼다.`,
        "good",
      ));
    }
    if (carriedEnergy > 0) {
      nextLogs.unshift(makeLog(`잔광: 남은 에너지 ${carriedEnergy}을(를) 다음 턴으로 이월했다.`, "good"));
    }

    setLogs(nextLogs.slice(0, 14));
    setHand(retainedCard ? [retainedCard, ...result.drawn] : result.drawn);
    setDrawPile(result.drawPile);
    setDiscardPile(result.discardPile);
    setEnergy(BASE_ENERGY + carriedEnergy);
    setRetainedCardUid(null);
    setCombatTurn(nextCombatTurn);
    setSkillsPlayedThisTurn(0);
    nextEnemy.vulnerable = Math.max(0, nextEnemy.vulnerable - 1);
    setEnemy(nextEnemy);
    setIntent(makeIntent(stage, nextCombatTurn, nextEnemy.strength));
  };

  const chooseCardReward = (card?: CardDefinition) => {
    const nextDeck = card ? [...deck, makeCard(card.id)] : [...deck];
    const recovery = card ? 0 : Math.min(14, player.maxHp - player.hp);
    const nextPlayer = card
      ? { ...player }
      : { ...player, hp: player.hp + recovery };
    setDeck(nextDeck);
    setLogs((current) => [
      makeLog(card ? `${card.name}을(를) 덱에 추가했다.` : `야영지에서 체력 ${recovery} 회복.`, "good"),
      makeLog("원정 지도로 돌아왔다. 다음 길을 선택하세요."),
      ...current,
    ].slice(0, 14));
    setPlayer(nextPlayer);
    setPhase("map");
  };

  const startHandDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    const container = handScrollRef.current;
    if (!container) return;

    if (handAnimationRef.current !== null) {
      window.cancelAnimationFrame(handAnimationRef.current);
      handAnimationRef.current = null;
    }

    handDragRef.current = {
      active: true,
      startX: event.clientX,
      scrollLeft: container.scrollLeft,
      moved: false,
      lastX: event.clientX,
      lastTime: performance.now(),
      velocity: 0,
    };
    suppressHandClickRef.current = false;
    container.classList.add("is-dragging");
    container.setPointerCapture(event.pointerId);
  };

  const moveHandDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    const container = handScrollRef.current;
    const drag = handDragRef.current;
    if (!container || !drag.active) return;

    const now = performance.now();
    const distance = event.clientX - drag.startX;
    const elapsed = Math.max(1, now - drag.lastTime);
    const instantVelocity = -(event.clientX - drag.lastX) / elapsed;

    if (Math.abs(distance) > HAND_DRAG_THRESHOLD) {
      drag.moved = true;
      suppressHandClickRef.current = true;
    }
    if (!drag.moved) return;

    drag.velocity = (drag.velocity * 0.7) + (instantVelocity * 0.3);
    drag.lastX = event.clientX;
    drag.lastTime = now;
    container.scrollLeft = drag.scrollLeft - distance;
    if (event.cancelable) event.preventDefault();
  };

  const endHandDrag = (event: ReactPointerEvent<HTMLDivElement>) => {
    const container = handScrollRef.current;
    const drag = handDragRef.current;
    const wasMoved = drag.moved;
    drag.active = false;

    if (container?.hasPointerCapture(event.pointerId)) {
      container.releasePointerCapture(event.pointerId);
    }
    container?.classList.remove("is-dragging");

    if (wasMoved) {
      if (container) {
        const maxScroll = Math.max(0, container.scrollWidth - container.clientWidth);
        const firstCard = container.querySelector<HTMLElement>(".hand-card-slot");
        const computedStyle = window.getComputedStyle(container);
        const cardGap = Number.parseFloat(computedStyle.columnGap || computedStyle.gap) || 0;
        const cardStep = firstCard ? firstCard.offsetWidth + cardGap : 150;
        const releaseVelocity = performance.now() - drag.lastTime > 100 ? 0 : drag.velocity;
        const flingDistance = Math.max(
          -HAND_MAX_FLING_DISTANCE,
          Math.min(HAND_MAX_FLING_DISTANCE, releaseVelocity * HAND_MOMENTUM_MS),
        );
        const projectedScroll = Math.max(0, Math.min(maxScroll, container.scrollLeft + flingDistance));
        const targetScroll = Math.max(0, Math.min(maxScroll, Math.round(projectedScroll / cardStep) * cardStep));
        const startScroll = container.scrollLeft;
        const scrollDistance = targetScroll - startScroll;
        const duration = Math.min(440, Math.max(240, Math.abs(scrollDistance) * 1.1));
        const startedAt = performance.now();

        const animateScroll = (timestamp: number) => {
          const progress = Math.min(1, (timestamp - startedAt) / duration);
          const easedProgress = 1 - Math.pow(1 - progress, 3);
          container.scrollLeft = startScroll + (scrollDistance * easedProgress);

          if (progress < 1) {
            handAnimationRef.current = window.requestAnimationFrame(animateScroll);
          } else {
            handAnimationRef.current = null;
          }
        };

        handAnimationRef.current = window.requestAnimationFrame(animateScroll);
      }

      window.setTimeout(() => {
        suppressHandClickRef.current = false;
      }, 0);
    }
  };

  const blockCardClickAfterDrag = (event: ReactMouseEvent<HTMLDivElement>) => {
    if (!suppressHandClickRef.current) return;
    event.preventDefault();
    event.stopPropagation();
    suppressHandClickRef.current = false;
  };

  const hpPercent = Math.max(0, (player.hp / player.maxHp) * 100);
  const enemyPercent = Math.max(0, (enemy.hp / enemy.maxHp) * 100);
  const deckSummary = Object.entries(
    deck.reduce<Record<string, number>>((summary, card) => {
      summary[card.cardId] = (summary[card.cardId] ?? 0) + 1;
      return summary;
    }, {}),
  );
  const strategySummary = (["bleed", "guard", "focus"] as const).map((strategy) => ({
    strategy,
    count: deck.filter((instance) => CARD_LIBRARY[instance.cardId].strategy === strategy).length,
  }));
  const dominantStrategy = [...strategySummary].sort((a, b) => b.count - a.count)[0].strategy;
  const retainedCard = retainedCardUid
    ? hand.find((instance) => instance.uid === retainedCardUid)
    : undefined;
  const retainedDefinition = retainedCard ? CARD_LIBRARY[retainedCard.cardId] : undefined;
  const projectedEnergyCarry = Math.min(MAX_ENERGY_CARRY, energy);
  const currentMapNode = getMapNode(currentMapNodeId) ?? EXPEDITION_MAP[0];
  const availableMapNodeIds = currentMapNode.links;
  const clearedMapNodes = Math.max(0, visitedMapNodeIds.length - 1);
  const intentForecast = Array.from({ length: 3 }, (_, index) =>
    makeIntent(stage, combatTurn + index, enemy.strength));

  return (
    <main className="game-shell">
      <header className="game-header">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">Ⅴ</span>
          <div>
            <p className="eyebrow">A SUNLIT DECKBUILDING ADVENTURE</p>
            <h1>마지막 관문 <span>LAST GATE</span></h1>
          </div>
        </div>
        <div className="run-chip"><span /> {oath ? OATHS[oath].name : "서약 선택 전"} · {STRATEGY_LABELS[dominantStrategy]}</div>
      </header>

      <div className="game-grid">
        <aside className="panel route-panel" aria-label="원정 진행도와 덱 구성">
          <div className="panel-heading">
            <span>원정 기록</span>
            <small>{Math.min(stage + 1, 5)} / 5</small>
          </div>
          <div className="route-line">
            {ENCOUNTERS.map((encounter, index) => {
              const state = index < stage ? "cleared" : index === stage ? "current" : "locked";
              return (
                <div className={`route-step ${state}`} key={encounter.name}>
                  <div className="route-node">{index < stage ? "✓" : index + 1}</div>
                  <div>
                    <strong>{index === 4 ? "최후의 관문" : `${index + 1}구역`}</strong>
                    <span>{index <= stage ? encounter.name : "미확인"}</span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="deck-panel">
            <div className="deck-title">
              <p className="micro-label">현재 덱</p>
              <strong>{deck.length}<span>장</span></strong>
            </div>
            {oath && (
              <div className={`active-oath oath-${OATHS[oath].tone}`}>
                <span>{OATHS[oath].glyph}</span>
                <div><small>ACTIVE OATH</small><strong>{OATHS[oath].name}</strong></div>
              </div>
            )}
            <div className="deck-list">
              {deckSummary.map(([cardId, count]) => (
                <div key={cardId}>
                  <span className={CARD_LIBRARY[cardId].type}>{CARD_LIBRARY[cardId].glyph}</span>
                  <p>{CARD_LIBRARY[cardId].name}</p>
                  <strong>×{count}</strong>
                </div>
              ))}
            </div>
            <div className="build-identity">
              <p className="micro-label">덱 방향</p>
              {strategySummary.map(({ strategy, count }) => (
                <div className={`strategy-${strategy}`} key={strategy}>
                  <span />
                  <p>{STRATEGY_LABELS[strategy]}</p>
                  <strong>{count}</strong>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <section className="panel battlefield" aria-label="카드 전투 화면">
          <div className="battle-topline">
            <div>
              <span className="stage-kicker">ENCOUNTER {String(stage + 1).padStart(2, "0")} · TURN {combatTurn}</span>
              <strong>{ARENA_NAMES[stage]}</strong>
            </div>
            <div className={`intent ${intent.kind} ${intent.heavy ? "heavy" : ""}`}>
              <span>적의 현재 의도</span>
              <strong>{intent.icon} {intent.label} {intent.amount}{intent.hits > 1 ? `×${intent.hits}` : ""}</strong>
              <small>{intent.note}</small>
            </div>
          </div>

          <div className="enemy-readout">
            <div>
              <p>{enemy.title}</p>
              <h2>{enemy.name}</h2>
            </div>
            <div className="enemy-status">
              {enemy.phase === 2 && <span className="phase-badge">2단계</span>}
              {enemy.block > 0 && <span className="enemy-block-badge">◇ {enemy.block}</span>}
              {enemy.strength > 0 && <span className="strength-badge">↑ {enemy.strength}</span>}
              {enemy.bleed > 0 && <span className="bleed-badge">출혈 {enemy.bleed}</span>}
              {enemy.vulnerable > 0 && <span className="vulnerable-badge">취약 {enemy.vulnerable}</span>}
              <strong>{enemy.hp} <span>/ {enemy.maxHp}</span></strong>
            </div>
          </div>
          <div className="health-track enemy-health" role="progressbar" aria-label="적 체력" aria-valuenow={enemy.hp} aria-valuemin={0} aria-valuemax={enemy.maxHp}>
            <span style={{ width: `${enemyPercent}%` }} />
          </div>

          <div className={`arena enemy-${enemy.tone} intent-${intent.kind} ${enemy.phase === 2 ? "boss-enraged" : ""}`}>
            <div className="far-gate" aria-hidden="true"><i /><i /><i /></div>
            <div className="dust dust-one" />
            <div className="dust dust-two" />
            <div className="enemy-aura" aria-hidden="true" />
            <div className="pattern-forecast" aria-label="적의 행동 순서">
              <span>PATTERN</span>
              {intentForecast.map((forecast, index) => (
                <div className={index === 0 ? "current" : ""} key={`${forecast.label}-${index}`}>
                  <strong>{forecast.icon}</strong><small>{forecast.label}</small>
                </div>
              ))}
            </div>
            <div className={`intent-orb ${intent.kind}`} aria-hidden="true">
              <small>{intent.icon} {intent.label}</small>
              <strong>{intent.hits > 1 ? `${intent.amount}×${intent.hits}` : intent.amount}</strong>
            </div>
            <div className="enemy-figure" aria-hidden="true">
              <img className="enemy-portrait" src={enemy.art} alt="" draggable={false} />
              <i className="enemy-shadow" />
            </div>
            {battleEffect && (
              <div key={battleEffect.id} className={`battle-effect ${battleEffect.kind} target-${battleEffect.target} ${battleEffect.variant ? `fx-${battleEffect.variant}` : ""}`} aria-hidden="true">
                <i className="fx-main" />
                <i className="fx-secondary" />
                <i className="fx-accent" />
                <strong>{battleEffect.text}</strong>
              </div>
            )}
            <p className="enemy-description">“{enemy.phase === 2 ? "태양석이 깨어나고 눈부신 불꽃이 소용돌이친다." : enemy.description}”</p>
          </div>

          <div className="player-readout">
            <div className="player-name">
              <span className="player-sigil">†</span>
              <div><small>THE GATE SEEKER</small><strong>관문을 찾는 모험가</strong></div>
            </div>
            <div className="player-vitals">
              {player.focus > 0 && <span className="focus-badge">✦ 집중 {player.focus} · 다음 공격 +{player.focus * 4}</span>}
              {player.block > 0 && <span className="block-badge">◇ {player.block}</span>}
              <div className="player-hp"><strong>{player.hp}</strong><span> / {player.maxHp} HP</span></div>
            </div>
          </div>
          <div className="health-track player-health" role="progressbar" aria-label="플레이어 체력" aria-valuenow={player.hp} aria-valuemin={0} aria-valuemax={player.maxHp}>
            <span style={{ width: `${hpPercent}%` }} />
          </div>

          <div className="turn-controls">
            <div className="resource-counters">
              <div className="energy-counter" aria-label={`에너지 ${energy}`}>
                <strong>{energy}</strong><span>3 BASE<br />+1 CARRY</span>
              </div>
              <div className={`focus-counter ${player.focus > 0 ? "active" : ""}`} aria-label={`집중 ${player.focus}`}>
                <strong>✦{player.focus}</strong><span>NEXT HIT<br />+{player.focus * 4}</span>
              </div>
            </div>
            <div className="pile-counts">
              <div><span className="pile-icon">▤</span><p>뽑을 카드<strong>{drawPile.length}</strong></p></div>
              <div><span className="pile-icon discard">▧</span><p>버린 카드<strong>{discardPile.length}</strong></p></div>
            </div>
            <button type="button" onClick={endTurn} disabled={phase !== "battle"}>
              턴 종료 <span>→</span>
            </button>
          </div>

          <div className="turn-plan" aria-live="polite">
            <span className={projectedEnergyCarry > 0 ? "active" : ""}>☼ 에너지 이월 {projectedEnergyCarry}</span>
            <span className={retainedDefinition ? "active" : ""}>◇ {retainedDefinition ? `${retainedDefinition.name} 보존` : "보존 카드 없음"}</span>
            <small>남은 에너지 최대 1 이월 · 카드 보존 비용 1</small>
          </div>

          <div className="mobile-hand-nav" aria-label="손패 이동">
            <button
              type="button"
              onClick={() => handScrollRef.current?.scrollBy({ left: -150, behavior: "smooth" })}
              disabled={phase !== "battle"}
              aria-label="이전 카드 보기"
            >
              ‹
            </button>
            <span>손패를 좌우로 밀거나 버튼으로 이동</span>
            <button
              type="button"
              onClick={() => handScrollRef.current?.scrollBy({ left: 150, behavior: "smooth" })}
              disabled={phase !== "battle"}
              aria-label="다음 카드 보기"
            >
              ›
            </button>
          </div>

          <div
            className="card-hand"
            aria-label="현재 손패"
            ref={handScrollRef}
            onPointerDown={startHandDrag}
            onPointerMove={moveHandDrag}
            onPointerUp={endHandDrag}
            onPointerCancel={endHandDrag}
            onClickCapture={blockCardClickAfterDrag}
          >
            {hand.map((instance) => {
              const card = CARD_LIBRARY[instance.cardId];
              const isRetained = retainedCardUid === instance.uid;
              return (
                <div className={`hand-card-slot ${isRetained ? "has-retained-card" : ""}`} key={instance.uid}>
                  <CardFace
                    card={card}
                    player={player}
                    onClick={() => playCard(instance)}
                    disabled={phase !== "battle" || isRetained || card.cost > energy}
                  />
                  <button
                    type="button"
                    className="retain-toggle"
                    onClick={() => toggleRetain(instance)}
                    disabled={phase !== "battle" || (!retainedCardUid && energy < RETAIN_COST)}
                    aria-pressed={isRetained}
                    aria-label={`${card.name} ${isRetained ? "보존 취소" : "다음 턴까지 보존"}`}
                  >
                    {isRetained ? "✓ 보존됨" : `◇ 보존 ${RETAIN_COST}`}
                  </button>
                </div>
              );
            })}
            {hand.length === 0 && <div className="empty-hand">사용할 카드가 없습니다. 턴을 종료하세요.</div>}
          </div>

          {phase === "intro" && (
            <div className="modal-layer">
              <div className="intro-card oath-intro">
                <span className="intro-symbol">⌁</span>
                <p className="eyebrow">CHOOSE YOUR LIGHT. BEGIN THE JOURNEY.</p>
                <h2>햇살이 머무는<br />마지막 관문으로.</h2>
                <p>서약마다 시작 덱과 전투 규칙이 달라집니다. 나만의 전투 방식을 고르고, 여정에서 만난 카드로 덱을 성장시키세요.</p>
                <div className="oath-options">
                  {Object.values(OATHS).map((option) => (
                    <button className={`oath-option oath-${option.tone}`} type="button" key={option.id} onClick={() => startGame(option.id)}>
                      <span className="oath-art" aria-hidden="true">
                        <img src={option.art} alt="" draggable={false} />
                      </span>
                      <span className="oath-glyph">{option.glyph}</span>
                      <span className="oath-copy">
                        <small>{option.subtitle}</small>
                        <strong>{option.name}</strong>
                        <span className="oath-passive">{option.passive}</span>
                      </span>
                      <em>{option.starter}</em>
                    </button>
                  ))}
                </div>
                <small>서약별 전용 카드 2장 포함 · 약 6–10분 · 저장되지 않음</small>
              </div>
            </div>
          )}

          {phase === "map" && (
            <div className="modal-layer map-layer">
              <div className="expedition-map-card">
                <div className="map-heading">
                  <div>
                    <p className="eyebrow">CHOOSE THE NEXT PATH</p>
                    <h2>햇살이 이어지는 길</h2>
                    <p>전투, 사건, 휴식이 원정마다 새롭게 배치됩니다. 빛나는 노드 중 하나를 골라 나아가세요.</p>
                  </div>
                  <div className="map-run-stats" aria-label="현재 원정 상태">
                    <span>체력 <strong>{player.hp}/{player.maxHp}</strong></span>
                    <span>덱 <strong>{deck.length}장</strong></span>
                    <span>진행 <strong>{clearedMapNodes}/5</strong></span>
                  </div>
                </div>

                <div className="map-canvas" aria-label="분기형 원정 지도">
                  <div className="map-sun" aria-hidden="true">☼</div>
                  {MAP_CONNECTIONS.map((connection) => {
                    const source = getMapNode(connection.sourceId)!;
                    const target = getMapNode(connection.targetId)!;
                    const sourceVisitIndex = visitedMapNodeIds.indexOf(connection.sourceId);
                    const isTraversed = sourceVisitIndex >= 0
                      && visitedMapNodeIds[sourceVisitIndex + 1] === connection.targetId;
                    const connectionState = isTraversed
                      ? "traversed"
                      : currentMapNodeId === connection.sourceId && availableMapNodeIds.includes(connection.targetId)
                        ? "available"
                        : "locked";
                    return (
                      <span
                        className={`map-connection ${connectionState}`}
                        style={getMapConnectionStyle(source, target)}
                        key={`${connection.sourceId}-${connection.targetId}`}
                        aria-hidden="true"
                      />
                    );
                  })}

                  {EXPEDITION_MAP.map((node) => {
                    const nodeKind = mapNodeKinds[node.id] ?? node.kind;
                    const isCurrent = currentMapNodeId === node.id;
                    const isVisited = visitedMapNodeIds.includes(node.id);
                    const isAvailable = availableMapNodeIds.includes(node.id);
                    const nodeState = isCurrent ? "current" : isVisited ? "visited" : isAvailable ? "available" : "locked";
                    const position = getMapPosition(node);
                    const nodeDescription = nodeKind === "start"
                      ? "서약의 출발점"
                      : nodeKind === "event"
                        ? "무작위 만남"
                        : nodeKind === "rest"
                          ? "회복 또는 성장"
                          : node.encounter === undefined
                            ? "알 수 없는 길"
                            : ENCOUNTERS[node.encounter].name;
                    const nodeIcon = nodeKind === "start"
                      ? "☀"
                      : nodeKind === "boss"
                        ? "♛"
                        : nodeKind === "event"
                          ? "?"
                          : nodeKind === "rest"
                            ? "☼"
                            : "⚔";
                    return (
                      <button
                        type="button"
                        className={`expedition-node ${nodeKind} ${nodeState}`}
                        style={{ left: `${position.x}%`, top: `${position.y}%` }}
                        onClick={() => chooseMapNode(node)}
                        disabled={!isAvailable}
                        aria-label={`${node.label}, ${nodeDescription}${isAvailable ? ", 이동 가능" : ""}`}
                        key={node.id}
                      >
                        <span>{nodeIcon}</span>
                        <strong>{node.label}</strong>
                        <small>{nodeDescription}</small>
                      </button>
                    );
                  })}
                </div>

                <div className="map-legend">
                  <span><i className="available" /> 선택 가능</span>
                  <span><i className="visited" /> 지나온 길</span>
                  <span>⚔ 일반 전투</span>
                  <span>? 무작위 사건</span>
                  <span>☼ 휴식</span>
                  <span>♛ 최종 보스</span>
                </div>
              </div>
            </div>
          )}

          {phase === "event" && activeMapEvent && (
            <div className="modal-layer map-event-layer">
              <div className={`map-event-card event-${activeMapEvent.tone}`}>
                <span className="map-event-symbol" aria-hidden="true">{activeMapEvent.glyph}</span>
                <p className="eyebrow">{activeMapEvent.subtitle}</p>
                <h2>{activeMapEvent.title}</h2>
                <p>{activeMapEvent.description}</p>
                <div className="map-event-choices">
                  {activeMapEvent.choices.map((choice) => {
                    const isUnavailable = Boolean(choice.cost && player.hp <= choice.cost);
                    return (
                      <button
                        type="button"
                        onClick={() => resolveMapEvent(choice)}
                        disabled={isUnavailable}
                        key={choice.id}
                      >
                        <strong>{choice.label}</strong>
                        <span>{choice.description}</span>
                        {choice.cost && <small>{isUnavailable ? "체력이 부족합니다" : `현재 체력 ${player.hp} → ${player.hp - choice.cost}`}</small>}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {phase === "reward" && (
            <div className="modal-layer reward-layer">
              <div className="reward-selection">
                <p className="eyebrow">CHOOSE YOUR GIFT</p>
                <h2>새 카드를 얻을까, 잠시 쉬어갈까</h2>
                <p>출혈 연계 · 방어 반격 · 집중 폭발 중 한 방향을 강화하거나, 카드를 포기하고 회복하세요.</p>
                <div className="reward-options">
                  {cardRewards.map((card) => (
                    <CardFace
                      key={card.id}
                      card={card}
                      player={player}
                      onClick={() => chooseCardReward(card)}
                      reward
                    />
                  ))}
                </div>
                <button className="rest-reward" type="button" onClick={() => chooseCardReward()}>
                  <span>☼ 야영지에서 휴식</span>
                  <strong>{player.hp < player.maxHp ? `체력 +${Math.min(14, player.maxHp - player.hp)}` : "체력 최대 · 카드 건너뛰기"}</strong>
                </button>
              </div>
            </div>
          )}

          {(phase === "victory" || phase === "defeat") && (
            <div className="modal-layer ending-layer">
              <div className="ending-card">
                <span className="ending-rune">{phase === "victory" ? "☼" : "×"}</span>
                <p className="eyebrow">{phase === "victory" ? "THE GATE IS OPEN" : "THE JOURNEY RESTS"}</p>
                <h2>{phase === "victory" ? "관문 너머에 아침이 밝았습니다." : "모험가는 잠시 숨을 고릅니다."}</h2>
                {oath && <p className="ending-oath">{OATHS[oath].glyph} {OATHS[oath].name}</p>}
                <div className="result-row">
                  <div><span>도달 구역</span><strong>{stage + 1} / 5</strong></div>
                  <div><span>사용한 카드</span><strong>{cardsPlayed}</strong></div>
                  <div><span>최종 덱</span><strong>{deck.length}장</strong></div>
                </div>
                <button type="button" onClick={() => { setOath(null); setPhase("intro"); setBattleEffect(null); }}>다른 서약으로 다시 도전 <span>↻</span></button>
              </div>
            </div>
          )}
        </section>

        <aside className="panel ledger-panel" aria-label="전투 기록">
          <div className="panel-heading">
            <span>전투 기록</span>
            <small>{turns} TURN</small>
          </div>
          <div className="battle-log" aria-live="polite">
            {logs.map((entry, index) => (
              <div className={`log-entry ${entry.tone}`} key={entry.id}>
                <span>{String(Math.max(turns - index, 0)).padStart(2, "0")}</span>
                <p>{entry.text}</p>
              </div>
            ))}
          </div>
          <div className="ledger-bottom">
            <p className="micro-label">전투 규칙</p>
            <div className="rule-list">
              <div><span>01</span><p>출혈은 쌍검의 피해를 높이고 수확으로 폭발합니다.</p></div>
              <div><span>02</span><p>맞받아치기는 현재 방어도만큼 더 강해집니다.</p></div>
              <div><span>03</span><p>집중은 다음 공격 한 장에 모두 소모됩니다.</p></div>
            </div>
          </div>
        </aside>
      </div>

      <footer className="game-footer">
        <span>DRAW · PLAY · DISCARD · REPEAT</span>
        <p>패배하면 초기 덱부터 다시 시작합니다.</p>
        <span>BUILD 0.8.0 · RANDOM PATH EVENTS</span>
      </footer>
    </main>
  );
}
