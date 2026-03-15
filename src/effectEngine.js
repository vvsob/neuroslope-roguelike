import { CARD_LIBRARY } from "./data/cards.js";
import { RELIC_LIBRARY } from "./data/relics.js";

export function hasKeyword(definition, keyword) {
  return definition.keywords?.includes(keyword) ?? false;
}

export function triggerRelicEvent(state, trigger, context = {}) {
  for (const relicId of state.player.relics) {
    const relic = RELIC_LIBRARY[relicId];
    if (!relic) {
      continue;
    }

    runBehaviorSet(state, relic.behaviors, trigger, {
      ...context,
      owner: "player",
      source: relic,
      sourceType: "relic",
    });
  }
}

export function triggerCardEvent(state, card, trigger, context = {}) {
  runBehaviorSet(state, card.behaviors, trigger, {
    ...context,
    owner: "player",
    source: card,
    sourceType: "card",
    card,
  });
}

function runBehaviorSet(state, behaviors = [], trigger, context) {
  for (const behavior of behaviors) {
    if (behavior.trigger !== trigger) {
      continue;
    }

    executeEffects(state, behavior.effects ?? [], context);
  }
}

export function executeEffects(state, effects = [], context = {}) {
  for (const effect of effects) {
    executeEffect(state, effect, context);
  }
}

