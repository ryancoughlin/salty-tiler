from typing import Any, Dict
from titiler.core.factory import TilerFactory
from titiler.core.resources.enums import ImageType

# TilerFactory instance with bilinear resampling
cog_tiler = TilerFactory(
    reader="rio_cog",
    default_reader_options={"resampling_method": "bilinear"}
)

def render_tile(
    path: str,
    z: int,
    x: int,
    y: int,
    min_value: float,
    max_value: float,
    colormap: Any,
    colormap_bins: int = 256,
) -> bytes:
    """
    Render a PNG tile from a COG using TiTiler with bilinear resampling and a custom colormap.
    Returns PNG bytes.
    """
    # TiTiler expects scale_range as [min, max]
    return cog_tiler.render(
        path=path,
        tile_format=ImageType.png,
        scale_range=[min_value, max_value],
        colormap=colormap,
        colormap_bins=colormap_bins,
        z=z, x=x, y=y
    ) 