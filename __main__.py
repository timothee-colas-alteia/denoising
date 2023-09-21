import click
from scripts.denoising import denoised_slope


@click.command()
@click.option(
    "-p",
    "--dtm_path",
    help="DTM path.",
    required=True
)
@click.option(
    "-t",
    "--threshold",
    help="Denoising threshold.",
    default=0.6,
    show_default=True
)
@click.option(
    "-i",
    "--iterations",
    help="Number of denoising iterations.",
    default=15,
    show_default=True
)
@click.option(
    "-tm",
    "--test-mode",
    help="If test mode is flaged, all temp files are kept.",
    is_flag=True
)

def main(dtm_path: str, threshold: float, iterations: int, test_mode: bool) -> None:
    """
    This tool has for aim to denoise a LiDAR DTM raster and generate a combo slope map.
    Slope map generated has two bands, one in degrees, a second in percent.

    Mdenoise process handles the denoising part.
    https://www.cs.cf.ac.uk/meshfiltering/index_files/Page342.htm
    https://personalpages.manchester.ac.uk/staff/neil.mitchell/mdenoise/
    https://github.com/exuberant/mdenoise

    Slope map generation is handled by GDAL.
    https://gdal.org/api/python/osgeo.gdal.html#osgeo.gdal.DEMProcessing

    Author:
    Timothee Colas - Alteia
    """
    denoised_slope(tif_str_path=dtm_path, threshold=threshold, iterations=iterations, test_mode=test_mode)


if __name__ == "__main__":
    main()
