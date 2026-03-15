# Neuroslope Spire Prototype

A lightweight Slay the Spire style prototype built with plain JavaScript and browser UI.

## Features

- Branching run map with hallway fights, elites, campfires, treasure, and a boss
- Card combat with energy, draw pile, discard pile, exhaust-style turn flow, and enemy intents
- Persistent run state across battles
- Post-combat card rewards and campfire healing
- No build step required

## Run it

Because browsers block ES modules from `file://` URLs, serve the project with a tiny local web server from the repo root.

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## How to play

- Click a map node to travel
- Play cards from your hand during combat
- Click `End Turn` to let the enemy act
- After combat, choose one reward card to add it to your deck
- Reach the final boss and survive
