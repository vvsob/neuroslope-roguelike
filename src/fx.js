/**
 * fx.js — Visual effects layer for card play and combat animations.
 *
 * Design notes for future merges:
 *  - All effects are appended to a persistent fixed overlay (#spire-fx-layer)
 *    that lives outside the game root, so innerHTML re-renders never destroy
 *    in-flight animations.
 *  - `triggerFx(events)` is the only export the game needs to call.
 *    It defers one animation frame so the renderer has already settled.
 *  - Target strings are multi-enemy-ready:
 *      "player"    → .player-side
 *      "enemy"     → .enemy-side  (single-enemy shorthand, current)
 *      "enemy:0"   → [data-combatant="enemy-0"]
 *      "enemy:1"   → [data-combatant="enemy-1"]
 *    renderBattle() already stamps data-combatant on each combatant div.
 *
 * Event object shape:
 *   { type: FxType, target: string, value?: number, label?: string }
 *
 * FxType catalogue (extend freely):
 *   "damage"   – red flash + floating negative number
 *   "block"    – blue shield pulse + ring expand + number
 *   "heal"     – green glow + positive number
 *   "buff"     – golden upward particles + optional label
 *   "debuff"   – purple downward particles + optional label
 *   -- reserved for future use (no-op today) --
 *   "poison"   – green dot particles
 *   "burn"     – orange fire particles
 *   "freeze"   – blue crystal shatter
 *   "draw"     – card shimmer
 *   "exhaust"  – grey dissolve
 */

// ── Layer & utility helpers ───────────────────────────────────────────────────

const LAYER_ID = "spire-fx-layer";
const STYLE_ID = "spire-fx-styles";

function getLayer() {
  let el = document.getElementById(LAYER_ID);
  if (!el) {
    el = document.createElement("div");
    el.id = LAYER_ID;
    el.style.cssText =
      "position:fixed;inset:0;pointer-events:none;z-index:9999;overflow:hidden;";
    document.body.appendChild(el);
  }
  return el;
}

function resolveTarget(selector) {
  if (selector instanceof HTMLElement) return selector;
  return document.querySelector(selector);
}

/** Rect centre in viewport coords */
function centre(el) {
  const r = el.getBoundingClientRect();
  return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
}

function make(css, html = "") {
  const el = document.createElement("div");
  el.style.cssText = css;
  el.innerHTML = html;
  return el;
}

function after(ms, fn) {
  return setTimeout(fn, ms);
}

// ── Enemy lunge animation ─────────────────────────────────────────────────────

/**
 * Briefly lunges the enemy sprite toward the player and snaps back.
 * Used before each enemy damage hit to telegraph the attack.
 */
function fxEnemyLunge(enemyEl) {
  if (!enemyEl) return;
  // Lunge left (toward player) then snap back
  enemyEl.style.transition = "transform 120ms ease-out";
  enemyEl.style.transform = "translateX(-28px) scaleX(0.92)";
  after(120, () => {
    enemyEl.style.transition = "transform 200ms cubic-bezier(0.22,1,0.36,1)";
    enemyEl.style.transform = "";
    after(210, () => {
      enemyEl.style.transition = "";
    });
  });
}

/**
 * Briefly shakes the enemy sprite (used for buff/debuff on enemy).
 */
function fxEnemyShake(enemyEl) {
  if (!enemyEl) return;
  enemyEl.style.transition = "transform 80ms ease-in-out";
  enemyEl.style.transform = "translateX(8px)";
  after(80, () => {
    enemyEl.style.transform = "translateX(-8px)";
    after(80, () => {
      enemyEl.style.transform = "";
      enemyEl.style.transition = "";
    });
  });
}

// ── Individual effect painters ────────────────────────────────────────────────

function fxDamage(targetEl, value) {
  const layer = getLayer();
  const { x, y } = centre(targetEl);

  const flash = make(
    `position:fixed;left:${x - 64}px;top:${y - 90}px;width:128px;height:180px;
     border-radius:20px;background:rgba(243,90,70,0.38);
     animation:sfx-flash 300ms ease-out forwards;`
  );

  const num = make(
    `position:fixed;left:${x}px;top:${y - 60}px;transform:translateX(-50%);
     color:#ff7055;font-size:2.1rem;font-weight:700;font-family:Georgia,serif;
     text-shadow:0 2px 10px rgba(0,0,0,0.75);white-space:nowrap;
     animation:sfx-float-up 750ms cubic-bezier(0.22,1,0.36,1) forwards;`,
    `−${value}`
  );

  // Shockwave ring
  const ring = make(
    `position:fixed;left:${x - 36}px;top:${y - 36}px;width:72px;height:72px;
     border-radius:999px;border:3px solid rgba(255,110,80,0.6);
     animation:sfx-ring 480ms ease-out forwards;`
  );

  layer.append(flash, num, ring);
  after(820, () => { flash.remove(); num.remove(); ring.remove(); });
}

