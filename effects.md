# Effects Data System

Cards and relics are authored as data, not custom logic.

## Files

- `src/data/cards.js`
- `src/data/relics.js`
- `src/effectEngine.js`

## Card Definition

```js
{
  id: "strike",
  name: "Strike",
  cost: 1,
  type: "Attack",
  rarity: "Starter",
  description: "Deal 6 damage.",
  keywords: ["exhaust"],
  behaviors: [
    {
      trigger: "onPlay",
      effects: [
        { type: "damage", target: "opponent", amount: 6, useCombatModifiers: true },
        { type: "log", text: "{playerName} slashes for 6." }
      ]
    }
  ]
}
```

## Relic Definition

```js
{
  id: "battle_battery",
  name: "Battle Battery",
  icon: "⚡",
  description: "At the start of each battle, gain 1 Energy.",
  behaviors: [
    {
      trigger: "onBattleStart",
      effects: [
        { type: "gainEnergy", amount: 1 },
        { type: "log", text: "{sourceName} crackles. Gain 1 Energy." }
      ]
    }
  ]
}
```

## Supported Triggers

- `onPlay`
- `onDraw`
- `onBattleStart`
- `onBattleEnd`
- `onTurnStart`
- `onTurnEnd`
- `onCardPlayed`
- `onCardDrawn`

## Supported Effect Types

- `damage`
- `modifyStat`
- `heal`
- `drawCards`
- `gainEnergy`
- `addCard`
- `log`
- `repeat`
- `condition`

## Targets

- `self`
- `owner`
- `opponent`
- `player`
- `enemy`
- `allEnemies`

## Common Stats

- `block`
- `strength`
- `weak`
- `vulnerable`
- `metallicize`

## Notes

- A new custom card usually only needs a new object in `src/data/cards.js`.
- A new custom relic usually only needs a new object in `src/data/relics.js`.
- If you need a brand new kind of effect, add it once in `src/effectEngine.js`, then future content can use it with data only.
- In multi-enemy fights, `opponent` and `enemy` resolve to the currently selected enemy. If no enemy is selected, they resolve to the first living enemy.
- `allEnemies` applies the same effect to every living enemy in the current battle.
