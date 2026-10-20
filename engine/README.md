# engine/: shared code

Everything recipes build on: separation, analysis, the session grid, synthesis, effects, mixing, mastering
and rendering. Module-by-module reference: [`craft/toolkit.md`](../craft/toolkit.md). How the stages fit
together: [`craft/pipeline.md`](../craft/pipeline.md).

Scripts run from the repo root, for example `python3 engine/render.py recipes/ddd2/ddd2_flume.py`. Modules
import each other by plain name (`import dsp`), which works because Python puts the running script's folder
(`engine/`) on the path.
