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
    const target = resolveTargetUnit(state, effect.target, context);
    if (!target) {
      return;
    }
    target.hp = Math.min(target.maxHp, target.hp + resolveNumericValue(effect.amount, state, context));
    return;
  }

  if (effect.type === "modifyStat") {
    const target = resolveTargetUnit(state, effect.target, context);
    if (!target) {
      return;
    }
    const amount = resolveNumericValue(effect.amount, state, context);
    target[effect.stat] = (target[effect.stat] ?? 0) + amount;
    return;
  }

  if (effect.type === "damage") {
    const target = resolveTargetUnit(state, effect.target, context);
    if (!target) {
      return;
    }
    const attacker = resolveTargetUnit(state, effect.sourceTarget ?? "self", context);
    let amount = resolveNumericValue(effect.amount, state, context);
    if (effect.useCombatModifiers && attacker) {
      amount = calculateDamageWithModifiers({
        amount,
        attacker,
        defender: target,
      });
    }
    context.absorbDamage?.(target, amount);
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

function resolveTargetUnit(state, target, context) {
  if (target === "player") {
    return state.player;
  }
  if (target === "enemy") {
    return state.enemy;
  }
  if (target === "self" || target === "owner") {
    return context.owner === "enemy" ? state.enemy : state.player;
  }
  if (target === "opponent") {
    return context.owner === "enemy" ? state.player : state.enemy;
  }
  return null;
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
    .replaceAll("{enemyName}", state.enemy?.name ?? "enemy")
    .replaceAll("{sourceName}", context.source?.name ?? "Effect")
    .replaceAll("{cardName}", context.card?.name ?? "");
}

export function describeRelic(relicId) {
  return RELIC_LIBRARY[relicId];
}

export function describeCard(cardId) {
  return CARD_LIBRARY[cardId];
}
