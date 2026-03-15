# Neuroslope Spire Prototype

A lightweight Slay the Spire style prototype built with plain JavaScript and browser UI.

## Features

- Branching run map with hallway fights, elites, campfires, treasure, and a boss
- Card combat with energy, draw pile, discard pile, exhaust-style turn flow, and enemy intents
- Persistent run state across battles
- Post-combat card rewards and campfire healing
- Per-floor enemy and weapon art slots with a batch image generation script
- No build step required

## Run it

Because browsers block ES modules from `file://` URLs, serve the project with a tiny local web server from the repo root.

```bash
python3 -m http.server 4173
```

Then open `http://localhost:4173`.

## Generate level art

The game looks for generated images in `src/assets/generated/`. Use the Python script to create enemy and weapon art for all combat themes:

```bash
HF_TOKEN=your_token_here python3 src/gen_image.py
```

Generate only one asset family or one floor if needed:

```bash
HF_TOKEN=your_token_here python3 src/gen_image.py --kind weapon
HF_TOKEN=your_token_here python3 src/gen_image.py --level n5 --kind enemy
```

If a generated image is missing, the UI falls back to the placeholder SVGs.

## How to play

- Click a map node to travel
- Play cards from your hand during combat
- Click `End Turn` to let the enemy act
- After combat, choose one reward card to add it to your deck
- Reach the final boss and survive
