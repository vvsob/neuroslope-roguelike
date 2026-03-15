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
  }
}

function evaluateCondition(state, condition, context) {
  if (!condition) {
    return true;
  }

  const target = resolveTargetUnit(state, condition.target, context);
  const current = target?.[condition.stat];
  const value = resolveNumericValue(condition.value, state, context);

  if (condition.operator === "gt") {
    return current > value;
  }
  if (condition.operator === "gte") {
    return current >= value;
  }
  if (condition.operator === "lt") {
    return current < value;
  }
  if (condition.operator === "lte") {
    return current <= value;
  }
  if (condition.operator === "eq") {
    return current === value;
  }
  return false;
}

function resolveNumericValue(value, state, context) {
  if (typeof value === "number") {
    return value;
  }

  if (typeof value === "string") {
    if (value === "cardsInHand") {
      return state.player.hand.length;
    }
    if (value === "playerStrength") {
      return state.player.strength;
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
