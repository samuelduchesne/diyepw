import urllib.request as _request
import re as _re
import os as _os
import pandas as _pd

from ._logging import _logger

def get_noaa_isd_lite_file(wmo_index:int, year:int, output_dir:str = None, force_update = False) -> str:
    """
    Given a WMO index and a year, retrieve the corresponding NOAA ISD Lite AMY file
    :param wmo_index:
    :param year:
    :param output_dir: Optional output directory - if not specified, the file will be saved to a package directory.
        If the directory already contains a NOAA ISD Lite file matching the requested WMO Index and year, then a new
        file will not be downloaded from NOAA and that file's path will be returned
    :param force_update: Pass True to force a new ISD Lite file to be downloaded, even if it already exists in the
       output directory.
    :return: The path to the NOAA ISD Lite file
    """
    if output_dir is None:
        this_dir = _os.path.dirname(_os.path.realpath(__file__))
        output_dir = _os.path.join(this_dir, 'files', 'noaa_isd_lite_files')
        _logger.debug(f"get_noaa_isd_lite_file() - output_dir was not defined, will use {output_dir}")

    if not _os.path.exists(output_dir):
        _os.mkdir(output_dir)
        _logger.debug(f"get_noaa_isd_lite_file() - {output_dir} did not exist, so has been created")

    # On the NOAA website, the ISD Lite files are named with a third number between WMO and year, but
    # since we don't use that third number for anything and it complicates identifying a file for a
    # WMO/Year combination, we simplify the name to only contain the values we care about
    file_name = f"{wmo_index}-{year}.gz"
    file_path = _os.path.join(output_dir, file_name)

    # Download the ISD Lite file if it's not already in the output directory
    if force_update or not _os.path.exists(file_path):
        url = _get_noaa_isd_lite_file_url(year, wmo_index)
        with _request.urlopen(url) as response:
            with open(file_path, 'wb') as downloaded_file:
                downloaded_file.write(response.read())

    return file_path

def _get_noaa_isd_lite_file_url(year:int, wmo_index:int) -> str:
    catalog = _get_noaa_isd_lite_file_catalog(year)
    file_name = list(catalog.loc[catalog['wmo_index'] == wmo_index]['file_name'])[0]
    return f"https://www1.ncdc.noaa.gov/pub/data/noaa/isd-lite/{year}/{file_name}"

def _get_noaa_isd_lite_file_catalog(year:int, catalog_dir=None, force_update=False) -> _pd.DataFrame:
    """
    Retrieve the list of all NOAA ISD Lite files for North America (WMO indices starting with 7) for a given year.
    If the file is not already present, one will be downloaded. Files are named after the year whose files they
    describe.
    :param year:
    :param catalog_dir: The directory in which to look for the file, and into which the file will be written if
        downloaded
    :param force_update: If set to True, a new copy of the catalog file will be downloaded and will overwrite the
        current one if it already exists.
    :return: A Pandas Dataframe containing a set of file names. The file names can be
        appended to the URL https://www1.ncdc.noaa.gov/pub/data/noaa/isd-lite/{year}/ to download the files from
        NOAA
    """
    if catalog_dir is None:
        this_dir = _os.path.dirname(_os.path.realpath(__file__))
        catalog_dir = _os.path.join(this_dir, 'files', 'noaa_isd_lite_catalogs')
        _logger.debug(f"catalog_dir was not defined, using {catalog_dir}")

    if not _os.path.exists(catalog_dir):
        raise Exception(f"Directory {catalog_dir} does not exist")

    file_path = _os.path.join(catalog_dir, str(year))

    # If the catalog file already exists, we'll read it. If it doesn't, we'll download it, import it into a
    # dataframe, and then save that so that it exists the next time we need it.
    if _os.path.exists(file_path) and not force_update:
        _logger.debug(f"Catalog file exists at {file_path}, using it instead of downloading it from NOAA")
        catalog = _pd.read_csv(file_path)
    else:
        catalog_url = f"https://www1.ncdc.noaa.gov/pub/data/noaa/isd-lite/{year}/"
        _logger.info(f"Downloading catalog file for year {year} from {catalog_url}")

        # Retrieve the NOAA ISD Lite catalog for the requested year
        catalog = _pd.DataFrame(columns=['wmo_index', 'file_name'])
        with _request.urlopen(catalog_url) as response:
            # Process the file: Look for an href linking to a file that starts with "7" (indicating it is
            # a North American WMO) and put all such referenced file names into the catalog file
            html = response.read().decode('utf-8')
            for line in html.splitlines():
                # Regex: Match hrefs pointing to files in the form #-#-#.gz, where the first # starts with a 7.
                # Capture groups: The big capture group gets the file name, and the small one gets the WMO
                match = _re.search(f'href="((7\d+)-.*\.gz)"', line)
                if match is not None:
                    file_name, wmo_index = match.groups()
                    catalog = catalog.append({'wmo_index': int(wmo_index), 'file_name': file_name}, ignore_index=True)

            catalog.to_csv(file_path, index=False)
            _logger.info(f"Catalog file for year {year} saved to {file_path}")

    return catalog