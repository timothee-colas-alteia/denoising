#!/usr/bin/env python3

import subprocess
import os
from pathlib import Path
from osgeo import gdal
from shutil import rmtree
import rasterio as rio
from rasterio.warp import calculate_default_transform, Resampling, reproject
from shapely.geometry import box
import geopandas as gpd
from colorama import Fore, Back, Style


def denoised_slope(tif_str_path: str, threshold: float, iterations: int, test_mode: bool) -> None:
    """
    This function execute all sub-functions to generate a denoised slope map.
    It creates a temporary folder where all step files are stocked.
    If test mode is not false, all temporary files are dumped.

    Parameters:
    -----------
    tif_str_path: String
        Path of DTM raster.

    threshold: Float
        Denoising threshold.

    iterations: Int
        Number of denoising iterations.

    test_mode: Bool
        If test mode is true, all temp files are kept.
    """
    if test_mode:
        print(Fore.BLACK + Style.BRIGHT + Back.GREEN +
              '\nTest mode activated, all temporary files are retained.' + Style.RESET_ALL)

    tif_path = Path(tif_str_path)
    temp_path = tif_path.parent / Path('temp')
    if temp_path.exists():
        rmtree(temp_path)
    os.mkdir(temp_path)

    tif_path, tif_crs, good_unit = check_unit(
        tif_path=tif_path, temp_path=temp_path)
    asc_path = tif2asc(tif_path=tif_path, temp_path=temp_path)
    asc_denoised_path = denoising(
        asc_path=asc_path, threshold=threshold, iterations=iterations)
    tif_denoised_path = asc2tif(asc_denoised_path=asc_denoised_path)
    slope(tif_denoised_path=tif_denoised_path, temp_path=temp_path,
          tif_crs=tif_crs, good_unit=good_unit)

    if not test_mode:
        try:
            rmtree(temp_path)
        except:
            pass

    print(Fore.GREEN + '\nSlope Map Generation Complete!\n')


def check_unit(tif_path: Path, temp_path: Path) -> [Path, str, bool]:
    """
    This function check unit of raster projection. Mdenoise requires projection in meter to operate.
    If raster projection unit isn't meter, this function reprojects raster in an appropriate projection.

    Parameters
    ----------
    tif_path: Path
        Path of DTM raster.

    temp_path: Path
        Path of temporary folder.

    Returns
    -------
    tif_path: Path
        Path of DTM raster.

    reproj_tif_path: Path
        Path of reprojected DTM raster.

    tif_crs: String
        Original CRS of DTM raster.

    good_unit: Boolean
        Is unit good, True or False.
    """
    print(Fore.YELLOW + '\nChecking raster unit' + Style.RESET_ALL)
    with rio.open(tif_path, 'r') as tif:
        tif_transform = tif.transform

        tif_crs = tif.crs
        tif_unit = tif.crs.linear_units
        print('Unit: {}'.format(tif_unit))

        if tif_unit != 'metre':
            print('Reprojection required to a meter projected coordinate system')

            bounds = tif.bounds
            gdf = gpd.GeoDataFrame({"id": 1, "geometry": [box(*bounds)]})
            gdf.crs = tif_crs.to_authority()[1]
            dst_crs = gdf.estimate_utm_crs()
            print('New projection used: {}'.format(dst_crs))

            transform, width, height = calculate_default_transform(
                tif.crs, dst_crs, tif.width, tif.height, *tif.bounds)
            kwargs = tif.meta.copy()
            kwargs.update({
                'crs': dst_crs,
                'transform': transform,
                'width': width,
                'height': height
            })

            reproj_tif_path = Path(str(temp_path / tif_path.stem) +
                                   '_{}'.format(dst_crs) + str(tif_path.suffix))

            with rio.open(reproj_tif_path, 'w', **kwargs) as dst:
                reproject(
                    source=rio.band(tif, 1),
                    destination=rio.band(dst, 1),
                    src_transform=tif_transform,
                    src_crs=tif_crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.cubic
                )
            good_unit = False
            return reproj_tif_path, tif_crs, good_unit
        else:
            print('OK')
            good_unit = True
            return tif_path, tif_crs, good_unit


def tif2asc(tif_path: Path, temp_path: Path) -> Path:
    """
    This function convert DTM tif into ascii file.

    Parameters
    ----------
    tif_path: Path
        Path of DTM raster.

    temp_path: Path
        Path of temporary folder.

    Returns
    -------
    asc_path: Path
        Path of ascii DTM file.
    """
    print(Fore.YELLOW + '\nConverting Tif to Ascii' + Style.RESET_ALL)
    asc_path = Path(str(temp_path / tif_path.stem) + '.asc')
    gdal.Translate(str(asc_path), str(tif_path), widthPct=100,
                   heightPct=100, resampleAlg='cubicspline', format='AAIGrid')
    return asc_path