function fxBlock(targetEl, value) {
  const layer = getLayer();
  const { x, y } = centre(targetEl);

  const flash = make(
    `position:fixed;left:${x - 64}px;top:${y - 90}px;width:128px;height:180px;
     border-radius:20px;background:rgba(80,150,255,0.28);
     animation:sfx-flash 360ms ease-out forwards;`
  );

  const num = make(
    `position:fixed;left:${x}px;top:${y - 60}px;transform:translateX(-50%);
     color:#90c8ff;font-size:1.7rem;font-weight:700;font-family:Georgia,serif;
     text-shadow:0 2px 10px rgba(0,0,0,0.75);white-space:nowrap;
     animation:sfx-float-up 750ms cubic-bezier(0.22,1,0.36,1) forwards;`,
    `🛡 +${value}`
  );

  const ring = make(
    `position:fixed;left:${x - 36}px;top:${y - 36}px;width:72px;height:72px;
     border-radius:999px;border:3px solid rgba(110,170,255,0.7);
     animation:sfx-ring 550ms ease-out forwards;`
  );

  layer.append(flash, num, ring);
  after(820, () => { flash.remove(); num.remove(); ring.remove(); });
}

function fxHeal(targetEl, value) {
  const layer = getLayer();
  const { x, y } = centre(targetEl);

  const flash = make(
    `position:fixed;left:${x - 64}px;top:${y - 90}px;width:128px;height:180px;
     border-radius:20px;background:rgba(70,210,120,0.22);
     animation:sfx-flash 420ms ease-out forwards;`
  );

  const num = make(
    `position:fixed;left:${x}px;top:${y - 60}px;transform:translateX(-50%);
     color:#7de8a8;font-size:1.7rem;font-weight:700;font-family:Georgia,serif;
     text-shadow:0 2px 10px rgba(0,0,0,0.75);white-space:nowrap;
     animation:sfx-float-up 800ms cubic-bezier(0.22,1,0.36,1) forwards;`,
    `+${value} HP`
  );

  layer.append(flash, num);
  after(880, () => { flash.remove(); num.remove(); });
}

function fxBuff(targetEl, label) {
  const layer = getLayer();
  const { x, y } = centre(targetEl);

  for (let i = 0; i < 7; i++) {
    const dx = (Math.random() - 0.5) * 70;
    const dy = -(50 + Math.random() * 50);
    const p = make(
      `position:fixed;left:${x + (Math.random() - 0.5) * 36}px;top:${y}px;
       width:8px;height:8px;border-radius:999px;
       background:${i % 2 === 0 ? "#e69a42" : "#ffd080"};
       --dx:${dx}px;--dy:${dy}px;
       animation:sfx-particle-up 640ms ease-out ${i * 45}ms forwards;`
    );
    layer.appendChild(p);
    after(700 + i * 45, () => p.remove());
  }

  if (label) {
    const lbl = make(
      `position:fixed;left:${x}px;top:${y - 80}px;transform:translateX(-50%);
       color:#ffd080;font-size:1.05rem;font-weight:700;font-family:Georgia,serif;
       text-shadow:0 2px 10px rgba(0,0,0,0.85);white-space:nowrap;
       animation:sfx-float-up 900ms cubic-bezier(0.22,1,0.36,1) forwards;`,
      label
    );
    layer.appendChild(lbl);
    after(980, () => lbl.remove());
  }
}

function fxDebuff(targetEl, label) {
  const layer = getLayer();
  const { x, y } = centre(targetEl);

  const flash = make(
    `position:fixed;left:${x - 64}px;top:${y - 90}px;width:128px;height:180px;
     border-radius:20px;background:rgba(160,60,200,0.20);
     animation:sfx-flash 380ms ease-out forwards;`
  );
  layer.appendChild(flash);
  after(500, () => flash.remove());

  for (let i = 0; i < 6; i++) {
    const dx = (Math.random() - 0.5) * 50;
    const dy = 35 + Math.random() * 35;
    const p = make(
      `position:fixed;left:${x + (Math.random() - 0.5) * 36}px;top:${y}px;
       width:7px;height:7px;border-radius:999px;
       background:${i % 2 === 0 ? "#c060e8" : "#7040a0"};
       --dx:${dx}px;--dy:${dy}px;
       animation:sfx-particle-down 620ms ease-out ${i * 50}ms forwards;`
    );
    layer.appendChild(p);
    after(720 + i * 50, () => p.remove());
  }

  if (label) {
    const lbl = make(
      `position:fixed;left:${x}px;top:${y - 60}px;transform:translateX(-50%);
       color:#d080f8;font-size:1.05rem;font-weight:700;font-family:Georgia,serif;
       text-shadow:0 2px 10px rgba(0,0,0,0.85);white-space:nowrap;
       animation:sfx-float-down 850ms cubic-bezier(0.22,1,0.36,1) forwards;`,
      label
    );
    layer.appendChild(lbl);
    after(930, () => lbl.remove());
  }
}

// ── CSS keyframes (injected once) ─────────────────────────────────────────────

