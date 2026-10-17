# Scenes

Each pattern has four scenes, on physical T1–T4. A scene holds absolute targets across audio tracks. All four scenes start enabled with no learned targets. Untouched empty scenes also default to enabled when loading existing projects. Scenes with learned targets retain their saved enabled state; explicit toggles and scene clears are saved. Disable a scene with FUNC+T before learning if you want to learn silently. An enabled scene applies while its T button is held; release returns to the current sequencer values, including parameter locks that changed during the hold.

| Gesture | Result |
| --- | --- |
| Hold T1–T4 and turn A–H on a supported sound page | Learn or edit targets |
| Hold FUNC before pressing T1–T4 | Toggle scene enabled state |
| Hold scene + press encoder A–H | Clear that parameter's scene lock on SRC, FLTR, AMP or LFO |
| Hold scene + PLAY | Clear and disable that scene |
| Hold scene + REC | Copy the complete scene |
| Hold destination scene + STOP | Replace it with the copied scene |

FUNC must already be held when T is pressed; pressing FUNC afterward does not toggle. The toggle press does not perform the scene. Only the first accepted scene hold owns editing/performance until release; other held scenes do not automatically take over. Pattern/project changes cancel the hold.

Scene LEDs show enabled green or disabled off. Learned locks use the native inverted parameter boxes while the scene is held. Disabled-scene learning leaves underlying sound data and native sequencer locks intact. Capture is limited to audio-track sound providers; global FX/master and MIDI-track scene targets are unsupported. Scene amount/interpolation and LEVEL amount control are unimplemented.

The clipboard includes enabled state and locks across audio tracks and survives pattern changes until restart. It holds a snapshot independent of the source scene. Paste before copy does nothing; copying an empty scene then pasting clears the destination. Scene transport gestures consume their press/repeat/release events. The scene clipboard is independent of the native pattern clipboard.

## Persistence

Targets and enabled state belong to each of 128 patterns. Full project operations, native pattern copy/paste/clear/undo, temporary saves/reloads and shutdown saves have integration hooks. A same-project background cache refresh preserves unsaved scene edits. FUNC+NO explicitly reloads the current pattern's scene row; a same-project full native reload is not a separately established whole-table rollback boundary.

Scene data lives in an instrument-local extension to native project slots. Stock Elektron Transfer project exports **do not include it**. Copying/exporting only native projects does not back up scenes.

Reads validate in staging before publication. A failed initial scene read leaves initialized RAM scenes usable, with persistence unavailable until a successful explicit native save/reload transaction can reconcile stored and edited rows. Background writes do not overwrite an unread checkpoint. Failed replacement by another project's scenes quarantines the old owner rather than applying its locks to the new project. RAM boundary corruption disables scenes.

Scene storage errors and guard failures retain their internal handling; they do not claim the NOTE/KEYBOARD LED. A working RAM scene with a continuing storage error may not survive restart.