def denoising(asc_path: Path, threshold: float, iterations: int) -> Path:
    """
    This function do denoising task with Mdenoise tool.

    Parameters
    ----------
    asc_path: Path
        Path of ascii DTM file.

    threshold: Float
        Denoising threshold.

    iterations: Int
        Number of denoising iterations.

    Returns
    -------
    asc_denoised_path: Path
        Path of ascii DTM denoised file.
    """
    print(Fore.YELLOW + '\nDenoising Ascii' + Style.RESET_ALL)
    asc_denoised_path = Path(str(asc_path.parent / asc_path.stem) +
                             '_denoised_{}_{}'.format(threshold, iterations) + str(asc_path.suffix))
    print('Output File: {}'.format(asc_denoised_path))

    bashCommand = "mdenoise -i {} -t {} -n {} -v 50 -o {} -z".format(
        asc_path, threshold, iterations, asc_denoised_path)
    process = subprocess.run(bashCommand, shell=True)

    return asc_denoised_path


def asc2tif(asc_denoised_path: Path) -> Path:
    """
    This function convert DTM denoised ascii into tif file.

    Parameters
    ----------
    asc_denoised_path: Path
        Path of ascii DTM denoised file.

    Returns
    -------
    tif_denoised_path: Path
        Path of tif DTM denoised file.
    """
    print(Fore.YELLOW + '\nConverting Ascii to Tif' + Style.RESET_ALL)
    tif_denoised_path = Path(
        str(asc_denoised_path.parent / asc_denoised_path.stem) + '.tif')
    gdal.Translate(str(tif_denoised_path), str(
        asc_denoised_path), format='Gtiff')
    return tif_denoised_path


def slope(tif_denoised_path: Path, temp_path: Path, tif_crs: str, good_unit: bool) -> None:
    """
    This function generate two slope maps, one in degrees, second in percentage.
    Both are combined in a two bands raster file.
    If original raster projection unit isn't meter, it reprojects slope raster in original projection.

    Parameters
    ----------
    tif_denoised_path: Path
        Path of tif DTM denoised file.

    temp_path: Path
        Path of temporary folder.

    tif_crs: String
        Original CRS of DTM raster.

    good_unit: Boolean
        Is unit good, True or False.    
    """
    pre_slope_list = []
    for slopeformat in ['degree', 'percent']:
        print(Fore.YELLOW +
              '\nGenerating {} slope map'.format(slopeformat) + Style.RESET_ALL)
        pre_slope_path = Path(
            str(tif_denoised_path.parent / tif_denoised_path.stem)
            + '_slope_'
            + str(slopeformat)
            + str(tif_denoised_path.suffix)
        )

        pre_slope_list.append(pre_slope_path)

        gdal.DEMProcessing(
            destName=str(pre_slope_path),
            srcDS=str(tif_denoised_path),
            scale=1.0,
            band=1,
            processing='slope',
            slopeFormat=slopeformat,
            format='GTiff'
        )

    slope_path = Path(
        str(tif_denoised_path.parents[1] / tif_denoised_path.stem)
        + '_slope'
        + str(tif_denoised_path.suffix)
    )
    print(Fore.YELLOW + '\nCombining slope maps' + Style.RESET_ALL)
    degree = rio.open(pre_slope_list[0])
    percent = rio.open(pre_slope_list[1])

    profile = degree.profile
    profile.update(count=2)
    kwargs = degree.meta.copy()
    kwargs.update({
        'count': 2,
        'crs': tif_crs
    })

    if good_unit:
        with rio.open(slope_path, 'w', **kwargs) as dest:
            for band, src in enumerate([degree.read(1), percent.read(1)], start=1):
                dest.write(src, band)
    else:
        with rio.open(temp_path / slope_path.stem, 'w', **profile) as dest:
            for band, src in enumerate([degree.read(1), percent.read(1)], start=1):
                dest.write(src, band)

        print('Reprojection to original projected coordinate system: {}'.format(tif_crs))
        with rio.open(temp_path / slope_path.stem) as src:
            transform, width, height = calculate_default_transform(
                src.crs, tif_crs, src.width, src.height, *src.bounds)
            kwargs = src.meta.copy()
            kwargs.update({
                'crs': tif_crs,
                'transform': transform,
                'width': width,
                'height': height
            })

            with rio.open(
                str(slope_path.parent / Path(slope_path.stem[:slope_path.stem.find(
                    '_EPSG')] + slope_path.stem[slope_path.stem.find('_denoised'):])) + slope_path.suffix,
                'w',
                **kwargs
            ) as dst:
                for i in range(1, profile['count']):
                    reproject(
                        source=rio.band(src, i),
                        destination=rio.band(dst, i),
                        src_transform=src.transform,
                        src_crs=src.crs,
                        dst_transform=transform,
                        dst_crs=tif_crs,
                        resampling=Resampling.cubic)


if __name__ == "__main__":

    tif_str_path = '/home/timothee/DTM_Denoising/DATA/LIDAR_DTM_4171.tif'
    threshold = 0.6
    iterations = 15

    denoised_slope(tif_str_path=tif_str_path, threshold=threshold,
                   iterations=iterations, test_mode=True)