const CSS = `
@keyframes sfx-flash {
  0%   { opacity: 1; }
  100% { opacity: 0; }
}
@keyframes sfx-float-up {
  0%   { opacity: 1; transform: translateX(-50%) translateY(0);    }
  100% { opacity: 0; transform: translateX(-50%) translateY(-58px); }
}
@keyframes sfx-float-down {
  0%   { opacity: 1; transform: translateX(-50%) translateY(0);   }
  100% { opacity: 0; transform: translateX(-50%) translateY(26px); }
}
@keyframes sfx-ring {
  0%   { transform: scale(1);   opacity: 0.85; }
  100% { transform: scale(2.6); opacity: 0;    }
}
@keyframes sfx-particle-up {
  0%   { opacity: 1; transform: translate(0, 0) scale(1); }
  100% { opacity: 0; transform: translate(var(--dx,0), var(--dy,-50px)) scale(0.25); }
}
@keyframes sfx-particle-down {
  0%   { opacity: 1; transform: translate(0, 0) scale(1); }
  100% { opacity: 0; transform: translate(var(--dx,0), var(--dy, 35px)) scale(0.25); }
}
`;

(function injectCss() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = CSS;
  document.head.appendChild(style);
})();

// ── Target selector builder (multi-enemy ready) ───────────────────────────────

/**
 * Converts a logical target string to a CSS selector.
 *
 * Current single-enemy shortcuts:
 *   "enemy"  → .enemy-side
 *   "player" → .player-side
 *
 * Multi-enemy pattern (add enemies with data-combatant="enemy-N"):
 *   "enemy:0" → [data-combatant="enemy-0"]
 *   "enemy:1" → [data-combatant="enemy-1"]
 *   "player:0" → [data-combatant="player-0"]  (for co-op future)
 */
function buildSelector(target) {
  if (target === "enemy")  return ".enemy-side";
  if (target === "player") return ".player-side";
  const m = target.match(/^(enemy|player):(\d+)$/);
  if (m) return `[data-combatant="${m[1]}-${m[2]}"]`;
  return target; // pass-through for raw selectors
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Fire a batch of visual effects.
 *
 * Enemy damage events play sequentially with a lunge animation before each hit.
 * Other events (player damage, block, buff, etc.) fire immediately in one rAF.
 *
 * Enemy-sourced damage is detected by target being "player" or "player:*".
 * Each sequential hit is separated by ENEMY_HIT_INTERVAL ms.
 *
 * @param {Array<{type:string, target:string, value?:number, label?:string}>} events
 */
const ENEMY_HIT_INTERVAL = 480; // ms between sequential enemy attacks

export function triggerFx(events) {
  if (!events || events.length === 0) return;

  // Split into sequential enemy hits vs instant effects
  const enemyHits = [];
  const instant = [];
  for (const ev of events) {
    const tgt = ev.target ?? "";
    const isEnemyAttack = ev.type === "damage" &&
      (tgt === "player" || tgt === "player:0" || /^player:\d+$/.test(tgt));
    if (isEnemyAttack) {
      enemyHits.push(ev);
    } else {
      instant.push(ev);
    }
  }

  // Fire instant effects (player's own attacks, blocks, buffs) right away
  if (instant.length > 0) {
    requestAnimationFrame(() => {
      for (const ev of instant) {
        _playEffect(ev);
      }
    });
  }

  // Fire enemy hits one-by-one with a lunge + delay
  if (enemyHits.length > 0) {
    enemyHits.forEach((ev, i) => {
      after(i * ENEMY_HIT_INTERVAL, () => {
        requestAnimationFrame(() => {
          // Lunge the enemy sprite that's attacking (if identifiable)
          // enemy:0 → [data-combatant="enemy-0"], fallback .enemy-side
          const enemySelector = _guessAttackingEnemySelector(ev);
          const enemyEl = resolveTarget(enemySelector);
          if (enemyEl) fxEnemyLunge(enemyEl);

          // Show hit on player ~100ms after lunge starts (impact frame)
          after(100, () => {
            const targetEl = resolveTarget(buildSelector(ev.target ?? "player"));
            if (targetEl) fxDamage(targetEl, ev.value ?? 0);
          });
        });
      });
    });
  }
}

/**
 * Try to find the enemy element that's doing the attacking.
 * If the event has no explicit enemy reference we fall back to .enemy-side.
 */
function _guessAttackingEnemySelector(ev) {
  // Events may carry a sourceTarget like "enemy:0" in future; for now use first enemy
  return ".enemy-side, [data-combatant^='enemy-']";
}

function _playEffect(ev) {
  const el = resolveTarget(buildSelector(ev.target ?? "enemy"));
  if (!el) return;
  switch (ev.type) {
    case "damage": fxDamage(el, ev.value ?? 0); break;
    case "block":  fxBlock(el,  ev.value ?? 0); break;
    case "heal":   fxHeal(el,   ev.value ?? 0); break;
    case "buff":   fxBuff(el,   ev.label ?? ""); fxEnemyShake(resolveTarget(".enemy-side")); break;
    case "debuff": fxDebuff(el, ev.label ?? ""); break;
    default: break;
  }
}
