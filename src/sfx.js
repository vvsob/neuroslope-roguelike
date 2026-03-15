/**
 * sfx.js — Synthesised sound effects via Web Audio API.
 * No external audio files required — all sounds are procedurally generated.
 *
 * Browser autoplay: AudioContext is created lazily on first call, which
 * works reliably because playSfx() is always triggered by a user gesture
 * (clicking a card / button).
 *
 * Design notes for future merges:
 *  - Add new sounds by defining a function and wiring it into the switch
 *    inside playSfx().
 *  - masterGain.gain controls global volume (0–1). Hook it to a volume
 *    slider if needed.
 *  - SFX.enabled persists in module scope, survives re-renders.
 *
 * Sound catalogue:
 *   "cardPlay"    – soft paper whoosh when any card is played
 *   "attack"      – sharp noise crack + low pitch envelope (player attacks)
 *   "block"       – metallic clunk + high partial (player gains block)
 *   "heal"        – rising major third sine swell
 *   "buff"        – bright ascending arpeggio (player gains a positive status)
 *   "debuff"      – descending sawtooth warble (debuff applied to any unit)
 *   "enemyAttack" – deeper thud + rumble noise (enemy hits the player)
 *   "victory"     – 4-note ascending sine arpeggio
 *   "defeat"      – 4-note descending sawtooth minor fall
 */

let _ctx = null;
let _master = null;

function ctx() {
  if (!_ctx) {
    _ctx = new (window.AudioContext || window.webkitAudioContext)();
    _master = _ctx.createGain();
    _master.gain.value = 0.95;
    _master.connect(_ctx.destination);
  }
  if (_ctx.state === "suspended") _ctx.resume();
  return _ctx;
}

function dest() { return _master; }

// ── Low-level synth helpers ───────────────────────────────────────────────────

/**
 * Single oscillator with exponential gain decay.
 * @param {"sine"|"square"|"sawtooth"|"triangle"} type
 * @param {number} freqStart   Hz at t=now+delay
 * @param {number|null} freqEnd Hz at t=now+delay+dur, null = no sweep
 * @param {number} delay       seconds from now
 * @param {number} dur         duration in seconds
 * @param {number} gain        peak gain
 */
function osc(type, freqStart, freqEnd, delay, dur, gain = 0.25) {
  const c = ctx();
  const now = c.currentTime;
  const o = c.createOscillator();
  const g = c.createGain();

  o.type = type;
  o.frequency.setValueAtTime(freqStart, now + delay);
  if (freqEnd !== null) {
    o.frequency.exponentialRampToValueAtTime(
      Math.max(freqEnd, 1),
      now + delay + dur
    );
  }

  g.gain.setValueAtTime(gain, now + delay);
  g.gain.exponentialRampToValueAtTime(0.001, now + delay + dur);

  o.connect(g);
  g.connect(dest());
  o.start(now + delay);
  o.stop(now + delay + dur + 0.04);
}

/**
 * Burst of filtered white noise.
 * @param {number} dur         seconds
 * @param {number} gain
 * @param {number} filterFreq  bandpass centre Hz
 * @param {number} delay       seconds from now
 */
function noise(dur, gain = 0.15, filterFreq = 1800, delay = 0) {
  const c = ctx();
  const now = c.currentTime;
  const sampleRate = c.sampleRate;
  const len = Math.ceil(sampleRate * dur);
  const buf = c.createBuffer(1, len, sampleRate);
  const data = buf.getChannelData(0);
  for (let i = 0; i < len; i++) data[i] = Math.random() * 2 - 1;

  const src = c.createBufferSource();
  src.buffer = buf;

  const filter = c.createBiquadFilter();
  filter.type = "bandpass";
  filter.frequency.value = filterFreq;
  filter.Q.value = 1.4;

  const g = c.createGain();
  g.gain.setValueAtTime(gain, now + delay);
  g.gain.exponentialRampToValueAtTime(0.001, now + delay + dur);

  src.connect(filter);
  filter.connect(g);
  g.connect(dest());
  src.start(now + delay);
  src.stop(now + delay + dur + 0.02);
}

// ── Sound definitions ─────────────────────────────────────────────────────────

function sndCardPlay() {
  noise(0.09, 0.11, 5000, 0);
  osc("sine", 580, 340, 0, 0.12, 0.07);
}

function sndAttack() {
  noise(0.13, 0.22, 900, 0);
  osc("sawtooth", 200, 70, 0, 0.16, 0.14);
  osc("square",   380, 120, 0, 0.10, 0.06);
}

function sndBlock() {
  osc("triangle", 340, 290, 0,    0.20, 0.18);
  osc("square",   680, 640, 0,    0.12, 0.07);
  osc("sine",     900, 860, 0.04, 0.10, 0.05);
}

function sndHeal() {
  osc("sine", 523, null, 0,    0.20, 0.13);
  osc("sine", 659, null, 0.09, 0.22, 0.11);
  osc("sine", 784, null, 0.18, 0.18, 0.09);
}

function sndBuff() {
  // Bright ascending triad
  osc("sine", 440, null, 0,    0.16, 0.12);
  osc("sine", 554, null, 0.07, 0.16, 0.11);
  osc("sine", 660, null, 0.14, 0.18, 0.11);
  osc("sine", 880, null, 0.21, 0.14, 0.08);
}

function sndDebuff() {
  osc("sawtooth", 440, 340, 0,    0.16, 0.13);
  osc("sawtooth", 320, 220, 0.09, 0.18, 0.12);
  osc("sawtooth", 200, 120, 0.18, 0.16, 0.09);
}

function sndEnemyAttack() {
  osc("sawtooth", 110, 55, 0,    0.26, 0.24);
  noise(0.18, 0.20, 420, 0);
  osc("square",   220, 90, 0.04, 0.14, 0.10);
}

function sndVictory() {
  [523, 659, 784, 1047].forEach((f, i) =>
    osc("sine", f, null, i * 0.13, 0.32, 0.13)
  );
}

function sndDefeat() {
  [392, 349, 294, 220].forEach((f, i) =>
    osc("sawtooth", f, f * 0.88, i * 0.15, 0.38, 0.12)
  );
}

// ── Module state (survives re-renders) ────────────────────────────────────────

let _enabled = true;

/** Public SFX control object */
export const SFX = {
  get enabled() { return _enabled; },
  enable()  { _enabled = true;  },
  disable() { _enabled = false; },
  toggle()  { _enabled = !_enabled; },
  /** 0.0 – 1.0 master volume */
  setVolume(v) {
    if (_master) _master.gain.value = Math.max(0, Math.min(1, v));
  },
};

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Play a named sound effect.
 * Safe to call even if Web Audio is unavailable — errors are silently caught.
 *
 * @param {"cardPlay"|"attack"|"block"|"heal"|"buff"|"debuff"|"enemyAttack"|"victory"|"defeat"} type
 */
export function playSfx(type) {
  if (!_enabled) return;
  if (!window.AudioContext && !window.webkitAudioContext) return;
  try {
    switch (type) {
      case "cardPlay":    sndCardPlay();    break;
      case "attack":      sndAttack();      break;
      case "block":       sndBlock();       break;
      case "heal":        sndHeal();        break;
      case "buff":        sndBuff();        break;
      case "debuff":      sndDebuff();      break;
      case "enemyAttack": sndEnemyAttack(); break;
      case "victory":     sndVictory();     break;
      case "defeat":      sndDefeat();      break;
      default: break;
    }
  } catch (err) {
    // Audio context may be blocked in some environments — never crash the game
    console.warn("[sfx] Audio error:", err);
  }
}