function executeEffect(state, effect, context) {
  if (!effect?.type) {
    return;
  }

  if (effect.type === "repeat") {
    const times = resolveNumericValue(effect.times, state, context);
    for (let index = 0; index < times; index += 1) {
      executeEffects(state, effect.effects ?? [], { ...context, repeatIndex: index });
    }
    return;
  }

  if (effect.type === "condition") {
    const passed = evaluateCondition(state, effect.condition, context);
    executeEffects(state, passed ? effect.effects : effect.elseEffects, context);
    return;
  }

  if (effect.type === "log") {
    state.log.unshift(interpolateText(effect.text ?? "", state, context));
    return;
  }

  if (effect.type === "drawCards") {
    context.drawCards?.(state, resolveNumericValue(effect.amount, state, context));
    return;
  }

  if (effect.type === "gainEnergy") {
    state.player.energy += resolveNumericValue(effect.amount, state, context);
    return;
  }

  if (effect.type === "heal") {
    const targets = resolveTargetUnits(state, effect.target, context);
    if (targets.length === 0) {
      return;
    }
    for (const target of targets) {
      target.hp = Math.min(target.maxHp, target.hp + resolveNumericValue(effect.amount, state, context));
    }
    return;
  }

  if (effect.type === "modifyStat") {
    const targets = resolveTargetUnits(state, effect.target, context);
    if (targets.length === 0) {
      return;
    }
    const amount = resolveNumericValue(effect.amount, state, context);
    for (const target of targets) {
      target[effect.stat] = (target[effect.stat] ?? 0) + amount;
    }
    return;
  }

  if (effect.type === "damage") {
    const targets = resolveTargetUnits(state, effect.target, context);
    if (targets.length === 0) {
      return;
    }
    const attacker = resolveTargetUnit(state, effect.sourceTarget ?? "self", context);
    let amount = resolveNumericValue(effect.amount, state, context);
    for (const target of targets) {
      let resolvedAmount = amount;
      if (effect.useCombatModifiers && attacker) {
        resolvedAmount = calculateDamageWithModifiers({
          amount,
          attacker,
          defender: target,
        });
      }
      context.absorbDamage?.(target, resolvedAmount);
    }
    return;
  }

  if (effect.type === "addCard") {
    const zone = effect.zone ?? "discardPile";
    const amount = resolveNumericValue(effect.amount ?? 1, state, context);
    for (let index = 0; index < amount; index += 1) {
      state.player[zone].push(effect.cardId);
    }
    return;
  }

  // ── Extended effect primitives ──────────────────────────────────────────────

  // multiHit: deal damage N times, each hit optionally escalated
  // {"type":"multiHit","hits":3,"amount":5,"escalate":1.5,"useCombatModifiers":true}
  if (effect.type === "multiHit") {
    const targets = resolveTargetUnits(state, effect.target ?? "opponent", context);
    if (targets.length === 0) return;
    const attacker = resolveTargetUnit(state, effect.sourceTarget ?? "self", context);
    const hits = resolveNumericValue(effect.hits ?? 2, state, context);
    const escalate = typeof effect.escalate === "number" ? effect.escalate : 1;
    let amount = resolveNumericValue(effect.amount, state, context);
    for (let i = 0; i < hits; i++) {
      const dmg = effect.useCombatModifiers && attacker
        ? calculateDamageWithModifiers({ amount: Math.floor(amount), attacker, defender: targets[0] })
        : Math.floor(amount);
      for (const target of targets) {
        context.absorbDamage?.(target, dmg);
      }
      amount *= escalate;
    }
    return;
  }

  // splitDamage: divide total damage evenly across all alive enemies
  // {"type":"splitDamage","amount":18,"useCombatModifiers":true}
  if (effect.type === "splitDamage") {
    const enemies = getAliveEnemies(state);
    if (enemies.length === 0) return;
    const attacker = resolveTargetUnit(state, "self", context);
    const total = resolveNumericValue(effect.amount, state, context);
    const perTarget = Math.max(1, Math.floor(total / enemies.length));
    for (const target of enemies) {
      const dmg = effect.useCombatModifiers && attacker
        ? calculateDamageWithModifiers({ amount: perTarget, attacker, defender: target })
        : perTarget;
      context.absorbDamage?.(target, dmg);
    }
    return;
  }

  // lifesteal: deal damage and heal self for a fraction of damage dealt
  // {"type":"lifesteal","amount":10,"steal":0.5,"useCombatModifiers":true}
  if (effect.type === "lifesteal") {
    const targets = resolveTargetUnits(state, effect.target ?? "opponent", context);
    if (targets.length === 0) return;
    const attacker = resolveTargetUnit(state, "self", context);
    let baseAmount = resolveNumericValue(effect.amount, state, context);
    let totalDealt = 0;
    for (const target of targets) {
      const dmg = effect.useCombatModifiers && attacker
        ? calculateDamageWithModifiers({ amount: baseAmount, attacker, defender: target })
        : baseAmount;
      const hpBefore = target.hp;
      context.absorbDamage?.(target, dmg);
      totalDealt += hpBefore - target.hp;
    }
    const healAmount = Math.floor(totalDealt * (effect.steal ?? 0.5));
    if (healAmount > 0) {
      state.player.hp = Math.min(state.player.maxHp, state.player.hp + healAmount);
    }
    return;
  }

  // execute: instantly kill target if hp < threshold (flat or percent)
  // {"type":"execute","threshold":15} or {"type":"execute","thresholdPercent":20}
  if (effect.type === "execute") {
    const targets = resolveTargetUnits(state, effect.target ?? "opponent", context);
    for (const target of targets) {
      const threshold = effect.thresholdPercent != null
        ? Math.floor(target.maxHp * effect.thresholdPercent / 100)
        : resolveNumericValue(effect.threshold ?? 0, state, context);
      if (target.hp <= threshold) {
        target.hp = 0;
      }
    }
    return;
  }

  // echo: re-apply the onPlay effects of the last played card (stored in context)
  // {"type":"echo"}
  if (effect.type === "echo") {
    const lastCard = context.lastPlayedCard;
    if (!lastCard) return;
    for (const behavior of lastCard.behaviors ?? []) {
      if (behavior.trigger === "onPlay") {
        executeEffects(state, behavior.effects ?? [], { ...context, lastPlayedCard: null });
      }
    }
    return;
  }

  // exhaustRandom: exhaust N random cards from hand
  // {"type":"exhaustRandom","amount":1}
  if (effect.type === "exhaustRandom") {
    const amount = resolveNumericValue(effect.amount ?? 1, state, context);
    for (let i = 0; i < amount; i++) {
      if (state.player.hand.length === 0) break;
      const idx = Math.floor(Math.random() * state.player.hand.length);
      const [cardId] = state.player.hand.splice(idx, 1);
      state.player.exhaustPile.push(cardId);
    }
    return;
  }

  // gainBlock: alias so LLM can write it more naturally
  // {"type":"gainBlock","amount":8}
  if (effect.type === "gainBlock") {
    const targets = resolveTargetUnits(state, effect.target ?? "self", context);
    const amount = resolveNumericValue(effect.amount, state, context);
    for (const t of targets) {
      t.block = (t.block ?? 0) + amount;
    }
    return;
  }
}

