class DenseRasterScheduleError(RuntimeError):
    pass

class DenseRasterSchedule:
    """Own one object raster per object state, shared by all loss terms."""
    def __init__(self,rasterize,object_frozen):
        if not callable(rasterize): raise TypeError('rasterize_must_be_callable')
        self.rasterize=rasterize; self.object_frozen=bool(object_frozen)
        self._fixed=None; self._iteration_key=None; self._moving=None

    def for_forward(self,vertices,iteration_key=None):
        if self.object_frozen:
            if self._fixed is None: self._fixed=self.rasterize(vertices)
            return self._fixed
        if iteration_key is None: raise DenseRasterScheduleError('moving_object_requires_iteration_key')
        if self._iteration_key!=iteration_key:
            self._iteration_key=iteration_key; self._moving=self.rasterize(vertices)
        return self._moving

    def finish_forward(self,iteration_key=None):
        if self.object_frozen: return
        if iteration_key is not None and self._iteration_key!=iteration_key:
            raise DenseRasterScheduleError('finish_key_does_not_match_active_forward')
        self._iteration_key=None; self._moving=None

    def invalidate_fixed(self):
        if not self.object_frozen: raise DenseRasterScheduleError('moving_schedule_has_no_fixed_cache')
        self._fixed=None
