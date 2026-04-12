"""Animation layer definitions."""


class Layer:
    """Base class for animation generator layers."""

    name = ''

    def __init__(self):
        self.enabled = True
        self._params = {}

    def channels(self):
        """Return list of Channel objects for current parameter values."""
        raise NotImplementedError

    def controls(self):
        """Return list of control names affected by this layer."""
        raise NotImplementedError

    def fkik_state(self):
        """Return ``{blend_ctrl: value}`` pairs this layer requires.

        Convention: ``FKIKBlend`` 0 = full IK, 10 = full FK.
        Override in subclasses that need a specific mode.
        """
        return {}

    def params(self):
        """Return a copy of current parameter values."""
        return dict(self._params)

    def set_params(self, d):
        """Update parameters from a dict."""
        self._params.update(d)

    def reset(self):
        """Reset parameters to defaults."""
        if hasattr(self, 'DEFAULTS'):
            self._params = dict(self.DEFAULTS)
