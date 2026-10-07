# Retro MMORPG HUD

Implemented 2026-10-05 in `client/ui/hud.gd` and `client/ui/retro_frame.gd`.

- Top left: character name, level medallion, actual selected model portrait, green health and blue mana. Player stats are exported from `client/player/player.gd` (defaults: level 1, 100/100 health and mana); combat progression is not implemented in this exploration project.
- Top right: circular north-up map of the actual world, rotating player arrow, cardinal directions and persistent current zone name. Region entry is also recorded in Game chat.
- Bottom left: switchable All, Game, Players and Combat channels, scrollable history (200 entries), and text entry. System/weather events feed Game; drawing/sheathing the sword feeds Combat. `add_chat_message(channel, text, sender)` accepts future events. Player messages emit `chat_submitted(text)` and echo locally. There is no network transport yet.
- Bottom right: supplied stone menu artwork with six hit targets (spellbook, journal, inventory, equipment, players and settings), hover/focus highlighting and tooltips. Information panels describe the current exploration systems; Every icon, including Settings, opens the same fixed-size rectangle directly above the dock. The panel matches the dock width and touches its top edge; selecting another icon swaps its contents. Clicking the selected icon or the close button collapses it. Settings controls scroll inside the panel; Escape still provides the full pause menu. Two reference slots remain empty.

Enter opens chat and sends text. I releases/recaptures the cursor. Escape leaves chat/interface mode; otherwise it opens the pause menu. Movement and gameplay shortcuts are blocked while entering text. The pause-menu overlay blocks clicks to the HUD below. F1 retains HUD visibility control.

The four corners adapt to window size and aspect ratio; UI scales down below 1152×700 logical pixels. The layout was checked at 800×600, 1280×720, 1600×900 and 2560×1080.

## Verification

Run `Godot --headless --path . --script res://tools/verify_hud.gd` for integration assertions covering all channel filters, text handling, input capture, menus, zones, stats, bounded history and four viewport sizes. Results are saved in `checks.log`.

Run `Godot --path . --script res://tools/capture_hud.gd` for real-renderer mouse-hit checks and the screenshots here. It restores the original character selection after verifying the female portrait. `preview.png` shows the final layout, `chat-and-inventory.png` shows interactive panels, `settings.png` shows the attached Settings panel, and `compact-female.png` checks the smaller layout and alternate model. The Vulkan visual run completed without script or renderer errors.

Original HUD and player scripts are retained in `before/` because this workspace has no Git repository.

