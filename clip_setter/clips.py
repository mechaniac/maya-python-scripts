"""Clip definitions for a 3rd-person s&box character controller.

Each clip is a dict with:
  - name:      FBX clip name (s&box naming: lowercase_snake_case)
  - frames:    frame count for the animation
  - loop:      True for looping locomotion, False for one-shot actions
  - category:  grouping for UI/generation purposes

The layout engine spaces clips sequentially on the timeline with
configurable buffer frames between them.
"""


# ── default clip set ──────────────────────────────────────────────

DEFAULT_CLIPS = [
    # Locomotion (looping)
    {'name': 'idle',            'frames': 1,  'loop': True,  'category': 'locomotion'},
    {'name': 'walk',            'frames': 30, 'loop': True,  'category': 'locomotion'},
    {'name': 'run',             'frames': 20, 'loop': True,  'category': 'locomotion'},
    {'name': 'strafe_left',     'frames': 30, 'loop': True,  'category': 'locomotion'},
    {'name': 'strafe_right',    'frames': 30, 'loop': True,  'category': 'locomotion'},
    {'name': 'crouch_idle',     'frames': 1,  'loop': True,  'category': 'locomotion'},
    {'name': 'crouch_walk',     'frames': 30, 'loop': True,  'category': 'locomotion'},
    # Actions (one-shot)
    {'name': 'jump',            'frames': 30, 'loop': False, 'category': 'action'},
    {'name': 'fall_idle',       'frames': 110, 'loop': True,  'category': 'action'},
    {'name': 'land_light',      'frames': 40, 'loop': False, 'category': 'action'},
]

DEFAULT_BUFFER = 100    # frames between clips (must exceed worst-case extended key overshoot)
DEFAULT_START = 100     # first clip starts at this frame (leave room for T-pose / rest at 0)


# ── layout engine ─────────────────────────────────────────────────

def layout_clips(clips=None, buffer=DEFAULT_BUFFER, start=DEFAULT_START):
    """Compute frame ranges for each clip.

    Returns a list of dicts, each with:
      name, frames, loop, category, start, end
    """
    if clips is None:
        clips = DEFAULT_CLIPS
    result = []
    frame = start
    for clip in clips:
        end = frame + clip['frames']
        result.append({
            'name': clip['name'],
            'frames': clip['frames'],
            'loop': clip['loop'],
            'category': clip.get('category', ''),
            'start': frame,
            'end': end,
        })
        frame = end + buffer
    return result


def timeline_end(layout):
    """Return the last frame needed for the full clip layout."""
    if not layout:
        return 0
    return layout[-1]['end']


def clip_by_name(layout, name):
    """Find a clip in the layout by name.  Returns dict or None."""
    for c in layout:
        if c['name'] == name:
            return c
    return None
