# Scene-centered composition contract

Use this contract for a small conceptual image that must communicate a topic quickly after being placed in a figure, circular panel, or central hole.

## Required storyboard fields

Record these fields in `brief.json` and carry them into the image prompt:

- `composition_mode`: `scene_centered`, `icon_composite`, or `process_chain`.
- `visual_anchor`: the single subject that should dominate recognition.
- `environment`: the smallest setting that explains where the subject is and what it is doing.
- `state_cue`: one visible posture, symptom, or state cue supported by the brief.
- `integrated_secondary_cue`: one compact scientific cue embedded in the subject or environment.
- `relation_semantics`: associative, causal, predictive, descriptive, or another explicitly supported relation.
- `avoid_list`: detached icons, unlisted mechanisms, labels, values, or anatomy that the evidence does not support.

For a topic asset, use `scene_centered` unless the user explicitly requests a process or a collection of isolated objects. The anchor should occupy most of the visual attention. The environment should make the behavior or context legible without becoming a second subject; retain the objects necessary to establish the requested behavior, while removing decorative clutter. One coherent scene may include a person, desk, screen, and office chair. Do not reduce a desk-screen activity to an armchair pose merely to simplify the composition. The secondary cue should be local to the anchor: a small chest-area glow, embedded inset, or contextual detail is preferable to a separate heart, vessel, or icon floating beside the person.

For compact scenes, keep the setting quiet and the subject expressive. Natural skin tones, a clear face, graceful curves, tonal depth, and tasteful cartoon or sculptural rendering can improve appeal. Choose these features intentionally instead of treating flatness, desaturation, or a blank face as scientific rigor. Simplify redundant props before removing the subject's character. Inspect the result under the separate [aesthetic review contract](aesthetic-review.md).

## Exploration versus selected-base refinement

Choose from the user’s intent before generating. `explore` compares design directions with a stated visible difference and purpose. A mirrored view, demographic change, or small recolor alone is a detail variant, not a new design direction. Keep the action and science fixed while varying a meaningful composition, silhouette, or rendering choice. Review actual images; a diverse-looking prompt matrix does not prove output diversity.

When the user selects a base, use `refine`: preserve the approved composition and identity, send the actual base as an edit reference, and describe observable changes to named details. A second image can guide specified finish or detail without replacing the base composition. Save the base hash and compare before/after crops at useful magnification plus the final figure size. A higher overall aesthetic score cannot replace evidence that those edits improved.

## Required behavior

If the user specifies an activity, lock `brief.action_contract` before creating variations:

- `action`: the visible activity and posture.
- `attention_target`: where the subject must look or direct attention; optional when irrelevant.
- `required_context`: the minimal objects or setting that establish the activity.

Keep this contract fixed across candidate viewpoints and styles. A different camera angle must still show the action and attention target. The aesthetic reviewer adds `required_behavior_match` as a required gate whenever this contract is present. Empty contracts preserve existing static-object workflows.

## Prompt and review rules

The prompt must state that the composition is one coherent scene and must forbid a vertical stack or detached icon chain when `scene_centered` is selected. Do not add arrows unless the user requests them and the relation is supported. A symptom or risk cue is not a diagnosis. An observational or post-GWAS association must retain associative language in both the brief and the visual treatment.

Review the isolated PNG and the destination figure at two scales:

1. Around 200 px square, where the anchor and state cue should still be recognizable.
2. At the actual figure slot, where the scene must read as one unit and no secondary object should look accidentally detached.

The automated QA can record the contract, alpha, dimensions, and sidecars. Human review remains necessary for coherence, scientific interpretation, and absence of unintended anatomy or text.