function evaluateCondition(state, condition, context) {
  if (!condition) {
    return true;
  }

  const target = resolveTargetUnit(state, condition.target, context);
  const current = target?.[condition.stat] ?? 0;

  // valuePercent: compare stat as % of maxHp (or maxEnergy)
  let value;
  if (condition.valuePercent != null) {
    const maxStat = condition.stat === "energy"
      ? (target?.maxEnergy ?? 3)
      : (target?.maxHp ?? 1);
    value = Math.floor(maxStat * condition.valuePercent / 100);
  } else {
    value = resolveNumericValue(condition.value, state, context);
  }

  if (condition.operator === "gt") return current > value;
  if (condition.operator === "gte") return current >= value;
  if (condition.operator === "lt") return current < value;
  if (condition.operator === "lte") return current <= value;
  if (condition.operator === "eq") return current === value;
  return false;
}

function resolveNumericValue(value, state, context) {
  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "string") {
    if (value === "cardsInHand") return state.player.hand.length;
    if (value === "playerStrength") return state.player.strength ?? 0;
    if (value === "playerMissingHp") return state.player.maxHp - state.player.hp;
    if (value === "playerHpPercent") return Math.floor((state.player.hp / state.player.maxHp) * 100);
    if (value === "enemyCount") return getAliveEnemies(state).length;
    if (value === "deckSize") return state.player.deck?.length ?? 0;
    if (value === "discardSize") return state.player.discardPile?.length ?? 0;
    // "targetMissingHp": missing HP of the selected/primary enemy
    if (value === "targetMissingHp") {
      const enemy = getPrimaryEnemy(state, context ?? {});
      return enemy ? enemy.maxHp - enemy.hp : 0;
    }
  }

  return 0;
}

function resolveTargetUnits(state, target, context) {
  if (target === "allEnemies") {
    return getAliveEnemies(state);
  }

  const unit = resolveTargetUnit(state, target, context);
  return unit ? [unit] : [];
}

function resolveTargetUnit(state, target, context) {
  if (target === "player") {
    return state.player;
  }
  if (target === "enemy") {
    return getPrimaryEnemy(state, context);
  }
  if (target === "self" || target === "owner") {
    return context.owner === "enemy" ? getPrimaryEnemy(state, context) : state.player;
  }
  if (target === "opponent") {
    return context.owner === "enemy" ? state.player : getPrimaryEnemy(state, context);
  }
  return null;
}

function getPrimaryEnemy(state, context) {
  if (context.targetEnemyId) {
    return getAliveEnemies(state).find((enemy) => enemy.id === context.targetEnemyId) ?? getAliveEnemies(state)[0] ?? null;
  }
  return getAliveEnemies(state)[0] ?? null;
}

function getAliveEnemies(state) {
  return (state.enemies ?? []).filter((enemy) => enemy.hp > 0);
}

function calculateDamageWithModifiers({ amount, attacker, defender }) {
  let total = amount + (attacker.strength ?? 0);
  if ((attacker.weak ?? 0) > 0) {
    total = Math.floor(total * 0.75);
  }
  if ((defender.vulnerable ?? 0) > 0) {
    total = Math.floor(total * 1.5);
  }
  return Math.max(0, total);
}

function interpolateText(text, state, context) {
  return text
    .replaceAll("{playerName}", state.player.name)
    .replaceAll("{enemyName}", getAliveEnemies(state)[0]?.name ?? "enemy")
    .replaceAll("{sourceName}", context.source?.name ?? "Effect")
    .replaceAll("{cardName}", context.card?.name ?? "");
}

export function describeRelic(relicId) {
  return RELIC_LIBRARY[relicId];
}

export function describeCard(cardId) {
  return CARD_LIBRARY[cardId];
}
